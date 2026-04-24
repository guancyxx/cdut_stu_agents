"""
Specialized Worker Agents for programming competition training.
Each agent focuses on a specific aspect of student development.
All AI responses to users must be in Chinese (简体中文).
Prompts and code remain in English only.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger("ai-agent-lite.workers")

class CompletionStatus(Enum):
    COMPLETE = "complete"
    NEEDS_FOLLOWUP = "needs_followup"
    ERROR = "error"

@dataclass
class AgentResponse:
    content: str
    status: CompletionStatus
    metadata: Dict[str, Any] = None
    next_actions: List[Dict] = None


def _build_history_block(
    message_history: List[Dict[str, str]] = None,
    max_messages: int = 6,
    max_chars: int = 200,
) -> str:
    """Build a concise conversation-history block for agent prompts.

    Returns a human-readable summary of recent turns, or an empty string
    if no history is available.  Keeps the last *max_messages* messages
    and truncates each to *max_chars*.
    """
    if not message_history:
        return ""
    recent = message_history[-max_messages:]
    lines = []
    for msg in recent:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))[:max_chars]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_problem_anchor_block(state: Dict[str, Any]) -> str:
    """Build a problem-anchor instruction block for agent prompts.

    When a problem is selected, this generates a strong instruction
    that keeps the agent anchored to the current problem, preventing
    the conversation from drifting to unrelated topics.

    Returns empty string if no problem context is available.
    """
    problem_context = state.get("current_problem_context", "")
    if not problem_context:
        return ""

    # Extract title and problem ID from the structured context message
    title = ""
    problem_id = ""
    difficulty = ""
    for line in problem_context.split("\n"):
        if line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
        elif line.startswith("Problem ID:"):
            problem_id = line.replace("Problem ID:", "").strip()
        elif line.startswith("Difficulty:"):
            difficulty = line.replace("Difficulty:", "").strip()

    # Extract problem statement section
    statement_start = problem_context.find("Problem statement:")
    problem_statement = ""
    if statement_start >= 0:
        problem_statement = problem_context[statement_start + len("Problem statement:"):].strip()

    anchor = (
        "\n====== CURRENT PROBLEM (TEACHING ANCHOR) ======\n"
        f"Problem ID: {problem_id or 'N/A'}\n"
        f"Title: {title or 'Unknown'}\n"
        f"Difficulty: {difficulty or 'Unknown'}\n"
    )
    if problem_statement:
        # Truncate very long statements to keep prompts manageable
        stmt_preview = problem_statement[:800] + ("..." if len(problem_statement) > 800 else "")
        anchor += f"Problem statement preview: {stmt_preview}\n"

    anchor += (
        "====== END PROBLEM ANCHOR ======\n\n"
        "ABSOLUTE RULE — TOPIC ANCHORING:\n"
        "- You are aware that this problem is selected, but do NOT start teaching or analyzing it\n"
        "  unless the student EXPLICITLY asks for help with it.\n"
        "- If the student is chatting, greeting, or making casual conversation, respond NATURALLY.\n"
        "  Do NOT redirect them to the problem. Let them lead.\n"
        "- ONLY when the student asks about this problem (e.g., \"怎么做\", \"帮我看看\", \"不理解\"),\n"
        "  then enter teaching mode and anchor all your guidance to this problem.\n"
        "- In teaching mode: your response MUST be relevant to the current problem.\n"
        "  Do NOT discuss algorithms, data structures, or topics unrelated to this problem.\n"
        "  When giving examples or exercises, they must relate to THIS problem.\n"
    )
    return anchor


class BaseWorker:
    """Base class for all specialized workers."""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        """Process user input and return structured response."""
        raise NotImplementedError


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

        history_block = _build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (for context — the student may be "
                f"responding to a previous question about this code):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = _build_problem_anchor_block(state)

        prompt = f"""As an expert code reviewer for programming competitions, analyze this {language} code.
{problem_anchor}
Problem ID: {problem_id}

Code:
```{language}
{code}
```

Student's question: {user_input}
{history_section}
MICRO-STEP TEACHING RULES:
- Do NOT dump all analysis in one response. Cover ONE aspect per turn only.
- Start with the most critical issue (logic correctness). Other aspects wait for future turns.
- ALWAYS end with a concrete question or micro-task for the student (e.g., "Can you spot the bug in the loop condition?" or "Try fixing the time complexity and show me").
- NEVER give the complete corrected code unless the student has asked 3+ times on the same point.
- Briefly evaluate → give a hint → ask them to act.

