"""Knowledge delta assessment service — LLM-based evaluation of student learning gains."""
import json
import logging
from typing import Dict

from app.prompts import get_prompt

logger = logging.getLogger("ai-agent-lite.knowledge_assessor")

_INLINE_PROMPT = (
    "You are an AI tutor analyzing a conversation. Based on the exchange below, "
    "identify what programming/algorithm knowledge topics the student has gained, "
    "reinforced, or might be confused about.\n\n"
    "Student asked: {user_input}\nAI role: {agent_type}\nAI response: {agent_response}\n\n"
    'Return JSON ONLY — no markdown, no explanation. Format:\n'
    '{"deltas":[{"topic":"topic_name","delta":0.1}]}\n'
    "Rules:\n- topic: concise algorithm/CS concept\n- delta: -0.1 to 0.3\n- Max 5 topics"
)


class KnowledgeAssessor:
    """Uses LLM to assess knowledge gains from a conversation turn."""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def assess(self, user_input: str, agent_response: str, agent_type: str) -> Dict[str, float]:
        """Assess the student's knowledge delta from this turn."""
        template = get_prompt("knowledge_assessor") or _INLINE_PROMPT
        prompt = template.format(
            user_input=user_input[:400],
            agent_type=agent_type,
            agent_response=agent_response[:800],
        )

        try:
            raw = await self.llm.complete([{"role": "user", "content": prompt}])
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            deltas = data.get("deltas", [])
            result = {}
            for item in deltas:
                topic = item.get("topic", "").strip()
                delta_val = float(item.get("delta", 0))
                if topic and -0.1 <= delta_val <= 0.3:
                    result[topic] = delta_val
            return result
        except Exception as exc:
            logger.warning("knowledge delta assessment failed: %s", exc)
            return {}