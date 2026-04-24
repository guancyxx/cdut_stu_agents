"""Contest Coach Agent — simulates competition pressure and provides strategic advice."""
import logging
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block

logger = logging.getLogger("ai-agent-lite.workers.contest_coach")


class ContestCoachAgent(BaseWorker):
    """Simulates competition pressure and provides strategic advice."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        history_block = build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (for context):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = build_problem_anchor_block(state)

        prompt = (
            f"As a programming competition coach, provide strategic advice.\n"
            f"{problem_anchor}\n"
            f"Student's Situation: {user_input}\n"
            f"{history_section}"
            "MICRO-STEP TEACHING RULES:\n"
            "- Do NOT list all strategies at once. Cover ONE concrete tip or strategy per turn.\n"
            "- ALWAYS end with a concrete question or small action for the student.\n"
            "- When the student follows up, evaluate their thinking, then give the next tip.\n"
            "- Be competitive but supportive. Brief and direct.\n\n"
            "If the student is following up on previous coaching advice, respond to "
            "their specific situation first, then advance to the next strategy point."
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"coaching_type": "contest_strategy"},
            )
        except Exception as e:
            logger.error(f"Contest coaching failed: {e}")
            return AgentResponse(
                content="Competition coaching temporarily unavailable.",
                status=CompletionStatus.ERROR,
            )