If the student is answering a question from the conversation history,
evaluate their answer directly and concisely, then advance to the next aspect."""

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"analysis_type": "code_review", "language": language}
            )
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return AgentResponse(
                content="Code analysis temporarily unavailable.",
                status=CompletionStatus.ERROR
            )


class ProblemAnalyzerAgent(BaseWorker):
    """Deep analysis of competition problems and solution guidance."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        problem_id = state.get("current_problem_id", "unknown")

        history_block = _build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (for context — the student may be "
                f"continuing a discussion about this problem):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = _build_problem_anchor_block(state)

        prompt = f"""As a programming competition problem expert, help the student through this problem step by step.
{problem_anchor}
Problem Context: {problem_id}
Student's Question: {user_input}
{history_section}
MICRO-STEP TEACHING RULES:
- Do NOT provide a full analysis covering everything at once. You are a coach, not a textbook.
- Each turn, cover only ONE small aspect of the problem (e.g., just understand the input format, or just identify the core algorithm, or just analyze one edge case).
- ALWAYS end your response with a concrete question or micro-task that requires the student to think or try (e.g., "What do you think the time complexity would be if we used brute force?" or "Try writing just the input-parsing part").
- NEVER reveal the full solution approach unless the student has been stuck on the same point 3+ times.
- When the student answers your question, evaluate it first, then advance to the next micro-step.
- Do NOT give numbered lists of all aspects — that is lecturing, not coaching.
- Be brief. One concept → one question. That is one turn.

IMPORTANT: If the conversation history shows the student is answering a
previous question or trying an exercise, respond to THEIR answer first
(evaluate correctness, give feedback), then advance to the NEXT micro-step.
Do NOT restart the explanation from scratch as if this is a new conversation.

Focus on teaching problem-solving thinking, not just giving answers."""

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"problem_id": problem_id, "analysis_depth": "detailed"}
            )
        except Exception as e:
            logger.error(f"Problem analysis failed: {e}")
            return AgentResponse(
                content="Problem analysis temporarily unavailable.",
                status=CompletionStatus.ERROR
            )


class ContestCoachAgent(BaseWorker):
    """Simulates competition pressure and provides strategic advice."""

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        history_block = _build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (for context):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = _build_problem_anchor_block(state)

        prompt = f"""As a programming competition coach, provide strategic advice.
{problem_anchor}
Student's Situation: {user_input}
{history_section}
MICRO-STEP TEACHING RULES:
- Do NOT list all strategies at once. Cover ONE concrete tip or strategy per turn.
- ALWAYS end with a concrete question or small action for the student (e.g., "Which problem would you tackle first in a 2-hour contest and why?").
- When the student follows up, evaluate their thinking, then give the next tip.
- Be competitive but supportive. Brief and direct.

If the student is following up on previous coaching advice, respond to
their specific situation first, then advance to the next strategy point."""

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"coaching_type": "contest_strategy"}
            )
        except Exception as e:
            logger.error(f"Contest coaching failed: {e}")
            return AgentResponse(
                content="Competition coaching temporarily unavailable.",
                status=CompletionStatus.ERROR
            )


class EmotionAnalyzer(BaseWorker):
    """Analyzes student emotional state using LLM instead of keyword matching.

    Returns structured emotion scores used by the supervisor for routing
    and by other agents for adaptive behavior. This agent does NOT produce
    user-facing content — it returns a metadata-only AgentResponse.
    """

    async def analyze(self, user_input: str, recent_messages: list = None) -> Dict[str, float]:
        """Return emotion scores {frustration, confusion, excitement, confidence}.

        Each score is 0.0–1.0. On failure returns a neutral baseline.
        """
        # Build context from recent messages (max 3)
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
            import json as _json
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = _json.loads(cleaned)
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


