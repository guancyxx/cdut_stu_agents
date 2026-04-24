"""Session management service — creation, resolution, and context loading."""
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import session_repo, message_repo
from app.config import settings

logger = logging.getLogger("ai-agent-lite.session")


async def get_or_create_session(
    db: AsyncSession,
    session_id_str: str,
    user_id: str,
) -> tuple:
    """Load existing session or create a new one. Returns (session_id_uuid, is_new)."""
    try:
        sid = uuid.UUID(session_id_str)
        existing = await session_repo.get_session(db, sid)
        if existing and existing.user_id == user_id:
            return existing.id, False
    except (ValueError, AttributeError):
        pass

    new_session = await session_repo.create_session(db, user_id=user_id)
    return new_session.id, True


async def load_context(db: AsyncSession, session_id: uuid.UUID) -> list[dict]:
    """Load recent messages as LLM context dicts."""
    return await message_repo.list_messages_as_dicts(db, session_id, limit=settings.max_context_messages)


def extract_problem_context(messages: list[dict]) -> str:
    """Extract the most recent problem context message from conversation history.

    The frontend sends a structured message starting with
    "SYSTEM CONTEXT: OJ problem has been selected." when the student
    selects a problem. We find the latest one and return it so
    all agents stay anchored to the current problem.

    Returns empty string if no problem context message is found.
    """
    if not messages:
        return ""
    for msg in reversed(messages):
        content = str(msg.get("content", ""))
        if content.startswith("SYSTEM CONTEXT:"):
            return content
    return ""