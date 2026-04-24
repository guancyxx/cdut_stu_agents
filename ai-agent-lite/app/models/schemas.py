"""Pydantic-style data models for in-memory state transfer.

These are plain dataclasses used across services; not ORM models.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.models.enums import CompletionStatus


@dataclass
class StudentState:
    """Student learning state carried across conversation turns."""
    current_problem_id: Optional[str] = None
    submitted_code: Optional[str] = None
    knowledge_graph_position: Dict[str, float] = field(default_factory=dict)
    emotion_tags: Dict[str, float] = field(default_factory=dict)
    efficiency_trend: float = 1.0
    session_start_time: Optional[datetime] = None
    last_activity_time: Optional[datetime] = None
    last_agent_type: Optional[str] = None
    current_problem_context: str = ""


@dataclass
class AgentResponse:
    """Structured response from a worker agent."""
    content: str
    status: CompletionStatus = CompletionStatus.COMPLETE
    metadata: Dict[str, object] = field(default_factory=dict)
    next_actions: List[Dict[str, str]] = field(default_factory=list)