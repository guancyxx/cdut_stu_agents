"""Async CRUD for sessions table."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Session


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
        .values(status="archived", updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def find_recent_active_session(
    db: AsyncSession,
    user_id: str,
    problem_id: str,
    within_minutes: int = 180,
) -> Session | None:
    """Find a recent active session for the same user/problem to bind fallback events."""
    if not user_id or not problem_id:
        return None

    threshold = datetime.now(timezone.utc) - timedelta(minutes=max(1, within_minutes))
    result = await db.execute(
        select(Session)
        .where(
            Session.user_id == user_id,
            Session.problem_id == problem_id,
            Session.status == "active",
            Session.updated_at >= threshold,
        )
        .order_by(Session.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
