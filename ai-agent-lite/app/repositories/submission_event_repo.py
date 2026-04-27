"""Repository helpers for submission fallback event persistence."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import SubmissionEvent, SubmissionEventDLQ


async def get_by_idempotency(
    db: AsyncSession,
    submission_id: str,
    event_type: str,
    event_version: str,
) -> SubmissionEvent | None:
    """Find an existing event row by idempotency tuple."""
    result = await db.execute(
        select(SubmissionEvent).where(
            SubmissionEvent.submission_id == submission_id,
            SubmissionEvent.event_type == event_type,
            SubmissionEvent.event_version == event_version,
        )
    )
    return result.scalar_one_or_none()


async def has_accepted_before(
    db: AsyncSession,
    user_id: str,
    problem_id: str,
    submission_id: str,
) -> bool:
    """Return True when user already had ACCEPTED for this problem before this submission."""
    result = await db.execute(
        select(func.count(SubmissionEvent.id)).where(
            SubmissionEvent.user_id == user_id,
            SubmissionEvent.problem_id == problem_id,
            SubmissionEvent.status_label == "ACCEPTED",
            SubmissionEvent.submission_id != submission_id,
        )
    )
    return int(result.scalar() or 0) > 0


async def create_event(db: AsyncSession, payload: dict[str, Any]) -> tuple[SubmissionEvent, bool]:
    """Insert submission event; return (row, created)."""
    row = SubmissionEvent(
        session_id=UUID(payload["session_id"]) if payload.get("session_id") else None,
        user_id=payload["user_id"],
        problem_id=payload["problem_id"],
        submission_id=payload["submission_id"],
        event_type=payload["event_type"],
        event_version=payload["event_version"],
        source=payload["source"],
        status_code=payload.get("status_code"),
        status_label=payload["status_label"],
        language=payload.get("language"),
        score=payload.get("score", 0),
        time_cost_ms=payload.get("time_cost_ms", 0),
        memory_cost_kb=payload.get("memory_cost_kb", 0),
        test_cases_total=payload.get("test_cases_total", 0),
        test_cases_passed=payload.get("test_cases_passed", 0),
        summary_text=payload["summary_text"],
        raw_payload=payload["raw_payload"],
        should_trigger_ai=bool(payload.get("should_trigger_ai", True)),
        is_first_ac=bool(payload.get("is_first_ac", False)),
    )

    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
        return row, True
    except IntegrityError:
        await db.rollback()
        existing = await get_by_idempotency(
            db,
            submission_id=payload["submission_id"],
            event_type=payload["event_type"],
            event_version=payload["event_version"],
        )
        if existing:
            return existing, False
        raise


async def create_dlq(
    db: AsyncSession,
    source: str,
    payload: dict[str, Any],
    error_message: str,
    retry_count: int = 0,
) -> SubmissionEventDLQ:
    """Persist a failed submission-event payload into DLQ table."""
    row = SubmissionEventDLQ(
        source=source,
        payload=payload,
        error_message=str(error_message)[:2000],
        retry_count=max(0, int(retry_count)),
        resolved=False,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_pending_dlq(db: AsyncSession, limit: int = 50) -> list[SubmissionEventDLQ]:
    """List unresolved DLQ rows ordered by oldest first."""
    result = await db.execute(
        select(SubmissionEventDLQ)
        .where(SubmissionEventDLQ.resolved.is_(False))
        .order_by(SubmissionEventDLQ.created_at.asc())
        .limit(max(1, limit))
    )
    return list(result.scalars().all())


async def count_pending_dlq(db: AsyncSession) -> int:
    """Count unresolved DLQ rows."""
    result = await db.execute(
        select(func.count(SubmissionEventDLQ.id)).where(SubmissionEventDLQ.resolved.is_(False))
    )
    return int(result.scalar() or 0)


async def mark_dlq_resolved(db: AsyncSession, dlq_id: int) -> None:
    """Mark one DLQ row as resolved."""
    await db.execute(
        update(SubmissionEventDLQ)
        .where(SubmissionEventDLQ.id == dlq_id)
        .values(resolved=True)
    )
    await db.commit()


async def increment_dlq_retry(
    db: AsyncSession,
    dlq_id: int,
    error_message: str,
) -> None:
    """Increase retry counter and refresh last error message."""
    row = await db.get(SubmissionEventDLQ, dlq_id)
    if row is None:
        return
    row.retry_count = int(row.retry_count or 0) + 1
    row.error_message = str(error_message)[:2000]
    await db.commit()
