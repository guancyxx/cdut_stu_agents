"""Celery tasks for submission-event fallback compensation."""
from __future__ import annotations

import asyncio
import logging

from app.celery_app import celery_app
from app.database import async_session
from app.metrics import submission_dlq_replay_runs_total
from app.services.submission_dlq_replay import replay_submission_dlq

logger = logging.getLogger("ai-agent-lite.submission-events-task")


@celery_app.task(
    name="app.tasks.submission_events.retry_submission_dlq",
    bind=True,
    queue="audit",
    max_retries=3,
    soft_time_limit=120,
    time_limit=180,
)
def retry_submission_dlq_task(self, limit: int = 20) -> dict:
    """Replay unresolved submission-event DLQ rows in background."""

    async def _run() -> dict:
        async with async_session() as db:
            return await replay_submission_dlq(db, limit=limit)

    try:
        stats = asyncio.run(_run())
        logger.info(
            "submission dlq replay completed scanned=%s replayed=%s failed=%s",
            stats.get("scanned", 0),
            stats.get("replayed", 0),
            stats.get("failed", 0),
        )
        return {
            "ok": True,
            "scanned": int(stats.get("scanned", 0)),
            "replayed": int(stats.get("replayed", 0)),
            "failed": int(stats.get("failed", 0)),
        }
    except Exception as exc:
        submission_dlq_replay_runs_total.labels(outcome="task_failed").inc()
        logger.exception("submission dlq replay task failed")
        raise self.retry(exc=exc, countdown=60)
