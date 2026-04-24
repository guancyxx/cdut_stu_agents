"""Problem Analyzer Agent — deep analysis of competition problems and solution guidance."""
import logging
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block

logger = logging.getLogger("ai-agent-lite.workers.problem_analyzer")


class ProblemAnalyzerAgent(BaseWorker):
    """Deep analysis of competition problems and solution guidance."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        problem_id = state.get("current_problem_id", "unknown")

        history_block = build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (for context — the student may be "
                f"continuing a discussion about this problem):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = build_problem_anchor_block(state)

        prompt = (
            f"As a programming competition problem expert, help the student through this problem step by step.\n"
            f"{problem_anchor}\n"
            f"Problem Context: {problem_id}\n"
            f"Student's Question: {user_input}\n"
            f"{history_section}"
            "MICRO-STEP TEACHING RULES:\n"
            "- Do NOT provide a full analysis covering everything at once. You are a coach, not a textbook.\n"
            "- Each turn, cover only ONE small aspect of the problem.\n"
            "- ALWAYS end your response with a concrete question or micro-task.\n"
            "- NEVER reveal the full solution approach unless the student has been stuck on the same point 3+ times.\n"
            "- When the student answers your question, evaluate it first, then advance to the next micro-step.\n"
            "- Do NOT give numbered lists of all aspects — that is lecturing, not coaching.\n"
            "- Be brief. One concept → one question. That is one turn.\n\n"
            "IMPORTANT: If the conversation history shows the student is answering a "
            "previous question or trying an exercise, respond to THEIR answer first "
            "(evaluate correctness, give feedback), then advance to the NEXT micro-step.\n"
            "Do NOT restart the explanation from scratch as if this is a new conversation.\n\n"
            "Focus on teaching problem-solving thinking, not just giving answers."
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"problem_id": problem_id, "analysis_depth": "detailed"},
            )
        except Exception as e:
            logger.error(f"Problem analysis failed: {e}")
            return AgentResponse(
                content="Problem analysis temporarily unavailable.",
                status=CompletionStatus.ERROR,
            )