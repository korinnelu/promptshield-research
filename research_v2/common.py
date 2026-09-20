"""Shared clients and helpers for PromptShield Research V2."""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)

from research_v2.canary_victim import SCENARIOS, detect_canary_leakage
from research_v2.prompt_conditions import DETECTOR_PROMPTS
from research_v2.schema import (
    DETECTION_JSON_SCHEMA,
    parse_json_object,
    validate_detection_payload,
)

load_dotenv()

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DETECTOR_TEMPERATURE = 0.5
VICTIM_TEMPERATURE = 0.5
TOP_P = 1.0
DETECTOR_MAX_TOKENS = 1024
VICTIM_MAX_TOKENS = 1024
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RETRY_DELAYS_SECONDS = (2, 4, 8, 16, 30, 30)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_git_sha() -> Optional[str]:
    """Return current git commit SHA when running inside a git checkout."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None



def call_with_retry(fn, label: str):
    """Retry transient provider/network failures with deterministic backoff.

    This changes only execution reliability. It does not modify prompts,
    model parameters, labels, or benchmark inputs.
    """
    max_attempts = len(RETRY_DELAYS_SECONDS) + 1

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
            status_code = getattr(exc, "status_code", None)
            retryable = (
                isinstance(exc, (APIConnectionError, APITimeoutError))
                or status_code in RETRYABLE_STATUS_CODES
            )

            if not retryable or attempt >= max_attempts:
                raise

            delay = RETRY_DELAYS_SECONDS[attempt - 1]
            status_text = (
                f"HTTP {status_code}"
                if status_code is not None
                else exc.__class__.__name__
            )
            print(
                f"[retry] {label}: {status_text}; "
                f"attempt {attempt}/{max_attempts}, "
                f"retrying in {delay}s..."
            )
            time.sleep(delay)


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: str, obj: dict) -> None:
    ensure_parent(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ResearchDetector:
    def __init__(self, model: str = DEFAULT_MODEL):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set.")
        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        self.model = model

    def analyze(self, input_text: str, condition: str) -> dict:
        prompt = DETECTOR_PROMPTS[condition].format(input_text=input_text)
        response = call_with_retry(
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=DETECTOR_MAX_TOKENS,
                temperature=DETECTOR_TEMPERATURE,
                top_p=TOP_P,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "guided_json": DETECTION_JSON_SCHEMA,
                },
            ),
            label=f"detector/{condition}",
        )
        choice = response.choices[0]
        raw_text = choice.message.content
        parsed = validate_detection_payload(parse_json_object(raw_text))
        return {
            "condition": condition,
            "raw_text": raw_text,
            "parsed": parsed,
            "parse_error": parsed is None,
            "finish_reason": choice.finish_reason,
        }


class ResearchVictim:
    def __init__(self, model: str = DEFAULT_MODEL):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set.")
        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        self.model = model

    def respond(self, scenario_key: str, user_input: str) -> dict:
        scenario = SCENARIOS[scenario_key]
        response = call_with_retry(
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": scenario.system_prompt},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=VICTIM_MAX_TOKENS,
                temperature=VICTIM_TEMPERATURE,
                top_p=TOP_P,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False}
                },
            ),
            label=f"victim/{scenario_key}",
        )
        choice = response.choices[0]
        text = choice.message.content
        leakage = detect_canary_leakage(text, scenario_key)
        return {
            "scenario": scenario_key,
            "response": text,
            "finish_reason": choice.finish_reason,
            "truncated": choice.finish_reason == "length",
            **leakage,
        }