class LearningPartnerAgent(BaseWorker):
    """Provides warm, targeted emotional support and positive framing.

    Unlike the old keyword-driven approach, this agent receives LLM-analyzed
    emotion scores and crafts a response that directly addresses the student's
    specific emotional state — frustration, confusion, or simply needing
    encouragement. It never lists generic advice; it speaks to the student
    as a real person.
    """

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        emotional_state = state.get("emotion_tags", {})

        # Build a concise emotion summary for the prompt
        emotion_desc = ", ".join(
            f"{k}={v:.1f}" for k, v in emotional_state.items() if v > 0.2
        ) if emotional_state else "neutral"

        history_block = _build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                f"\nConversation history (so you understand what the student has been through):\n"
                f"```\n{history_block}\n```\n"
            )

        problem_anchor = _build_problem_anchor_block(state)

        prompt = (
            "You are a supportive learning companion for a programming-competition "
            "student.\n\n"
            f"Student says: {user_input}\n"
            f"Detected emotional state: {emotion_desc}\n"
            f"{problem_anchor}"
            f"{history_section}"
            "Rules:\n"
            "- CRITICAL: Do NOT start teaching or coaching unless the student explicitly asks for help. "
            "If the student is just greeting, chatting, or making small talk, respond as a friendly "
            "conversation partner — be natural, warm, and brief. No teaching, no problem analysis, "
            "no suggestions about algorithms or exercises.\n"
            "- If the student DOES explicitly ask for help with a problem or concept, briefly encourage "
            "them and then suggest they ask the specific question — but let them lead.\n"
            "- If frustrated: acknowledge the difficulty honestly, don't say it's "
            "easy. Share that this specific struggle is a normal stage.\n"
            "- If confused: reassure that confusion means learning is happening. "
            "Offer one tiny concrete thing to try.\n"
            "- If excited: match their energy briefly, then let them continue.\n"
            "- If neutral: be a calm, steady presence. No forced enthusiasm.\n"
            "- Keep it short — 2-3 sentences max.\n"
            "- Do NOT give a list of generic advice. Talk like a real person.\n"
            "- If the conversation history shows the student was in the middle of "
            "a learning exercise, briefly acknowledge their emotional state then "
            "help them get back on track with that exercise.\n"
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"support_type": "emotional", "emotional_state": emotional_state}
            )
        except Exception as e:
            logger.error(f"Learning partner response failed: {e}")
            return AgentResponse(
                content="我在这儿，随时可以继续。",
                status=CompletionStatus.COMPLETE
            )


class NextStepSuggester(BaseWorker):
    """Generates contextual next-step suggestions at the end of a conversation turn.

    This agent runs ONLY after the primary worker has finished producing content.
    It does not generate message content — it returns structured suggestion items
    that the WebSocket handler sends as a separate `next_suggestions` event.
    Suggestion titles and reasons are in Chinese for user-facing display.

    The prompt is driven by state_delta (knowledge_graph_position diff) rather than
    a generic summary of the agent response, producing targeted next actions.
    """

    SUGGESTION_TYPES = ("practice", "learn", "review", "debug", "compete")

    async def suggest(
        self,
        user_input: str,
        agent_response: str,
        agent_type: str,
        state: Dict[str, Any],
        state_delta: Dict[str, Any] = None,
    ) -> List[Dict[str, str]]:
        """Return 2-3 structured next-step suggestions based on state delta.

        If state_delta is provided and contains meaningful changes, the prompt
        focuses on those specific knowledge gains/gaps.  If no delta or empty
        delta, falls back to a context-only prompt.

        Returns a list of dicts with keys: type, title, target, reason.
        On failure returns an empty list (never raises).
        """
        # Build delta-human-readable section
        delta_section = ""
        if state_delta:
            gained = state_delta.get("gained", {})
            improved = state_delta.get("improved", {})
            weakened = state_delta.get("weakened", {})
            stable_topics = state_delta.get("stable", {})
            before_summary = state_delta.get("before_summary", {})
            after_summary = state_delta.get("after_summary", {})

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
                # No meaningful change — suggest something new
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
            # Fallback: no delta available
            prompt = (
                "You are an AI programming-competition coach. Based on the conversation "
                "below, suggest 2-3 concrete next actions the student could take.\n\n"
                f"Student's last message: {user_input}\n"
                f"AI agent role: {agent_type}\n"
                f"AI response summary: {agent_response[:600]}\n"
                f"Current context: problem_id={state.get('current_problem_id', 'N/A')}\n\n"
                'Return JSON ONLY — no markdown, no explanation. Format:\n'
                '{"suggestions":[{"type":"practice|learn|review|debug|compete",'
                '"title":"short action title in Chinese (简体中文)",'
                '"target":"specific target or problem id",'
                '"reason":"why this helps, in Chinese (简体中文)"}]}\n'
                "Keep titles under 20 characters. Keep reasons under 40 characters. "
                "Title and reason MUST be in Chinese (简体中文)."
            )

        try:
            raw = await self.llm.complete([{"role": "user", "content": prompt}])
            import json as _json

            # Strip markdown fences if the model wraps them
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = _json.loads(cleaned)
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


