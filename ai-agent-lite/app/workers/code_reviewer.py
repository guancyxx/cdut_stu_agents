"""Code Reviewer Agent — specialized in code quality, efficiency, and style evaluation."""
import logging
from typing import Dict, Any, List

from app.workers.base import BaseWorker
from app.models.schemas import AgentResponse, CompletionStatus
from app.utils.prompt_helpers import build_history_block, build_problem_anchor_block
from app.prompts import get_prompt

logger = logging.getLogger("ai-agent-lite.workers.code_reviewer")

_INLINE_PROMPT = (
    "As an expert code reviewer for programming competitions, analyze this {language} code.\n"
    "{problem_anchor}\nProblem ID: {problem_id}\n\n"
    "Code:\n```{language}\n{code}\n```\n\n"
    "Student's question: {user_input}\n{history_section}"
    "MICRO-STEP TEACHING RULES:\n"
    "- Do NOT dump all analysis in one response. Cover ONE aspect per turn only.\n"
    "- Start with the most critical issue (logic correctness).\n"
    "- ALWAYS end with a concrete question or micro-task for the student.\n"
    "- NEVER give the complete corrected code unless the student has asked 3+ times.\n"
    "- Briefly evaluate → give a hint → ask them to act.\n\n"
    "If the student is answering a question from the conversation history, "
    "evaluate their answer directly and concisely, then advance to the next aspect."
)


class CodeReviewerAgent(BaseWorker):
    """Specialized in code quality, efficiency, and style evaluation."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        code = state.get("submitted_code", "")
        language = state.get("language", "unknown")
        problem_id = state.get("current_problem_id", "unknown")

        history_block = build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (for context — the student may be "
                f"responding to a previous question about this code):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = build_problem_anchor_block(state)

        template = get_prompt("code_reviewer") or _INLINE_PROMPT
        prompt = template.format(
            language=language, code=code, problem_id=problem_id,
            user_input=user_input, history_section=history_section,
            problem_anchor=problem_anchor,
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"analysis_type": "code_review", "language": language},
            )
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return AgentResponse(
                content="Code analysis temporarily unavailable.",
                status=CompletionStatus.ERROR,
            )