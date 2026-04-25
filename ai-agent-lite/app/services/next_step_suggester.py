"""Next-step suggestion service — generates contextual follow-up actions for students.

Each suggestion represents what the student would naturally say or ask next,
guiding their learning direction.  The student clicks a suggestion to send it
as their next message.
"""
import json
import logging
from string import Template
from typing import Dict, Any, List

from app.models.schemas import AgentResponse, CompletionStatus
from app.prompts import get_prompt

logger = logging.getLogger("ai-agent-lite.next_step_suggester")

# Fallback prompts — used only when .md template files are missing
_INLINE_DELTA_PROMPT = (
    "You are a study buddy suggesting what the STUDENT should say next. "
    "Based on the conversation, propose 2-3 short utterances the student "
    "would naturally say to continue learning.\n\n"
    "Student just said: $user_input\nAgent role: $agent_type\n"
    "Current problem: $current_problem_id\nStudent mood: $emotion_hint\n"
    "Knowledge change this turn:\n$delta_section\n\n"
    "CRITICAL: Each suggestion is what the STUDENT would type next — "
    "phrased in first person, like a natural follow-up question or request.\n"
    "Examples: 'Can you walk me through the BFS approach?', "
    "'I think my loop condition is wrong, can you check?', "
    "'That makes sense, got any practice problems for this?'\n\n"
    'Return JSON (no markdown): {"suggestions":[{"type":"practice|learn|review|debug|compete|encourage",'
    '"title":"what the student would say (max 50 chars)",'
    '"target":"specific topic or problem",'
    '"reason":"why this is useful now (max 100 chars)"}]}\n\n'
    "type meanings:\n"
    "- practice: hands-on coding exercise\n"
    "- learn: study a new concept or method\n"
    "- review: revisit something just learned\n"
    "- debug: investigate a bug or wrong answer\n"
    "- compete: contest or competition related\n"
    "- encourage: motivational nudge (prioritize when student is struggling)"
)

_INLINE_FALLBACK_PROMPT = (
    "You are a study buddy suggesting what the STUDENT should say next. "
    "Based on the conversation, propose 2-3 short utterances the student "
    "would naturally say to continue learning.\n\n"
    "Student just said: $user_input\nAgent role: $agent_type\n"
    "AI response summary: $agent_response\n"
    "Current problem: $current_problem_id\nStudent mood: $emotion_hint\n\n"
    "CRITICAL: Each suggestion is what the STUDENT would type next — "
    "phrased in first person, like a natural follow-up question or request.\n"
    "Examples: 'Can you walk me through the BFS approach?', "
    "'I think my loop condition is wrong, can you check?', "
    "'That makes sense, got any practice problems for this?'\n\n"
    'Return JSON (no markdown): {"suggestions":[{"type":"practice|learn|review|debug|compete|encourage",'
    '"title":"what the student would say (max 50 chars)",'
    '"target":"specific topic or problem",'
    '"reason":"why this is useful now (max 100 chars)"}]}\n\n'
    "type meanings:\n"
    "- practice: hands-on coding exercise\n"
    "- learn: study a new concept or method\n"
    "- review: revisit something just learned\n"
    "- debug: investigate a bug or wrong answer\n"
    "- compete: contest or competition related\n"
    "- encourage: motivational nudge"
)


class NextStepSuggester:
    """Generates contextual next-step suggestions at the end of a conversation turn."""

    SUGGESTION_TYPES = ("practice", "learn", "review", "debug", "compete", "encourage")

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
        """Return 2-3 structured next-step suggestions based on state delta.

        Each suggestion's 'title' is phrased as what the student would say next.
        """
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
                delta_lines.append(f"Newly mastered: {items}")
            if improved:
                items = ", ".join(f"{k}: {v['before']}->{v['after']}" for k, v in improved.items())
                delta_lines.append(f"Improved: {items}")
            if weakened:
                items = ", ".join(f"{k}: {v['before']}->{v['after']}" for k, v in weakened.items())
                delta_lines.append(f"Weakened: {items}")
            if delta_lines:
                delta_section = "\n".join(delta_lines)
            elif stable_topics:
                stable_list = ", ".join(f"{k}({v})" for k, v in stable_topics.items())
                delta_section = f"Stable (no significant change): {stable_list}"

        # Build emotion hint from state
        emotion_tags = state.get("emotion_tags", {})
        if emotion_tags:
            high = [(k, v) for k, v in emotion_tags.items() if v > 0.3]
            if high:
                emotion_hint = ", ".join(f"{k}({v:.1f})" for k, v in high)
            else:
                emotion_hint = "calm"
        else:
            emotion_hint = "neutral"

        # Load prompt templates from .md files, fallback to inline
        if delta_section:
            template_text = get_prompt("next_step_suggester_delta") or _INLINE_DELTA_PROMPT
            prompt = Template(template_text).safe_substitute(
                user_input=user_input,
                agent_type=agent_type,
                current_problem_id=state.get("current_problem_id", "N/A"),
                emotion_hint=emotion_hint,
                delta_section=delta_section,
            )
        else:
            template_text = get_prompt("next_step_suggester_fallback") or _INLINE_FALLBACK_PROMPT
            prompt = Template(template_text).safe_substitute(
                user_input=user_input,
                agent_type=agent_type,
                agent_response=agent_response[:600],
                current_problem_id=state.get("current_problem_id", "N/A"),
                emotion_hint=emotion_hint,
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
                    "title": str(item.get("title", ""))[:50],
                    "target": str(item.get("target", ""))[:80],
                    "reason": str(item.get("reason", ""))[:100],
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