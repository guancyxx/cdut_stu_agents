"""Next-step suggestion service — generates contextual follow-up actions for students."""
import json
import logging
from typing import Dict, Any, List

from app.models.schemas import AgentResponse, CompletionStatus

logger = logging.getLogger("ai-agent-lite.next_step_suggester")


class NextStepSuggester:
    """Generates contextual next-step suggestions at the end of a conversation turn.

    This agent runs ONLY after the primary worker has finished producing content.
    It does not generate message content — it returns structured suggestion items
    that the WebSocket handler sends as a separate ``next_suggestions`` event.
    Suggestion titles and reasons are in Chinese for user-facing display.

    The prompt is driven by state_delta (knowledge_graph_position diff) rather than
    a generic summary of the agent response, producing targeted next actions.
    """

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
        # Build delta-human-readable section
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
                items = ", ".join(
                    f"{k}: {v['before']}→{v['after']}" for k, v in improved.items()
                )
                delta_lines.append(f"进步: {items}")
            if weakened:
                items = ", ".join(
                    f"{k}: {v['before']}→{v['after']}" for k, v in weakened.items()
                )
                delta_lines.append(f"退步: {items}")
            if delta_lines:
                delta_section = "\n".join(delta_lines)
            elif stable_topics:
                stable_list = ", ".join(f"{k}({v})" for k, v in stable_topics.items())
                delta_section = f"已掌握(无明显变化): {stable_list}"

        if delta_section:
            prompt = (
                "You are an AI programming-competition coach. Based on the student's "
                "knowledge state change this turn, suggest 2-3 concrete next actions "
                "that directly build on their new capabilities or address weaknesses.\n\n"
                f"Student asked: {user_input}\n"
                f"Agent type: {agent_type}\n"
                f"Current problem: {state.get('current_problem_id', 'N/A')}\n"
                f"Knowledge change this turn:\n{delta_section}\n\n"
                "Rules:\n"
                "- Target the SPECIFIC topics that just improved or appeared (gained/improved).\n"
                "- If topics weakened, suggest review/debug on those exact topics.\n"
                "- If no meaningful change, suggest a NEW related topic to explore.\n"
                "- DO NOT suggest vague general actions.\n"
                '- Return JSON ONLY — no markdown, no explanation. Format:\n'
                '{"suggestions":[{"type":"practice|learn|review|debug|compete",'
                '"title":"short action title in Chinese (简体中文)",'
                '"target":"specific target or problem id",'
                '"reason":"why this helps — refer to the specific knowledge change, in Chinese (简体中文)"}]}\n'
                "Keep titles under 20 characters. Keep reasons under 40 characters. "
                "Title and reason MUST be in Chinese (简体中文)."
            )
        else:
            prompt = (
                "You are an AI programming-competition coach. Based on the conversation "
                "below, suggest 2-3 concrete next actions the student could take.\n\n"
                f"Student's last message: {user_input}\n"
                f"AI agent role: {agent_type}\n"
                f"AI response summary: {agent_response[:600]}\n"
                f"Current context: problem_id={state.get('current_problem_id', 'N/A')}\n\n"
                '- Return JSON ONLY — no markdown, no explanation. Format:\n'
                '{"suggestions":[{"type":"practice|learn|review|debug|compete",'
                '"title":"short action title in Chinese (简体中文)",'
                '"target":"specific target or problem id",'
                '"reason":"why this helps, in Chinese (简体中文)"}]}\n'
                "Keep titles under 20 characters. Keep reasons under 40 characters. "
                "Title and reason MUST be in Chinese (简体中文)."
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