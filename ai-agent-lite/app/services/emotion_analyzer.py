"""Emotion analysis service — LLM-based student emotional state detection."""
import json
import logging
from typing import Dict, List, Any

from app.models.schemas import AgentResponse, CompletionStatus

logger = logging.getLogger("ai-agent-lite.emotion_analyzer")


class EmotionAnalyzer:
    """Analyzes student emotional state using LLM instead of keyword matching.

    Returns structured emotion scores used by the supervisor for routing
    and by other agents for adaptive behavior. This agent does NOT produce
    user-facing content — it returns a metadata-only AgentResponse.
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    async def analyze(self, user_input: str, recent_messages: list = None) -> Dict[str, float]:
        """Return emotion scores {frustration, confusion, excitement, confidence}.

        Each score is 0.0–1.0. On failure returns a neutral baseline.
        """
        ctx_lines = []
        if recent_messages:
            for msg in recent_messages[-3:]:
                role = msg.get("role", "user")
                content = str(msg.get("content", ""))[:200]
                ctx_lines.append(f"{role}: {content}")
        context_block = "\n".join(ctx_lines) if ctx_lines else "(no prior context)"

        prompt = (
            "You are analyzing a programming-competition student's emotional state. "
            "Based on their latest message and recent conversation context, "
            "estimate their current emotional levels.\n\n"
            f"Recent context:\n{context_block}\n"
            f"Current message: {user_input}\n\n"
            "Return JSON ONLY — no markdown, no explanation. Format:\n"
            '{"emotions":{"frustration":0.0,"confusion":0.0,"excitement":0.0,"confidence":0.0}}\n'
            "Rules:\n"
            "- Each value is between 0.0 and 1.0\n"
            "- frustration: annoyance, impatience, wanting to give up\n"
            "- confusion: not understanding, feeling lost\n"
            "- excitement: enthusiasm, insight, satisfaction\n"
            "- confidence: self-assurance in their ability\n"
            "- If the message is neutral, all values should be close to 0.3\n"
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
            emotions = data.get("emotions", {})
            result = {}
            for key in ("frustration", "confusion", "excitement", "confidence"):
                val = float(emotions.get(key, 0.3))
                result[key] = max(0.0, min(1.0, val))
            return result
        except Exception as exc:
            logger.warning("EmotionAnalyzer failed: %s", exc)
            return {"frustration": 0.0, "confusion": 0.0, "excitement": 0.0, "confidence": 0.5}

    async def process(self, user_input: str, state: Dict[str, Any], message_history: List[Dict[str, str]] = None) -> AgentResponse:
        """Not used directly — ``analyze`` is the public interface."""
        return AgentResponse(
            content="",
            status=CompletionStatus.COMPLETE,
            metadata={"role": "emotion_analyzer"},
        )