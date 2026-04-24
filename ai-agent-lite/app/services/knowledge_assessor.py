"""Knowledge delta assessment service — LLM-based evaluation of student learning gains."""
import json
import logging
from typing import Dict

logger = logging.getLogger("ai-agent-lite.knowledge_assessor")


class KnowledgeAssessor:
    """Uses LLM to assess knowledge gains from a conversation turn."""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def assess(self, user_input: str, agent_response: str, agent_type: str) -> Dict[str, float]:
        """Assess the student's knowledge delta from this turn.

        Returns a dict of {topic: mastery_delta} where mastery_delta is positive
        for gains and negative for losses.
        """
        prompt = (
            "You are an AI tutor analyzing a conversation. Based on the exchange below, "
            "identify what programming/algorithm knowledge topics the student has gained, "
            "reinforced, or might be confused about.\n\n"
            f"Student asked: {user_input[:400]}\n"
            f"AI role: {agent_type}\n"
            f"AI response: {agent_response[:800]}\n\n"
            "Return JSON ONLY — no markdown, no explanation. Format:\n"
            '{"deltas":[{"topic":"topic_name","delta":0.1}]}\n'
            "Rules:\n"
            '- topic should be a concise algorithm/CS concept (e.g. "binary_search", "dp", "graph_bfs")\n'
            "- delta is between -0.1 and 0.3 (positive = gained understanding, negative = confusion)\n"
            "- Only include topics that clearly appear in the exchange\n"
            "- Maximum 5 topics\n"
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