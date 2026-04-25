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
    # timeouts
    task_soft_time_limit=int(settings.ollama_timeout) + 30,
    task_time_limit=int(settings.ollama_timeout) + 60,
    # result expiry — audit results kept for 7 days
    result_expires=86400 * 7,
    # route all audit tasks to the audit queue
    task_routes={"app.tasks.problem_auditor.*": {"queue": "audit"}},
    # Beat schedule: audit one problem every 10 minutes
    beat_schedule={
        "audit-next-problem-every-10-min": {
            "task": "app.tasks.problem_auditor.audit_next_problem",
            "schedule": 600,  # 600 seconds = 10 minutes
        },
    },
)

# Explicitly import task modules so they register with this Celery app.
# autodiscover_tasks relies on a specific package layout that may not
# resolve correctly inside Docker containers; explicit imports are more robust.
celery_app.autodiscover_tasks(["app.tasks"], related_name=None)
# Also force-import to guarantee registration
from app.tasks import problem_auditor  # noqa: E402, F401