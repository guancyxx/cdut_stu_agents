"""Pydantic models for WebSocket inbound message validation.

All WS messages are parsed through these models before reaching
business logic — invalid structure is rejected early with a clear error.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class WsQueryContent(BaseModel):
    """Inner 'content' payload for a query message."""
    query: str = Field(..., min_length=1, max_length=5000, description="User query text")

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()


class WsQueryMessage(BaseModel):
    """Standard query message from client."""
    type: str = Field("query", pattern=r"^query$")
    content: WsQueryContent
    session_id: Optional[str] = Field(None, max_length=64)


class WsListAgentsMessage(BaseModel):
    """List-agents request — no payload required."""
    type: str = Field(..., pattern=r"^list_agents$")


class WsRawMessage(BaseModel):
    """Loose inbound message for initial parsing.

    Validates only the 'type' field; content is validated
    downstream depending on the type.
    """
    type: str = Field(..., pattern=r"^(query|list_agents)$")

    class Config:
        extra = "allow"