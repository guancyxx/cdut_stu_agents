"""Submission model for CDUT OJ.

Replaces QDUOJ's submission table with a dedicated ai_agent.submission.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.orm import Base
from app.config import settings


class Submission(Base):
    """Code submission record — created when a user submits code for judging."""

    __tablename__ = "submissions"
    __table_args__ = {"schema": settings.db_schema}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    language = Column(String(16), nullable=False)
    code = Column(Text, nullable=False)
    verdict = Column(String(8), nullable=True)
    time_sec = Column(Float, nullable=True)
    memory_kb = Column(Integer, nullable=True)
    test_case_results = Column(JSONB, nullable=True)
    compile_error = Column(Text, nullable=True)
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
