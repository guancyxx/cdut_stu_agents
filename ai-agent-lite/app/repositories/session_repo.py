"""
Async CRUD for sessions table.
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session


async def create_session(
    db: AsyncSession,
    user_id: str,
    problem_id: str | None = None,
    title: str | None = None,
) -> Session:
    """Create a new session and return it."""
    session = Session(
        id=uuid4(),
        user_id=user_id,
        problem_id=problem_id,
        title=title,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: UUID) -> Session | None:
    """Load a session by id. Returns None if not found."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def list_sessions_by_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
) -> list[Session]:
    """List active sessions for a user, most recent first."""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def archive_session(db: AsyncSession, session_id: UUID) -> None:
    """Mark a session as archived."""
    await db.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(status="archived", updated_at=datetime.utcnow())
    )
    await db.commit()