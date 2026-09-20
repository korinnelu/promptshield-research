"""Dependency-free parsing and validation for Research V2 detector outputs."""

import json
from typing import Optional


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


DETECTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_attack": {"type": "boolean"},
        "attack_type": {
            "type": "string",
            "enum": [
                "direct_injection",
                "indirect_injection",
                "jailbreak",
                "persona_hijack",
                "privilege_escalation",
                "social_engineering",
                "none",
            ],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "none"],
        },
        "explanation": {"type": "string"},
    },
    "required": [
        "is_attack",
        "attack_type",
        "confidence",
        "severity",
        "explanation",
    ],
    "additionalProperties": False,
}
