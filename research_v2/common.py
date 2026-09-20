"""Shared clients and helpers for PromptShield Research V2."""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from research_v2.canary_victim import SCENARIOS, detect_canary_leakage
from research_v2.prompt_conditions import DETECTOR_PROMPTS

load_dotenv()

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"
DETECTOR_TEMPERATURE = 0.0
VICTIM_TEMPERATURE = 0.0


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


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: str, obj: dict) -> None:
    ensure_parent(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_json_object(text: str) -> Optional[dict]:
    """Parse model JSON without turning parse failures into benign labels."""
    raw = (text or "").strip()
    try:
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, IndexError):
        return None


def validate_detection_payload(payload: Optional[dict]) -> Optional[dict]:
    """Validate the fields that Research V2 depends on.

    Important: do not coerce strings such as "false" with bool(...), because
    bool("false") is True in Python and would silently corrupt labels.
    """
    if payload is None:
        return None

    is_attack = payload.get("is_attack")
    if not isinstance(is_attack, bool):
        return None

    confidence = payload.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            return None
        if not 0.0 <= float(confidence) <= 1.0:
            return None

    return payload


class ResearchDetector:
    def __init__(self, model: str = DEFAULT_MODEL):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set.")
        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        self.model = model

    def analyze(self, input_text: str, condition: str) -> dict:
        prompt = DETECTOR_PROMPTS[condition].format(input_text=input_text)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=384,
            temperature=DETECTOR_TEMPERATURE,
        )
        raw_text = response.choices[0].message.content
        parsed = validate_detection_payload(parse_json_object(raw_text))
        return {
            "condition": condition,
            "raw_text": raw_text,
            "parsed": parsed,
            "parse_error": parsed is None,
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": scenario.system_prompt},
                {"role": "user", "content": user_input},
            ],
            max_tokens=512,
            temperature=VICTIM_TEMPERATURE,
        )
        text = response.choices[0].message.content
        leakage = detect_canary_leakage(text, scenario_key)
        return {
            "scenario": scenario_key,
            "response": text,
            **leakage,
        }
