"""Intent classification service — LLM-based intent recognition with context awareness."""
import logging
from string import Template
from typing import Dict, List

from app.prompts import get_prompt

logger = logging.getLogger("ai-agent-lite.intent_classifier")

# Fallback used only when prompts/intent_classifier.md is missing
_INLINE_PROMPT = (
    "Classify the student's intent from a programming competition training session.\n"
    "Current problem: $problem_hint\n"
    "Current student message: \"$user_input\"\n"
    "Previous conversation (most recent messages):\n$history_summary\n"
    "Previous AI agent: $last_agent_ctx\n"
    "Return ONLY the intent name (one word or phrase, lowercase with underscores)."
)


class IntentClassifier:
    """Classifies user intent using LLM with conversation context awareness."""

    def __init__(self, llm_client, state, problem_context: str = ""):
        self.llm = llm_client
        self.state = state
        self._problem_context = problem_context

    async def classify(
        self,
        user_input: str,
        message_history: List[Dict[str, str]] = None,
    ) -> str:
        """Use LLM to classify user intent with conversation context."""
        history_summary = ""
        if message_history:
            recent = message_history[-6:]
            lines = [f"{msg.get('role', 'unknown')}: {str(msg.get('content', ''))[:200]}" for msg in recent]
            history_summary = "\n".join(lines)

        last_agent_ctx = ""
        if self.state.last_agent_type:
            agent_name_map = {
                "code_reviewer": "Code Reviewer",
                "problem_analyzer": "Problem Analyzer",
                "contest_coach": "Contest Coach",
                "learning_partner": "Learning Partner",
                "learning_manager": "Learning Manager",
            }
            last_agent_ctx = agent_name_map.get(self.state.last_agent_type, self.state.last_agent_type)

        problem_hint = ""
        if self._problem_context:
            for line in self._problem_context.split("\n"):
                if line.startswith("Title:"):
                    problem_hint = line.strip()
                    break
            if not problem_hint:
                problem_hint = "(a specific OJ problem is selected)"

        template_text = get_prompt("intent_classifier") or _INLINE_PROMPT
        prompt = Template(template_text).safe_substitute(
            user_input=user_input,
            history_summary=history_summary or "(start of conversation)",
            last_agent_ctx=last_agent_ctx or "none — first message",
            problem_hint=problem_hint if problem_hint else "no problem selected yet",
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return response.strip().lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "problem_help"