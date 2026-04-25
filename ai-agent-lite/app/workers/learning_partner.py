"""Learning Partner Agent — provides warm, targeted emotional support and positive framing."""
import logging
from string import Template
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block
from app.prompts import get_prompt

logger = logging.getLogger("ai-agent-lite.workers.learning_partner")


class LearningPartnerAgent(BaseWorker):
    """Provides warm, targeted emotional support and positive framing."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        emotional_state = state.get("emotion_tags", {})

        emotion_desc = ", ".join(
            f"{k}={v:.1f}" for k, v in emotional_state.items() if v > 0.2
        ) if emotional_state else "neutral"

        history_block = build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (so you understand what the student has been through):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = build_problem_anchor_block(state)

        template_text = get_prompt("learning_partner")
        prompt = Template(template_text).safe_substitute(
            user_input=user_input, emotion_desc=emotion_desc,
            problem_anchor=problem_anchor, history_section=history_section,
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"support_type": "emotional", "emotional_state": emotional_state},
            )
        except Exception as e:
            logger.error(f"Learning partner response failed: {e}")
            return AgentResponse(
                content="我在这儿，随时可以继续。",
                status=CompletionStatus.COMPLETE,
            )