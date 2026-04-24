"""Intent classification service — LLM-based intent recognition with context awareness."""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ai-agent-lite.intent_classifier")


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
        """Use LLM to classify user intent with conversation context.

        When a student is answering a previous agent's question, the intent
        should follow the teaching flow rather than being re-classified
        into something unrelated.
        """
        # Build conversation context summary (last 6 messages)
        history_summary = ""
        if message_history:
            recent = message_history[-6:]
            lines = []
            for msg in recent:
                role = msg.get("role", "unknown")
                content = str(msg.get("content", ""))[:200]
                lines.append(f"{role}: {content}")
            history_summary = "\n".join(lines)

        # Build last agent context
        last_agent_ctx = ""
        if self.state.last_agent_type:
            agent_name_map = {
                "code_reviewer": "Code Reviewer (代码审查专家)",
                "problem_analyzer": "Problem Analyzer (问题解析专家)",
                "contest_coach": "Contest Coach (竞赛教练)",
                "learning_partner": "Learning Partner (学习伙伴)",
                "learning_manager": "Learning Manager (学习管理专家)",
            }
            last_agent_ctx = agent_name_map.get(
                self.state.last_agent_type, self.state.last_agent_type
            )

        # Build problem context hint
        problem_hint = ""
        if self._problem_context:
            for line in self._problem_context.split("\n"):
                if line.startswith("Title:"):
                    problem_hint = line.strip()
                    break
            if not problem_hint:
                problem_hint = "(a specific OJ problem is selected)"

        prompt = (
            "Classify the student's intent from a programming competition training session.\n"
            f"Current problem: {problem_hint if problem_hint else 'no problem selected yet'}\n"
            "NOTE: A problem may be selected, but that does NOT mean the student wants teaching right now. "
            "Classify based on what the student ACTUALLY says, not on what problem is open.\n"
            "If the student is just chatting or greeting, classify as \"casual\" — do NOT force it into a teaching category.\n"
            "IMPORTANT CONTEXT — You must consider the conversation history and what the previous AI agent was doing. "
            "If the student is clearly responding to a previous agent's question or following that agent's guidance, "
            "the intent should stay in the SAME flow, not jump to an unrelated category.\n"
            f"Current student message: \"{user_input}\"\n"
            f"Previous conversation (most recent messages):\n"
            f"{history_summary if history_summary else '(start of conversation)'}\n"
            f"Previous AI agent: {last_agent_ctx if last_agent_ctx else 'none — first message'}\n"
            "Possible intents:\n"
            "- code_review: Request for code analysis, optimization, or style feedback\n"
            "- problem_help: Need help understanding or solving the CURRENT problem\n"
            "- contest_prep: Seeking competition strategies or pressure simulation\n"
            "- emotional_support: Expressing frustration, confusion, or need for motivation\n"
            "- learning_plan: Request for study recommendations, progress tracking, OR continuing a learning-coaching dialogue\n"
            "- answer_to_coach: Student is answering a question or following instructions from the previous agent\n"
            "- casual: Student is greeting, chatting, making small talk. Examples: \"你好\", \"在吗\", \"今天天气怎么样\"\n"
            "- off_topic: Student explicitly asks about a DIFFERENT programming topic unrelated to the current problem\n"
            "RULES:\n"
            "- If the student is clearly answering a question from the previous agent, classify as \"answer_to_coach\"\n"
            "- Short acknowledgments like \"好的\", \"嗯\", \"明白\" that are NOT direct answers should be \"casual\"\n"
            "- If the student is following up on the previous agent's topic, prefer the same intent category\n"
            "- Classify as \"off_topic\" only when switching to a different technical topic\n"
            "Return ONLY the intent name (one word or phrase, lowercase with underscores)."
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return response.strip().lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "problem_help"