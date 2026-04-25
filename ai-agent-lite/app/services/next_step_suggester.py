"""Next-step suggestion service — generates contextual follow-up actions for students."""
import json
import logging
from typing import Dict, Any, List

from app.models.schemas import AgentResponse, CompletionStatus
from app.prompts import get_prompt_section

logger = logging.getLogger("ai-agent-lite.next_step_suggester")

_INLINE_DELTA_PROMPT = (
    "You are an AI programming-competition coach. Based on the student's "
    "knowledge state change this turn, suggest 2-3 concrete next actions "
    "that directly build on their new capabilities or address weaknesses.\n\n"
    "Student asked: {user_input}\nAgent type: {agent_type}\n"
    "Current problem: {current_problem_id}\n"
    "Knowledge change this turn:\n{delta_section}\n\n"
    '- Return JSON ONLY. Format: {"suggestions":[{"type":"practice|learn|review|debug|compete",'
    '"title":"short title in Chinese","target":"specific target","reason":"why in Chinese"}]}\n'
    "Keep titles under 20 chars, reasons under 40 chars. MUST be in Chinese (简体中文)."
)

_INLINE_FALLBACK_PROMPT = (
    "You are an AI programming-competition coach. Based on the conversation "
    "below, suggest 2-3 concrete next actions the student could take.\n\n"
    "Student's last message: {user_input}\nAI agent role: {agent_type}\n"
    "AI response summary: {agent_response}\n"
    "Current context: problem_id={current_problem_id}\n\n"
    '- Return JSON ONLY. Format: {"suggestions":[{"type":"practice|learn|review|debug|compete",'
    '"title":"short title in Chinese","target":"target","reason":"reason in Chinese"}]}\n'
    "Keep titles under 20 chars, reasons under 40 chars. MUST be in Chinese (简体中文)."
)


class NextStepSuggester:
    """Generates contextual next-step suggestions at the end of a conversation turn."""

    SUGGESTION_TYPES = ("practice", "learn", "review", "debug", "compete")

    def __init__(self, llm_client):
        self.llm = llm_client

    async def suggest(
        self,
        user_input: str,
        agent_response: str,
        agent_type: str,
        state: Dict[str, Any],
        state_delta: Dict[str, Any] = None,
    ) -> List[Dict[str, str]]:
        """Return 2-3 structured next-step suggestions based on state delta."""
        # Build delta section
        delta_section = ""
        if state_delta:
            gained = state_delta.get("gained", {})
            improved = state_delta.get("improved", {})
            weakened = state_delta.get("weakened", {})
            stable_topics = state_delta.get("stable", {})

            delta_lines = []
            if gained:
                items = ", ".join(f"{k}({v})" for k, v in gained.items())
                delta_lines.append(f"新掌握: {items}")
            if improved:
                items = ", ".join(f"{k}: {v['before']}→{v['after']}" for k, v in improved.items())
                delta_lines.append(f"进步: {items}")
            if weakened:
                items = ", ".join(f"{k}: {v['before']}→{v['after']}" for k, v in weakened.items())
                delta_lines.append(f"退步: {items}")
            if delta_lines:
                delta_section = "\n".join(delta_lines)
            elif stable_topics:
                stable_list = ", ".join(f"{k}({v})" for k, v in stable_topics.items())
                delta_section = f"已掌握(无明显变化): {stable_list}"

        # Load prompt templates from YAML, fallback to inline
        section = get_prompt_section("next_step_suggester")
        if delta_section:
            template = section.get("delta_template") or _INLINE_DELTA_PROMPT
            prompt = template.format(
                user_input=user_input,
                agent_type=agent_type,
                current_problem_id=state.get("current_problem_id", "N/A"),
                delta_section=delta_section,
            )
        else:
            template = section.get("fallback_template") or _INLINE_FALLBACK_PROMPT
            prompt = template.format(
                user_input=user_input,
                agent_type=agent_type,
                agent_response=agent_response[:600],
                current_problem_id=state.get("current_problem_id", "N/A"),
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
            items = data.get("suggestions", [])
            validated = []
            for item in items[:3]:
                if not isinstance(item, dict):
                    continue
                validated.append({
                    "type": item.get("type", "learn") if item.get("type") in self.SUGGESTION_TYPES else "learn",
                    "title": str(item.get("title", ""))[:40],
                    "target": str(item.get("target", ""))[:60],
                    "reason": str(item.get("reason", ""))[:80],
                })
            return validated[:3]
        except Exception as exc:
            logger.warning("NextStepSuggester failed: %s", exc)
            return []

    async def process(self, user_input: str, state: Dict[str, Any], message_history: List[Dict[str, str]] = None) -> AgentResponse:
        """Not used directly — ``suggest`` is the public interface."""
        return AgentResponse(
            content="",
            status=CompletionStatus.COMPLETE,
            metadata={"role": "next_step_suggester"},
        )