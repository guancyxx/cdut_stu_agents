"""Contest Coach Agent — simulates competition pressure and provides strategic advice."""
import logging
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block
from app.prompts import get_prompt

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

        template = get_prompt("contest_coach")
        prompt = template.format(
            user_input=user_input, history_section=history_section,
            problem_anchor=problem_anchor,
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