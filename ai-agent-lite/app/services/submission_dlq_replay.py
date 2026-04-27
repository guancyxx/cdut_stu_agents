"""Replay service for unresolved submission-event DLQ rows."""
from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics import (
    submission_dlq_pending_rows,
    submission_dlq_replay_duration_seconds,
    submission_dlq_replay_rows_total,
    submission_dlq_replay_runs_total,
)
from app.repositories import submission_event_repo
from app.services.submission_summary import build_submission_summary


async def replay_submission_dlq(db: AsyncSession, limit: int = 20) -> dict[str, int]:
    """Replay unresolved DLQ rows and return replay counters."""
    started_at = time.perf_counter()
    rows = await submission_event_repo.list_pending_dlq(db, limit=limit)
    replayed = 0
    failed = 0

    for row in rows:
        payload = row.payload or {}
        try:
            summary = build_submission_summary(payload)
            event_payload = {
                "session_id": payload.get("session_id"),
                "user_id": str(payload.get("user_id") or "").strip(),
                "problem_id": str(payload.get("problem_id") or "").strip(),
                "submission_id": str(payload.get("submission_id") or "").strip(),
                "event_type": "submission.finalized",
                "event_version": "v1",
                "source": str(payload.get("source") or "frontend_fb"),
                "status_code": payload.get("status_code"),
                "status_label": str(payload.get("status_label") or "ERROR").strip().upper(),
                "language": payload.get("language"),
                "score": int(payload.get("score") or 0),
                "time_cost_ms": int(payload.get("time_cost_ms") or 0),
                "memory_cost_kb": int(payload.get("memory_cost_kb") or 0),
                "test_cases_total": summary.test_cases_total,
                "test_cases_passed": summary.test_cases_passed,
                "summary_text": summary.summary_text,
                "raw_payload": payload,
                "should_trigger_ai": bool(payload.get("should_trigger_ai", True)),
                "is_first_ac": False,
            }
            if not event_payload["user_id"] or not event_payload["problem_id"] or not event_payload["submission_id"]:
                raise ValueError("missing required replay fields")

            await submission_event_repo.create_event(db, event_payload)
            await submission_event_repo.mark_dlq_resolved(db, row.id)
            replayed += 1
        except Exception as exc:
            await submission_event_repo.increment_dlq_retry(db, row.id, str(exc))
            failed += 1

    pending = await submission_event_repo.count_pending_dlq(db)
    submission_dlq_pending_rows.set(pending)
    submission_dlq_replay_rows_total.labels(outcome="replayed").inc(replayed)
    submission_dlq_replay_rows_total.labels(outcome="failed").inc(failed)
    submission_dlq_replay_runs_total.labels(outcome="success").inc()
    submission_dlq_replay_duration_seconds.observe(time.perf_counter() - started_at)

    return {
        "scanned": len(rows),
        "replayed": replayed,
        "failed": failed,
        "pending": pending,
    }
