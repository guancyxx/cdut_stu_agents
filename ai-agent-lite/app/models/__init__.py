"""Domain models package.

Re-exports public API for backward compatibility:
  - ORM models (Base, Session, Message, AuditLog)
  - Data models (StudentState, AgentResponse)
  - Enumerations (AgentType, CompletionStatus, ErrorCode)
  - WS message validation (WsQueryMessage, WsRawMessage)
"""
from app.models.orm import Base, Session, Message, AuditLog
from app.models.schemas import StudentState, AgentResponse
from app.models.enums import AgentType, CompletionStatus, ErrorCode
from app.models.ws_messages import WsQueryMessage, WsRawMessage, WsQueryContent

__all__ = [
    "Base", "Session", "Message", "AuditLog",
    "StudentState", "AgentResponse",
    "AgentType", "CompletionStatus", "ErrorCode",
    "WsQueryMessage", "WsRawMessage", "WsQueryContent",
]