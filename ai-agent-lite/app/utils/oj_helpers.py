"""Shared OJ-compat helpers: verdict mapping, time utils, JSON parsing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


def status_code_from_verdict(verdict: str) -> int:
    """Map verdict string to legacy-OJ-compatible status code."""
    mapping = {
        "AC": 0,
        "WA": -1,
        "CE": -2,
        "TLE": 1,
        "MLE": 3,
        "RE": 4,
        "SE": 5,
    }
    return mapping.get(verdict, 5)


def status_label(verdict: str) -> str:
    """Map verdict string to human-readable label."""
    mapping = {
        "AC": "ACCEPTED",
        "WA": "WRONG_ANSWER",
        "CE": "COMPILE_ERROR",
        "TLE": "CPU_TIME_LIMIT_EXCEEDED",
        "MLE": "MEMORY_LIMIT_EXCEEDED",
        "RE": "RUNTIME_ERROR",
        "SE": "SYSTEM_ERROR",
    }
    return mapping.get(verdict, "SYSTEM_ERROR")


def parse_json(value: Any, default: Any) -> Any:
    """Safely parse a JSON string, returning default on failure."""
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return default
    return default


def parse_uuid(value: str) -> str | None:
    """Validate and return a UUID string, or None on failure."""
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def contest_status(
    start_time: datetime, end_time: datetime, now: datetime,
) -> str:
    """Compute contest status from start/end times."""
    if now < start_time:
        return "upcoming"
    if now >= end_time:
        return "ended"
    return "running"


LANG_MAP = {
    "C++": "cpp", "C": "c", "Java": "java", "Python3": "python3",
    "cpp": "cpp", "c": "c", "java": "java", "python3": "python3",
}


def normalize_language(language: str) -> str:
    """Convert frontend language label to judge-internal label."""
    return LANG_MAP.get(language.strip(), language.strip())
