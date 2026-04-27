"""Submission summary builder for OJ->AI fallback events."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_REDACT_PATTERNS = [
    re.compile(r"\b\d{11}\b"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]


@dataclass
class SubmissionSummaryResult:
    """Normalized summary payload used by API and persistence layers."""

    summary_text: str
    test_cases_total: int
    test_cases_passed: int


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clip_text(value: Any, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}...(truncated)"


def _redact_sensitive(text: str) -> str:
    sanitized = text
    for pattern in _REDACT_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def build_submission_summary(payload: dict[str, Any]) -> SubmissionSummaryResult:
    """Create a concise and safe summary from raw submission payload."""
    status_label = _clip_text(payload.get("status_label") or "UNKNOWN", 32)
    status_display = _clip_text(payload.get("status_display") or status_label, 64)
    submission_id = _clip_text(payload.get("submission_id"), 64)
    score = _safe_int(payload.get("score"), 0)
    time_cost_ms = _safe_int(payload.get("time_cost_ms"), 0)
    memory_cost_kb = _safe_int(payload.get("memory_cost_kb"), 0)

    raw_cases = payload.get("test_cases")
    test_cases = raw_cases if isinstance(raw_cases, list) else []
    test_cases_total = len(test_cases)
    test_cases_passed = 0

    for case in test_cases:
        if not isinstance(case, dict):
            continue
        label = str(case.get("label") or "").upper()
        status = _safe_int(case.get("status"), -1)
        if label == "ACCEPTED" or status == 0:
            test_cases_passed += 1

    lines: list[str] = [f"[{status_label}] {status_display}"]
    if submission_id:
        lines.append(f"Submission: {submission_id}")
    lines.append(f"Score: {score}")
    lines.append(f"Time: {time_cost_ms}ms | Memory: {memory_cost_kb}KB")

    err_info = _clip_text(payload.get("err_info"), 600)
    if err_info:
        lines.append(f"Error: {_redact_sensitive(err_info)}")

    if test_cases_total > 0:
        lines.append(f"Cases: {test_cases_passed}/{test_cases_total} passed")

    summary_text = "\n".join(lines)
    return SubmissionSummaryResult(
        summary_text=summary_text,
        test_cases_total=test_cases_total,
        test_cases_passed=test_cases_passed,
    )
