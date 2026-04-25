"""Problem Analyzer Agent — deep analysis of competition problems and solution guidance."""
import logging
from string import Template
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block
from app.prompts import get_prompt

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

        template_text = get_prompt("problem_analyzer")
        prompt = Template(template_text).safe_substitute(
            problem_id=problem_id, user_input=user_input,
            history_section=history_section, problem_anchor=problem_anchor,
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