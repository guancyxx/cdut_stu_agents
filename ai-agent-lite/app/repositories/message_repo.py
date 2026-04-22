"""
Async CRUD for messages table.
"""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def create_message(
    db: AsyncSession,
    session_id: UUID,
    role: str,
    content: str,
    msg_type: str = "text",
) -> Message:
    """Append a message to a session."""
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        msg_type=msg_type,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_messages(
    db: AsyncSession,
    session_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[Message]:
    """List messages for a session, oldest first."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_messages(db: AsyncSession, session_id: UUID) -> int:
    """Count messages in a session."""
    result = await db.execute(
        select(func.count()).where(Message.session_id == session_id)
    )
    return result.scalar_one()


async def list_messages_as_dicts(
    db: AsyncSession,
    session_id: UUID,
    limit: int = 100,
) -> list[dict]:
    """Return messages as role/content dicts suitable for LLM context."""
    msgs = await list_messages(db, session_id, limit=limit)
    return [{"role": m.role, "content": m.content} for m in msgs]