"""
SQLAlchemy ORM models for ai-agent-lite persistence.
Uses a dedicated schema in the shared QDUOJ PostgreSQL instance.
"""
import os
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase
import uuid

_SCHEMA = os.getenv("LITE_DB_SCHEMA", "ai_agent")


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": _SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), nullable=False, index=True)
    problem_id = Column(String(32), nullable=True, index=True)
    title = Column(String(256), nullable=True)
    status = Column(String(16), nullable=False, default="active")
    supervisor_state = Column(JSONB, nullable=True)  # For supervisor state storage
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_session_created", "session_id", "created_at"),
        {"schema": _SCHEMA},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    msg_type = Column(String(16), nullable=False, default="text")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_time", "created_at"),
        {"schema": _SCHEMA},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(64), nullable=True)
    event_type = Column(String(32), nullable=False, index=True)
    detail = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)