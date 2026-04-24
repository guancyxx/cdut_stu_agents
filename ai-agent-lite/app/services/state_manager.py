"""State management service — student state persistence and knowledge delta computation."""
import uuid
import logging
from typing import Dict, Any

from app.database import async_session
from app.repositories import session_repo
from app.config import settings

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
        # Return empty default state
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

    def compute_knowledge_delta(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare knowledge_graph_position before/after a conversation turn.

        Returns a dict with:
          - gained: topics newly introduced (mastery > 0 in after but absent/0 in before)
          - improved: topics where mastery increased (delta > threshold)
          - stable: topics with no meaningful change
          - weakened: topics where mastery decreased
          - before_summary: {topic: level} snapshot before
          - after_summary: {topic: level} snapshot after
        """
        before_kg = before.get("knowledge_graph_position", {}) or {}
        after_kg = after.get("knowledge_graph_position", {}) or {}
        DELTA_THRESHOLD = 0.05

        gained = {}
        improved = {}
        stable = {}
        weakened = {}

        all_topics = set(before_kg.keys()) | set(after_kg.keys())
        for topic in all_topics:
            b_val = before_kg.get(topic, 0.0)
            a_val = after_kg.get(topic, 0.0)
            diff = a_val - b_val

            if b_val == 0 and a_val > 0:
                gained[topic] = round(a_val, 3)
            elif diff > DELTA_THRESHOLD:
                improved[topic] = {"before": round(b_val, 3), "after": round(a_val, 3), "delta": round(diff, 3)}
            elif diff < -DELTA_THRESHOLD:
                weakened[topic] = {"before": round(b_val, 3), "after": round(a_val, 3), "delta": round(diff, 3)}
            else:
                stable[topic] = round(a_val, 3)

        return {
            "gained": gained,
            "improved": improved,
            "stable": stable,
            "weakened": weakened,
            "before_summary": {k: round(v, 3) for k, v in before_kg.items()},
            "after_summary": {k: round(v, 3) for k, v in after_kg.items()},
        }

    async def track_efficiency(self, session_id: str, response_time: float, complexity: str):
        """Track learning efficiency metrics."""
        state = await self.load_state(session_id)
        expected_time = {"easy": 2.0, "medium": 5.0, "hard": 10.0}.get(complexity, 5.0)
        efficiency = expected_time / max(response_time, 0.1)
        state["efficiency_trend"] = state.get("efficiency_trend", 1.0) * 0.8 + efficiency * 0.2
        await self.save_state(session_id, state)


# Singleton instance — stateless, safe to share across connections
state_manager = StateManager()