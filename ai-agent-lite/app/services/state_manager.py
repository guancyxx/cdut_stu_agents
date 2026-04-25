"""State management service — student state persistence only.

Knowledge delta computation has been moved to
app.services.knowledge_delta.compute_knowledge_delta().
"""
import uuid
import logging
from typing import Dict, Any

from app.database import async_session
from app.repositories import session_repo

logger = logging.getLogger("ai-agent-lite.state_manager")


class StateManager:
    """Manages student state with persistent PostgreSQL storage.

    No in-memory cache — each load/save goes directly to the database
    to avoid stale state and memory leaks.
    """

    async def load_state(self, session_id: str) -> Dict[str, Any]:
        """Load state from database or return default empty state."""
        async with async_session() as db:
            session_data = await session_repo.get_session(db, uuid.UUID(session_id))
            if session_data and session_data.supervisor_state:
                return session_data.supervisor_state
        return {
            "current_problem_id": None,
            "submitted_code": None,
            "knowledge_graph_position": {},
            "emotion_tags": {},
            "efficiency_trend": 1.0,
            "last_agent_type": None,
            "current_problem_context": "",
        }

    async def save_state(self, session_id: str, state: Dict[str, Any]):
        """Save state to database."""
        from datetime import datetime, timezone
        async with async_session() as db:
            session_obj = await session_repo.get_session(db, uuid.UUID(session_id))
            if session_obj:
                session_obj.supervisor_state = state
                session_obj.updated_at = datetime.now(timezone.utc)
                await db.commit()

    def update_from_context(self, state: Dict[str, Any], context: Dict[str, Any]):
        """Update state based on current context."""
        if "problem_id" in context:
            state["current_problem_id"] = context["problem_id"]
        if "submitted_code" in context:
            state["submitted_code"] = context["submitted_code"]
        if "language" in context:
            state["language"] = context["language"]
        if "last_agent_type" in context and context["last_agent_type"]:
            state["last_agent_type"] = context["last_agent_type"]
        if "problem_context" in context and context["problem_context"]:
            state["current_problem_context"] = context["problem_context"]

    @staticmethod
    def compute_knowledge_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to the standalone compute_knowledge_delta function."""
        from app.services.knowledge_delta import compute_knowledge_delta as _compute
        return _compute(before, after)

    async def track_efficiency(self, session_id: str, response_time: float, complexity: str):
        """Track learning efficiency metrics."""
        state = await self.load_state(session_id)
        expected_time = {"easy": 2.0, "medium": 5.0, "hard": 10.0}.get(complexity, 5.0)
        efficiency = expected_time / max(response_time, 0.1)
        state["efficiency_trend"] = state.get("efficiency_trend", 1.0) * 0.8 + efficiency * 0.2
        await self.save_state(session_id, state)


# Singleton instance — stateless, safe to share across connections
state_manager = StateManager()