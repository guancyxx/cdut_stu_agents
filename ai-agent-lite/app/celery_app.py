"""Celery application instance for ai-agent-lite background tasks.

The worker process runs this as its entry point:
    celery -A app.celery_app worker --loglevel=info -Q audit

Beat scheduler for periodic tasks:
    celery -A app.celery_app beat --loglevel=info
"""
import logging

from celery import Celery

from app.config import settings

logger = logging.getLogger("ai-agent-lite.celery")

celery_app = Celery(
    "ai-agent-lite",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # concurrency — single worker processes one task at a time
    worker_concurrency=1,
    # timeouts (matched to audit LLM provider speed)
    task_soft_time_limit=int(settings.audit_llm_timeout) + 60,
    task_time_limit=int(settings.audit_llm_timeout) + 120,
    # result expiry — audit results kept for 7 days
    result_expires=86400 * 7,
    # route all background tasks to the audit queue
    task_routes={
        "app.tasks.problem_auditor.*": {"queue": "audit"},
        "app.tasks.submission_events.*": {"queue": "audit"},
    },
    # Beat schedule: periodic problem audit + submission fallback compensation
    beat_schedule={
        "audit-next-problem-every-100s": {
            "task": "app.tasks.problem_auditor.audit_next_problem",
            "schedule": settings.audit_beat_interval,  # ~100s → 3 audits / 5 min
        },
        "retry-submission-dlq-every-5-min": {
            "task": "app.tasks.submission_events.retry_submission_dlq",
            "schedule": 300,
            "kwargs": {"limit": 20},
        },
    },
)

# Explicitly import task modules so they register with this Celery app.
# autodiscover_tasks relies on a specific package layout that may not
# resolve correctly inside Docker containers; explicit imports are more robust.
celery_app.autodiscover_tasks(["app.tasks"], related_name=None)
# Also force-import to guarantee registration
from app.tasks import problem_auditor, submission_events  # noqa: E402, F401