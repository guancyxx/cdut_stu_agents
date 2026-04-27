"""Fallback ingestion API for finalized OJ submission events."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.metrics import submission_fallback_events_total
from app.repositories import audit_repo, session_repo, submission_event_repo
from app.services.submission_summary import build_submission_summary
from app.services.submission_recommendation import SubmissionRecommendationService
from app.services.submission_dlq_replay import replay_submission_dlq

router = APIRouter(prefix="/oj/submission-events", tags=["submission-events"])
logger = logging.getLogger("ai-agent-lite.submission-events")

_FINAL_STATUSES = {
    "ACCEPTED",
    "WRONG_ANSWER",
    "COMPILE_ERROR",
    "RUNTIME_ERROR",
    "CPU_TIME_LIMIT_EXCEEDED",
    "REAL_TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "SYSTEM_ERROR",
    "PARTIALLY_ACCEPTED",
    "TIMEOUT",
    "ERROR",
}


class TestCasePayload(BaseModel):
    """Per-test-case compact payload from frontend."""

    index: int | None = None
    status: int | None = None
    label: str | None = None


class SubmissionFallbackRequest(BaseModel):
    """Request body for frontend fallback submission event."""

    session_id: str | None = Field(default=None, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    problem_id: str = Field(min_length=1, max_length=64)
    submission_id: str = Field(min_length=1, max_length=64)
    status_code: int | None = None
    status_label: str = Field(min_length=1, max_length=64)
    status_display: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=32)
    score: int = 0
    time_cost_ms: int = 0
    memory_cost_kb: int = 0
    err_info: str | None = Field(default=None, max_length=4000)
    test_cases: list[TestCasePayload] = Field(default_factory=list)
    source: str = Field(default="frontend_fb", max_length=16)
    should_trigger_ai: bool = True


class SubmissionFallbackResponse(BaseModel):
    """Response payload with idempotency result."""

    ok: bool
    created: bool
    event_id: int
    event_type: str
    event_version: str
    summary_text: str
    should_trigger_ai: bool
    is_first_ac: bool
    recommendation: dict[str, Any] | None = None


class SubmissionRetryResponse(BaseModel):
    """DLQ retry execution result."""

    ok: bool
    scanned: int
    replayed: int
    failed: int


def _normalize_event_payload(body: SubmissionFallbackRequest) -> dict[str, Any]:
    status_label = body.status_label.strip().upper()
    if status_label not in _FINAL_STATUSES:
        raise HTTPException(status_code=400, detail="status_label must be a final submission status")

    session_id = (body.session_id or "").strip() or None
    if session_id:
        try:
            UUID(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="session_id must be a valid UUID") from exc

    payload = {
        "session_id": session_id,
        "user_id": body.user_id.strip(),
        "problem_id": body.problem_id.strip(),
        "submission_id": body.submission_id.strip(),
        "status_code": body.status_code,
        "status_label": status_label,
        "status_display": (body.status_display or status_label).strip(),
        "language": (body.language or "").strip() or None,
        "score": max(0, int(body.score)),
        "time_cost_ms": max(0, int(body.time_cost_ms)),
        "memory_cost_kb": max(0, int(body.memory_cost_kb)),
        "err_info": body.err_info or "",
        "test_cases": [tc.model_dump() for tc in body.test_cases],
        "source": body.source,
        "should_trigger_ai": bool(body.should_trigger_ai),
    }

    return payload


@router.post("/fallback", response_model=SubmissionFallbackResponse)
async def ingest_submission_fallback(
    body: SubmissionFallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> SubmissionFallbackResponse:
    """Ingest fallback submission result and persist idempotently."""
    normalized = _normalize_event_payload(body)
    if not normalized["session_id"]:
        session_row = await session_repo.find_recent_active_session(
            db,
            user_id=normalized["user_id"],
            problem_id=normalized["problem_id"],
            within_minutes=180,
        )
        if session_row:
            normalized["session_id"] = str(session_row.id)

    summary = build_submission_summary(normalized)

    is_first_ac = False
    if normalized["status_label"] == "ACCEPTED":
        had_accepted_before = await submission_event_repo.has_accepted_before(
            db,
            user_id=normalized["user_id"],
            problem_id=normalized["problem_id"],
            submission_id=normalized["submission_id"],
        )
        is_first_ac = not had_accepted_before

    event_payload = {
        "session_id": normalized["session_id"],
        "user_id": normalized["user_id"],
        "problem_id": normalized["problem_id"],
        "submission_id": normalized["submission_id"],
        "event_type": "submission.finalized",
        "event_version": "v1",
        "source": normalized["source"],
        "status_code": normalized["status_code"],
        "status_label": normalized["status_label"],
        "language": normalized["language"],
        "score": normalized["score"],
        "time_cost_ms": normalized["time_cost_ms"],
        "memory_cost_kb": normalized["memory_cost_kb"],
        "test_cases_total": summary.test_cases_total,
        "test_cases_passed": summary.test_cases_passed,
        "summary_text": summary.summary_text,
        "raw_payload": normalized,
        "should_trigger_ai": normalized["should_trigger_ai"],
        "is_first_ac": is_first_ac,
    }

    recommendation: dict[str, Any] | None = None
    try:
        row, created = await submission_event_repo.create_event(db, event_payload)

        if created and is_first_ac:
            try:
                recommender = SubmissionRecommendationService()
                recommendation = recommender.recommend_next_problem(
                    normalized["user_id"],
                    normalized["problem_id"],
                )
            except Exception as rec_exc:
                logger.warning(
                    "first_ac recommendation failed user=%s problem=%s err=%s",
                    normalized["user_id"],
                    normalized["problem_id"],
                    rec_exc,
                )

        await audit_repo.log_event(
            db,
            event_type="submission_fallback_received",
            request_id=getattr(request.state, "request_id", None),
            session_id=UUID(normalized["session_id"]) if normalized["session_id"] else None,
            user_id=normalized["user_id"],
            detail={
                "submission_id": normalized["submission_id"],
                "created": created,
                "status_label": normalized["status_label"],
                "is_first_ac": is_first_ac,
                "session_bound": bool(normalized["session_id"]),
            },
        )
        submission_fallback_events_total.labels(
            outcome="created" if created else "duplicate",
            status_label=normalized["status_label"],
            source=normalized["source"],
        ).inc()

        return SubmissionFallbackResponse(
            ok=True,
            created=created,
            event_id=row.id,
            event_type=row.event_type,
            event_version=row.event_version,
            summary_text=row.summary_text,
            should_trigger_ai=row.should_trigger_ai,
            is_first_ac=row.is_first_ac,
            recommendation=recommendation,
        )
    except Exception as exc:
        submission_fallback_events_total.labels(
            outcome="failed",
            status_label=normalized["status_label"],
            source=normalized["source"],
        ).inc()
        await db.rollback()
        await submission_event_repo.create_dlq(
            db,
            source=normalized["source"],
            payload=normalized,
            error_message=str(exc),
            retry_count=0,
        )
        raise HTTPException(status_code=500, detail="submission fallback ingest failed") from exc

@router.post("/retry-dlq", response_model=SubmissionRetryResponse)
async def retry_submission_dlq(
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
) -> SubmissionRetryResponse:
    """Replay unresolved DLQ rows by re-persisting normalized submission events."""
    stats = await replay_submission_dlq(db, limit=limit)
    return SubmissionRetryResponse(
        ok=True,
        scanned=stats["scanned"],
        replayed=stats["replayed"],
        failed=stats["failed"],
    )