class LearningManagerAgent(BaseWorker):
    """Micro-stepping learning coach that guides students through atomic tasks.

    This agent does NOT produce full lesson plans or information dumps.
    Instead, it follows a strict THOUGHT → GUIDANCE → INTERACTION protocol,
    delivering one atomic concept per turn and always ending with a question
    or micro-exercise that requires the student's active response.
    """

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentResponse:
        knowledge_graph = state.get("knowledge_graph_position", {})
        efficiency = state.get("efficiency_trend", 1.0)
        emotion_tags = state.get("emotion_tags", {})
        problem_id = state.get("current_problem_id", "unknown")

        emotion_context = ""
        if emotion_tags:
            emotion_items = ", ".join(f"{k}={v:.1f}" for k, v in emotion_tags.items() if v > 0.2)
            if emotion_items:
                emotion_context = f"\nStudent emotional signals: {emotion_items}"

        # Detect frustration from efficiency trend or emotional state
        frustration_level = ""
        if efficiency < 0.7:
            frustration_level = (
                "\n[IMPORTANT] The student's efficiency trend is declining. "
                "Simplify immediately — drop to a foundational concept, "
                "use a very small concrete example, and avoid any abstraction."
            )
        elif emotion_tags.get("frustration", 0) > 0.5 or emotion_tags.get("confusion", 0) > 0.6:
            frustration_level = (
                "\n[IMPORTANT] The student shows frustration or confusion. "
                "Slow down. Reassure briefly that the current difficulty is normal. "
                "Then offer a simpler, more concrete anchoring question."
            )

        # Build conversation history section
        history_block = _build_history_block(message_history)
        history_section = ""
        if history_block:
            history_section = (
                "\nConversation history (the teaching dialogue so far):\n"
                f"```\n{history_block}\n```\n"
            )

        # Build problem anchor — this is the strongest constraint
        problem_anchor = _build_problem_anchor_block(state)

        prompt = (
            "You are a pragmatic, precise programming-competition learning coach. "
            "Your role is to guide students through micro-steps, NOT to lecture.\n\n"
            "ABSOLUTE RULES:\n"
            "- NEVER dump large amounts of information in one turn. Cover only 1 concept "
            "or 1 exercise per turn, keeping your response concise and focused.\n"
            "- NEVER list more than 1 new concept or 1 exercise per turn.\n"
            "- NEVER give complete source code unless the student has asked 3+ times "
            "on the same logical point.\n"
            "- NEVER use empty praise like \"太棒了\" or \"令人惊叹\". Evaluate logic and "
            "code efficiency, not effort.\n"
            "- ALWAYS end your response with a concrete question or micro-task "
            "that requires the student to act. No exceptions.\n"
            "- Be warm and patient. Acknowledge struggle honestly — don't pretend "
            "difficult things are easy.\n"
            "- When a student is wrong, point out the specific gap and provide a "
            "minimal hint, not the full correction.\n\n"
            f"{problem_anchor}"
            f"Student's current knowledge profile: {knowledge_graph or 'new student'}\n"
            f"Current problem: {problem_id}\n"
            f"Efficiency trend: {efficiency:.2f}{emotion_context}{frustration_level}\n"
            f"{history_section}"
            f"Student says: {user_input}\n\n"
            "CRITICAL: If the conversation history shows you previously asked the student "
            "a question or gave them an exercise, the student's current message is likely "
            "their ANSWER to that question. In that case:\n"
            "- Evaluate their answer first (correct/partially correct/wrong)\n"
            "- Give targeted feedback on their specific answer\n"
            "- Then give the NEXT micro-step or question\n"
            "- Do NOT repeat the previous question or restart the explanation\n"
        )

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"plan_type": "micro_step_coaching", "efficiency_factor": efficiency}
            )
        except Exception as e:
            logger.error(f"Learning management failed: {e}")
            return AgentResponse(
                content="暂时无法响应，请稍后再试。",
                status=CompletionStatus.ERROR
            )