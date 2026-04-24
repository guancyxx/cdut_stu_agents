"""Base worker class and shared data models for specialized agents."""
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, field

from app.models.enums import CompletionStatus

logger = logging.getLogger("ai-agent-lite.workers")


class BaseWorker:
    """Base class for all specialized workers."""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> "AgentResponse":
        """Process user input and return structured response."""
        raise NotImplementedError