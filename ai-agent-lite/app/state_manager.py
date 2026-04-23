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
            if session_data and session_data.metadata:
                state_data = session_data.metadata.get("supervisor_state", {})
                # Convert back to StudentState object if needed
                return state_data
        
        # Return empty state if not found
        return {
            "current_problem_id": None,
            "submitted_code": None,
            "knowledge_graph_position": {},
            "emotion_tags": {},
            "efficiency_trend": 1.0
        }
    
    async def save_state(self, session_id: str, state: Dict[str, Any]):
        """Save state to database."""
        async with async_session() as db:
            session_obj = await session_repo.get_session(db, uuid.UUID(session_id))
            if session_obj:
                # Update metadata with state
                if not session_obj.metadata:
                    session_obj.metadata = {}
                session_obj.metadata["supervisor_state"] = state
                session_obj.updated_at = datetime.utcnow()
                await db.commit()
    
    def _state_to_dict(self, state) -> Dict[str, Any]:
        """Convert StudentState to dictionary."""
        return {
            "current_problem_id": state.current_problem_id,
            "submitted_code": state.submitted_code,
            "knowledge_graph_position": state.knowledge_graph_position,
            "emotion_tags": state.emotion_tags,
            "efficiency_trend": state.efficiency_trend
        }
    
    def update_from_context(self, state: Dict[str, Any], context: Dict[str, Any]):
        """Update state based on current context."""
        if "problem_id" in context:
            state["current_problem_id"] = context["problem_id"]
        if "submitted_code" in context:
            state["submitted_code"] = context["submitted_code"]
        if "language" in context:
            state["language"] = context["language"]
    
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