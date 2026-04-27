"""SQLAlchemy ORM models for ai-agent-lite persistence.

Uses a dedicated schema in the shared QDUOJ PostgreSQL instance.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


class Session(Base):  # noqa: A003 — shadowing builtins is intentional for ORM
    __tablename__ = "sessions"
    __table_args__ = {"schema": settings.db_schema}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), nullable=False, index=True)
    problem_id = Column(String(32), nullable=True, index=True)
    title = Column(String(256), nullable=True)
    status = Column(String(16), nullable=False, default="active")
    supervisor_state = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_session_created", "session_id", "created_at"),
        {"schema": settings.db_schema},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    msg_type = Column(String(16), nullable=False, default="text")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_time", "created_at"),
        {"schema": settings.db_schema},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(64), nullable=True)
    event_type = Column(String(32), nullable=False, index=True)
    detail = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ProblemAudit(Base):
    """Audit records for OJ problem quality checks by LLM.

    Each row records the result of one audit pass for a problem.
    The auditor skips problems that already have a 'pass' status
    unless the force flag is set.
    """
    __tablename__ = "problem_audit"
    __table_args__ = (
        Index("idx_problem_audit_display_id", "problem_display_id"),
        Index("idx_problem_audit_status", "status"),
        {"schema": settings.db_schema},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    problem_display_id = Column(String(64), nullable=False, index=True)
    problem_db_id = Column(BigInteger, nullable=False)
    # Audit result: pass | fail | error | fix_failed
    status = Column(String(32), nullable=False, default="pending")
    # JSON list of issue descriptions
    issues = Column(JSONB, nullable=True)
    # JSON dict of LLM-suggested fixes
    fixes = Column(JSONB, nullable=True)
    # Raw LLM response for debugging
    llm_raw_response = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SubmissionEvent(Base):
    """Normalized OJ submission event snapshots for learning-state updates."""

    __tablename__ = "submission_events"
    __table_args__ = (
        UniqueConstraint("submission_id", "event_type", "event_version", name="uq_submission_event_idem"),
        Index("idx_submission_events_user_created", "user_id", "created_at"),
        Index("idx_submission_events_session_created", "session_id", "created_at"),
        Index("idx_submission_events_problem_created", "problem_id", "created_at"),
        {"schema": settings.db_schema},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    problem_id = Column(String(64), nullable=False, index=True)
    submission_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, default="submission.finalized")
    event_version = Column(String(16), nullable=False, default="v1")
    source = Column(String(16), nullable=False, default="frontend_fb")
    status_code = Column(Integer, nullable=True)
    status_label = Column(String(64), nullable=False)
    language = Column(String(32), nullable=True)
    score = Column(Integer, nullable=False, default=0)
    time_cost_ms = Column(Integer, nullable=False, default=0)
    memory_cost_kb = Column(Integer, nullable=False, default=0)
    test_cases_total = Column(Integer, nullable=False, default=0)
    test_cases_passed = Column(Integer, nullable=False, default=0)
    summary_text = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    should_trigger_ai = Column(Boolean, nullable=False, default=True)
    is_first_ac = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class SubmissionEventDLQ(Base):
    """Dead-letter queue rows for submission events that failed processing."""

    __tablename__ = "submission_event_dlq"
    __table_args__ = (
        Index("idx_submission_event_dlq_created", "created_at"),
        {"schema": settings.db_schema},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source = Column(String(16), nullable=False, default="frontend_fb")
    payload = Column(JSONB, nullable=False)
    error_message = Column(Text, nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
