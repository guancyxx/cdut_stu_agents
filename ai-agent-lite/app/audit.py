"""
Async audit logger for ai-agent-lite.
Writes to the audit_log table without blocking the WS handler.
"""
import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

logger = logging.getLogger("ai-agent-lite.audit")


async def log_event(
    db: AsyncSession,
    event_type: str,
    request_id: UUID | None = None,
    session_id: UUID | None = None,
    user_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """Write an audit log entry. Called with fire-and-forget semantics."""
    try:
        entry = AuditLog(
            request_id=request_id or uuid4(),
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            detail={k: v for k, v in (detail or {}).items() if _is_safe_key(k)},
            created_at=datetime.utcnow(),
        )
        db.add(entry)
        await db.commit()
    except Exception:
        logger.exception("Failed to write audit log for event_type=%s", event_type)
        # Non-blocking: swallow to avoid crashing the WS handler
        await db.rollback()


# Keys that should never appear in audit detail (PII / secrets)
_BLOCKED_KEYS = {"password", "secret", "token", "api_key", "authorization", "cookie"}


def _is_safe_key(key: str) -> bool:
    return key.lower() not in _BLOCKED_KEYS