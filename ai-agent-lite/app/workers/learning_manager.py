"""Learning Manager Agent — micro-stepping learning coach for atomic concept delivery."""
import logging
from string import Template
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block
from app.prompts import get_prompt
from app.i18n import ERROR_FALLBACK

logger = logging.getLogger("ai-agent-lite.workers.learning_manager")


class LearningManagerAgent(BaseWorker):
    """Micro-stepping learning coach that guides students through atomic tasks."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        knowledge_graph = state.get("knowledge_graph_position", {})
        efficiency = state.get("efficiency_trend", 1.0)
        emotion_tags = state.get("emotion_tags", {})
        problem_id = state.get("current_problem_id", "unknown")

        emotion_context = ""
        if emotion_tags:
            emotion_items = ", ".join(f"{k}={v:.1f}" for k, v in emotion_tags.items() if v > 0.2)
            if emotion_items:
                emotion_context = f"\nStudent emotional signals: {emotion_items}"

        frustration_level = ""
        if efficiency < 0.7:
            frustration_level = (
                "\n[IMPORTANT] The student's efficiency trend is declining. "
                "Simplify immediately — drop to a foundational concept, "
                "use a very small concrete example, and avoid any abstraction."
            )
        elif emotion_tags.get("frustration", 0) > 0.5 or emotion_tags.get("confusion", 0) > 0.6:
            frustration_level = (
                "\n[IMPORTANT] The student shows frustration or confusion. "
                "Slow down. Reassure briefly that the current difficulty is normal. "
                "Then offer a simpler, more concrete anchoring question."
            )

        history_block = build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                "\nConversation history (the teaching dialogue so far):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = build_problem_anchor_block(state)

        template_text = get_prompt("learning_manager")
        prompt = Template(template_text).safe_substitute(
            knowledge_graph=knowledge_graph or "new student",
            problem_id=problem_id,
            efficiency=f"{efficiency:.2f}",
            emotion_context=emotion_context,
            frustration_level=frustration_level,
            problem_anchor=problem_anchor,
            history_section=history_section,
            user_input=user_input,
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"plan_type": "micro_step_coaching", "efficiency_factor": efficiency},
            )
        except Exception as e:
            logger.error(f"Learning management failed: {e}")
            return AgentResponse(
                content=ERROR_FALLBACK.get("learning_manager", "Request failed, please try again later."),
                status=CompletionStatus.ERROR,
            )