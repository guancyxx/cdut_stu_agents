"""Local user model for ai-agent-lite compatible auth endpoints."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.config import settings
from app.models.orm import Base


class LocalUser(Base):
    __tablename__ = "local_users"
    __table_args__ = {"schema": settings.db_schema}

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True, index=True)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), nullable=True)
    admin_type = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
