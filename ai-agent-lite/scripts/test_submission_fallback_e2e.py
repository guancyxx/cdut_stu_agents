"""
E2E smoke tests for submission fallback ingestion APIs.

Covers current implemented P0/P1 behavior:
1) Auto send success path (fallback ingest created=true)
2) Rejudge idempotency (same submission_id should deduplicate)
3) first_ac signal toggling on first/second ACCEPTED
4) DLQ replay endpoint reachability

Usage:
  python scripts/test_submission_fallback_e2e.py
  AGENT_BASE_URL=http://127.0.0.1:8850 python scripts/test_submission_fallback_e2e.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request


BASE_URL = os.getenv("AGENT_BASE_URL", "http://127.0.0.1:8850").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("E2E_TIMEOUT_SECONDS", "15"))


@dataclass
class CaseResult:
    name: str
    passed: bool
    detail: str


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _post_json(path: str, payload: dict[str, Any], params: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    query = f"?{urllib_parse.urlencode(params)}" if params else ""
    url = f"{BASE_URL}{path}{query}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url=url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib_request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status = int(resp.getcode())
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise AssertionError(f"POST {url} failed: {type(exc).__name__}: {exc}") from exc

    try:
        body = json.loads(raw) if raw else {}
    except Exception:
        raise AssertionError(f"POST {url} returned invalid JSON: {raw!r}")

    if status >= 400:
        raise AssertionError(f"POST {url} failed: status={status}, body={body!r}")
    if not isinstance(body, dict):
        raise AssertionError(f"POST {url} returned non-object body: {body!r}")

    return status, body


def _build_payload(
    *,
    session_id: str,
    user_id: str,
    problem_id: str,
    submission_id: str,
    status_label: str,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "user_id": user_id,
        "problem_id": problem_id,
        "submission_id": submission_id,
        "status_code": 0 if status_label == "ACCEPTED" else 1,
        "status_label": status_label,
        "status_display": status_label,
        "language": "Python3",
        "score": 100 if status_label == "ACCEPTED" else 0,
        "time_cost_ms": 12,
        "memory_cost_kb": 1024,
        "err_info": "",
        "test_cases": [
            {"index": 1, "status": 0 if status_label == "ACCEPTED" else 1, "label": status_label}
        ],
        "source": "frontend_fb",
        "should_trigger_ai": True,
    }


def test_auto_send_success_and_idempotency() -> CaseResult:
    case_name = "auto_send_success_and_rejudge_idempotency"
    suffix = uuid.uuid4().hex[:8]
    session_id = str(uuid.uuid4())
    user_id = f"e2e_user_{suffix}"
    problem_id = f"e2e_problem_{suffix}"
    submission_id = f"e2e_submission_{suffix}"

    _, first = _post_json(
        "/oj/submission-events/fallback",
        _build_payload(
            session_id=session_id,
            user_id=user_id,
            problem_id=problem_id,
            submission_id=submission_id,
            status_label="WRONG_ANSWER",
        ),
    )
    _assert(first.get("ok") is True, "first fallback should return ok=true")
    _assert(first.get("created") is True, "first fallback should create row")
    _assert(isinstance(first.get("event_id"), int), "first fallback should return event_id int")

    _, second = _post_json(
        "/oj/submission-events/fallback",
        _build_payload(
            session_id=session_id,
            user_id=user_id,
            problem_id=problem_id,
            submission_id=submission_id,
            status_label="WRONG_ANSWER",
        ),
    )
    _assert(second.get("ok") is True, "duplicate fallback should return ok=true")
    _assert(second.get("created") is False, "duplicate fallback should not create new row")
    _assert(second.get("event_id") == first.get("event_id"), "duplicate should return same event_id")

    return CaseResult(case_name, True, "created=true then created=false with same event_id")


def test_first_ac_signal() -> CaseResult:
    case_name = "first_ac_signal"
    suffix = uuid.uuid4().hex[:8]
    session_id = str(uuid.uuid4())
    user_id = f"e2e_user_ac_{suffix}"
    problem_id = f"e2e_problem_ac_{suffix}"

    first_submission_id = f"e2e_submission_ac1_{suffix}"
    second_submission_id = f"e2e_submission_ac2_{suffix}"

    _, first = _post_json(
        "/oj/submission-events/fallback",
        _build_payload(
            session_id=session_id,
            user_id=user_id,
            problem_id=problem_id,
            submission_id=first_submission_id,
            status_label="ACCEPTED",
        ),
    )
    _assert(first.get("ok") is True, "first AC should return ok=true")
    _assert(first.get("created") is True, "first AC should create row")
    _assert(first.get("is_first_ac") is True, "first AC should set is_first_ac=true")

    _, second = _post_json(
        "/oj/submission-events/fallback",
        _build_payload(
            session_id=session_id,
            user_id=user_id,
            problem_id=problem_id,
            submission_id=second_submission_id,
            status_label="ACCEPTED",
        ),
    )
    _assert(second.get("ok") is True, "second AC should return ok=true")
    _assert(second.get("created") is True, "second AC with new submission should create row")
    _assert(second.get("is_first_ac") is False, "second AC should set is_first_ac=false")

    return CaseResult(case_name, True, "is_first_ac toggled true->false across two ACCEPTED events")


def test_retry_dlq_endpoint() -> CaseResult:
    case_name = "retry_dlq_endpoint"
    _, body = _post_json("/oj/submission-events/retry-dlq", payload={}, params={"limit": 5})
    _assert(isinstance(body, dict), "retry-dlq should return JSON object")
    _assert(body.get("ok") is True, "retry-dlq should return ok=true")
    _assert(isinstance(body.get("scanned"), int), "retry-dlq should include scanned:int")
    _assert(isinstance(body.get("replayed"), int), "retry-dlq should include replayed:int")
    _assert(isinstance(body.get("failed"), int), "retry-dlq should include failed:int")

    return CaseResult(case_name, True, f"scanned={body.get('scanned')} replayed={body.get('replayed')} failed={body.get('failed')}")


def run() -> int:
    started = datetime.now(timezone.utc).isoformat()
    print(f"[INFO] start={started} base_url={BASE_URL} timeout={TIMEOUT_SECONDS}s")

    cases: list[CaseResult] = []
    for test_func in (
        test_auto_send_success_and_idempotency,
        test_first_ac_signal,
        test_retry_dlq_endpoint,
    ):
        name = test_func.__name__
        try:
            result = test_func()
            cases.append(result)
            print(f"[PASS] {result.name} :: {result.detail}")
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            cases.append(CaseResult(name=name, passed=False, detail=detail))
            print(f"[FAIL] {name} :: {detail}")

    passed = sum(1 for c in cases if c.passed)
    failed = sum(1 for c in cases if not c.passed)

    print("\n[SUMMARY]")
    print(json.dumps(
        {
            "base_url": BASE_URL,
            "total": len(cases),
            "passed": passed,
            "failed": failed,
            "cases": [c.__dict__ for c in cases],
        },
        ensure_ascii=False,
        indent=2,
    ))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
