"""
State management and persistence for supervisor pattern.
Integrated with existing PostgreSQL storage.
"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.repositories import session_repo, message_repo
from app.models import Session, Message

class StateManager:
    """Manages student state with persistent storage."""
    
    def __init__(self):
        self.active_states = {}  # session_id -> StudentState
    
    async def load_state(self, session_id: str) -> Dict[str, Any]:
        """Load state from database or create new."""
        if session_id in self.active_states:
            return self._state_to_dict(self.active_states[session_id])
        
        # Load from database
        async with async_session() as db:
            session_data = await session_repo.get_session(db, uuid.UUID(session_id))
            if session_data and session_data.supervisor_state:
                state_data = session_data.supervisor_state
                # Convert back to StudentState object if needed
                return state_data
        
        # Return empty state if not found
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
        async with async_session() as db:
            session_obj = await session_repo.get_session(db, uuid.UUID(session_id))
            if session_obj:
                # Update supervisor state directly
                session_obj.supervisor_state = state
                session_obj.updated_at = datetime.utcnow()
                await db.commit()
    
    def _state_to_dict(self, state) -> Dict[str, Any]:
        """Convert StudentState to dictionary."""
        return {
            "current_problem_id": state.current_problem_id,
            "submitted_code": state.submitted_code,
            "knowledge_graph_position": state.knowledge_graph_position,
            "emotion_tags": state.emotion_tags,
            "efficiency_trend": state.efficiency_trend,
            "last_agent_type": state.last_agent_type,
            "current_problem_context": getattr(state, "current_problem_context", ""),
        }
    
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
        # This would integrate with proper metrics system
        # For now, simple tracking
        state = await self.load_state(session_id)
        
        # Simple efficiency calculation (would be more sophisticated)
        expected_time = {"easy": 2.0, "medium": 5.0, "hard": 10.0}.get(complexity, 5.0)
        efficiency = expected_time / max(response_time, 0.1)
        
        state["efficiency_trend"] = state.get("efficiency_trend", 1.0) * 0.8 + efficiency * 0.2
        await self.save_state(session_id, state)

# Singleton instance
state_manager = StateManager()