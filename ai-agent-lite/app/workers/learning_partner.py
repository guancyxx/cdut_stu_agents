"""Learning Partner Agent — provides warm, targeted emotional support and positive framing."""
import logging
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block

logger = logging.getLogger("ai-agent-lite.workers.learning_partner")


class LearningPartnerAgent(BaseWorker):
    """Provides warm, targeted emotional support and positive framing.

    Unlike the old keyword-driven approach, this agent receives LLM-analyzed
    emotion scores and crafts a response that directly addresses the student's
    specific emotional state. It never lists generic advice; it speaks to the
    student as a real person.
    """

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

        prompt = (
            "You are a supportive learning companion for a programming-competition "
            "student.\n\n"
            f"Student says: {user_input}\n"
            f"Detected emotional state: {emotion_desc}\n"
            f"{problem_anchor}"
            f"{history_section}"
            "Rules:\n"
            "- CRITICAL: Do NOT start teaching or coaching unless the student explicitly asks for help. "
            "If the student is just greeting, chatting, or making small talk, respond as a friendly "
            "conversation partner — be natural, warm, and brief. No teaching, no problem analysis, "
            "no suggestions about algorithms or exercises.\n"
            "- If the student DOES explicitly ask for help with a problem or concept, briefly encourage "
            "them and then suggest they ask the specific question — but let them lead.\n"
            "- If frustrated: acknowledge the difficulty honestly, don't say it's "
            "easy. Share that this specific struggle is a normal stage.\n"
            "- If confused: reassure that confusion means learning is happening. "
            "Offer one tiny concrete thing to try.\n"
            "- If excited: match their energy briefly, then let them continue.\n"
            "- If neutral: be a calm, steady presence. No forced enthusiasm.\n"
            "- Keep it short — 2-3 sentences max.\n"
            "- Do NOT give a list of generic advice. Talk like a real person.\n"
            "- If the conversation history shows the student was in the middle of "
            "a learning exercise, briefly acknowledge their emotional state then "
            "help them get back on track with that exercise.\n"
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