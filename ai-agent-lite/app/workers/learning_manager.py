"""Learning Manager Agent — micro-stepping learning coach for atomic concept delivery."""
import logging
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block

logger = logging.getLogger("ai-agent-lite.workers.learning_manager")


class LearningManagerAgent(BaseWorker):
    """Micro-stepping learning coach that guides students through atomic tasks.

    This agent does NOT produce full lesson plans or information dumps.
    Instead, it follows a strict THOUGHT → GUIDANCE → INTERACTION protocol,
    delivering one atomic concept per turn and always ending with a question
    or micro-exercise that requires the student's active response.
    """

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

        prompt = (
            "You are a pragmatic, precise programming-competition learning coach. "
            "Your role is to guide students through micro-steps, NOT to lecture.\n\n"
            "ABSOLUTE RULES:\n"
            "- NEVER dump large amounts of information in one turn. Cover only 1 concept "
            "or 1 exercise per turn, keeping your response concise and focused.\n"
            "- NEVER list more than 1 new concept or 1 exercise per turn.\n"
            "- NEVER give complete source code unless the student has asked 3+ times "
            "on the same logical point.\n"
            "- NEVER use empty praise like \"太棒了\" or \"令人惊叹\". Evaluate logic and "
            "code efficiency, not effort.\n"
            "- ALWAYS end your response with a concrete question or micro-task "
            "that requires the student to act. No exceptions.\n"
            "- Be warm and patient. Acknowledge struggle honestly — don't pretend "
            "difficult things are easy.\n"
            "- When a student is wrong, point out the specific gap and provide a "
            "minimal hint, not the full correction.\n\n"
            f"{problem_anchor}"
            f"Student's current knowledge profile: {knowledge_graph or 'new student'}\n"
            f"Current problem: {problem_id}\n"
            f"Efficiency trend: {efficiency:.2f}{emotion_context}{frustration_level}\n"
            f"{history_section}"
            f"Student says: {user_input}\n\n"
            "CRITICAL: If the conversation history shows you previously asked the student "
            "a question or gave them an exercise, the student's current message is likely "
            "their ANSWER to that question. In that case:\n"
            "- Evaluate their answer first (correct/partially correct/wrong)\n"
            "- Give targeted feedback on their specific answer\n"
            "- Then give the NEXT micro-step or question\n"
            "- Do NOT repeat the previous question or restart the explanation\n"
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
                content="暂时无法响应，请稍后再试。",
                status=CompletionStatus.ERROR,
            )