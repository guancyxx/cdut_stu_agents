"""
Supervisor Agent - Context-aware router for multi-agent orchestration.
Routes to specialized workers based on intent, conversation context,
and continuity of the current teaching flow.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("ai-agent-lite.supervisor")

class AgentType(Enum):
    CODE_REVIEWER = "code_reviewer"
    PROBLEM_ANALYZER = "problem_analyzer"
    CONTEST_COACH = "contest_coach"
    LEARNING_PARTNER = "learning_partner"
    LEARNING_MANAGER = "learning_manager"
    NEXT_STEP_SUGGESTER = "next_step_suggester"

@dataclass
class StudentState:
    # Core learning state
    current_problem_id: Optional[str] = None
    submitted_code: Optional[str] = None
    knowledge_graph_position: Dict[str, float] = None  # {topic: mastery_level}

    # Emotional state
    emotion_tags: Dict[str, float] = None  # {"frustration": 0.7, "confusion": 0.3}
    efficiency_trend: float = 1.0  # Relative to baseline

    # Temporal context
    session_start_time: datetime = None
    last_activity_time: datetime = None

    # Conversation continuity — tracks which agent handled the last turn
    last_agent_type: Optional[str] = None

    def __post_init__(self):
        if self.knowledge_graph_position is None:
            self.knowledge_graph_position = {}
        if self.emotion_tags is None:
            self.emotion_tags = {}

class Supervisor:
    def __init__(self, llm_client, emotion_analyzer=None):
        self.llm = llm_client
        self.state = StudentState()
        self._emotion_analyzer = emotion_analyzer
        self._problem_context = ""  # Cached problem context for anchored routing

    async def route_request(
        self,
        user_input: str,
        session_context: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
    ) -> AgentType:
        """Determine which agent should handle this request.

        Args:
            user_input: The student's current message.
            session_context: State dict with problem_id, submitted_code, etc.
            message_history: Recent conversation messages for context-aware routing.
        """
        # Store user input for downstream suggestion context
        self._last_user_input = user_input
        self._message_history = message_history or []

        # Update state from context (async — includes LLM emotion analysis)
        await self._update_state_from_context(session_context)

        # Intent classification with LLM (now context-aware)
        intent = await self._classify_intent(user_input, self._message_history)

        # Store for trace output
        self._last_intent = intent

        # State-aware routing logic (now continuity-aware)
        agent_type = self._determine_agent(intent, user_input, self._message_history)

        # Track which agent handled this turn
        self.state.last_agent_type = agent_type.value

        logger.info(
            "Supervisor routing: intent=%s, last_agent=%s, agent=%s",
            intent, self.state.last_agent_type, agent_type,
        )
        return agent_type

    async def _classify_intent(
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
            # Extract just the title line for the prompt to keep it concise
            for line in self._problem_context.split("\n"):
                if line.startswith("Title:"):
                    problem_hint = line.strip()
                    break
            if not problem_hint:
                problem_hint = "(a specific OJ problem is selected)"

        prompt = f"""Classify the student's intent from a programming competition training session.

Current problem: {problem_hint if problem_hint else "no problem selected yet"}

NOTE: A problem may be selected, but that does NOT mean the student wants teaching right now.
Classify based on what the student ACTUALLY says, not on what problem is open.
If the student is just chatting or greeting, classify as "casual" — do NOT force it into a teaching category.

IMPORTANT CONTEXT — You must consider the conversation history and what the previous AI agent was doing. If the student is clearly responding to a previous agent's question or following that agent's guidance, the intent should stay in the SAME flow, not jump to an unrelated category.

Current student message: "{user_input}"

Previous conversation (most recent messages):
{history_summary if history_summary else "(start of conversation)"}

Previous AI agent: {last_agent_ctx if last_agent_ctx else "none — first message"}

Possible intents:
- code_review: Request for code analysis, optimization, or style feedback (for the CURRENT problem's code)
- problem_help: Need help understanding or solving the CURRENT problem
- contest_prep: Seeking competition strategies or pressure simulation
- emotional_support: Expressing frustration, confusion, or need for motivation
- learning_plan: Request for study recommendations, progress tracking, OR continuing a learning-coaching dialogue about the CURRENT problem
- answer_to_coach: Student is answering a question or following instructions from the previous agent (this keeps the conversation in the same teaching flow)
- casual: Student is greeting, chatting, making small talk, or asking a non-programming question with NO teaching need. Examples: "你好", "在吗", "今天天气怎么样", "你是谁", random conversation that does NOT ask for help with the current problem or any programming topic.
- off_topic: Student explicitly asks about a DIFFERENT programming topic unrelated to the current problem (but still technical, e.g., asking about a different algorithm or language). NOT the same as casual — off_topic is still technical, just not about this problem.

RULES:
- If the student is clearly answering a question from the previous agent, classify as "answer_to_coach"
- If the student is following up on the previous agent's topic, prefer the same intent category as the previous turn
- IMPORTANT: Having a problem selected does NOT mean every message should be classified as a teaching need. If the student is just chatting, greeting, or making casual conversation, classify as "casual" — do NOT force it into problem_help or learning_plan.
- Only classify as "problem_help" or "learning_plan" when the student EXPLICITLY asks for help with the problem or is following a teaching flow.
- Classify as "off_topic" only when the student switches to a different technical/programming topic unrelated to the current problem.
- For general questions about algorithms/data structures, if they relate to the current problem, classify as "problem_help"; otherwise classify as "off_topic"

Return ONLY the intent name (one word or phrase, lowercase with underscores)."""

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return response.strip().lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "problem_help"

    def _determine_agent(
        self,
        intent: str,
        user_input: str,
        message_history: List[Dict[str, str]] = None,
    ) -> AgentType:
        """Context-aware agent selection with teaching flow continuity.

        Core principles:
        1. If a problem is selected, ALL teaching stays anchored to it.
        2. If the student is continuing a dialogue with a specific agent,
           route back to the SAME agent for coherence.
        3. Only switch agents when the student explicitly changes topic.
        """
        # Emotional state override - always prioritize emotional support
        if self._needs_emotional_support():
            return AgentType.LEARNING_PARTNER

        # Performance-based routing (efficiency drop) - overrides continuity
        if self._needs_difficulty_adjustment():
            return AgentType.LEARNING_MANAGER

        # --- Casual intent: student is chatting, NOT asking for teaching ---
        # When the student is just greeting or making small talk, route to
        # learning_partner for a friendly chat response. Do NOT force them
        # into a teaching flow — wait until they explicitly ask for help.
        if intent == "casual":
            return AgentType.LEARNING_PARTNER

        # --- Topic anchoring: when a problem is selected, pull off-topic back ---
        # If we have a problem context and the intent is "off_topic" (still
        # technical but about a different problem), redirect to the
        # problem-focused agent instead of letting the conversation drift.
        # NOTE: "casual" intent is handled ABOVE and does NOT hit this block.
        if self._problem_context and intent in ("off_topic", "general_question"):
            # If the student was already being coached by a specific agent on
            # this problem, keep them with that agent
            if self.state.last_agent_type and self.state.last_agent_type in (
                "problem_analyzer", "learning_manager", "code_reviewer"
            ):
                try:
                    return AgentType(self.state.last_agent_type)
                except ValueError:
                    pass
            # Default: route to problem analyzer for anchored teaching
            return AgentType.PROBLEM_ANALYZER

        # --- Continuity-first routing ---
        # If the student is answering/following up the previous agent,
        # route back to the same agent instead of switching.
        if intent == "answer_to_coach" and self.state.last_agent_type:
            try:
                return AgentType(self.state.last_agent_type)
            except ValueError:
                pass

        # When intent matches the previous agent's domain, keep continuity
        if self.state.last_agent_type and self._is_continuation_of_same_flow(intent):
            try:
                return AgentType(self.state.last_agent_type)
            except ValueError:
                pass

        # Intent-based routing (standard mapping)
        intent_mapping = {
            "code_review": AgentType.CODE_REVIEWER,
            "problem_help": AgentType.PROBLEM_ANALYZER,
            "contest_prep": AgentType.CONTEST_COACH,
            "emotional_support": AgentType.LEARNING_PARTNER,
            "learning_plan": AgentType.LEARNING_MANAGER,
            "casual": AgentType.LEARNING_PARTNER,
            "general_question": AgentType.PROBLEM_ANALYZER,
            "off_topic": AgentType.PROBLEM_ANALYZER,
        }

        return intent_mapping.get(intent, AgentType.PROBLEM_ANALYZER)

    def _is_continuation_of_same_flow(self, intent: str) -> bool:
        """Check if the current intent logically belongs to the previous agent's domain.

        This prevents unnecessary agent-switching when a student is still
        working within the same teaching context.
        """
        # Map intents to the agent that typically handles them
        intent_agent_map = {
            "code_review": "code_reviewer",
            "problem_help": "problem_analyzer",
            "contest_prep": "contest_coach",
            "emotional_support": "learning_partner",
            "learning_plan": "learning_manager",
            "casual": "learning_partner",
        }

        expected_agent = intent_agent_map.get(intent)
        if not expected_agent:
            return False

        return self.state.last_agent_type == expected_agent

    def _needs_emotional_support(self) -> bool:
        """Check if student needs emotional support based on state."""
        frustration = self.state.emotion_tags.get("frustration", 0)
        confusion = self.state.emotion_tags.get("confusion", 0)
        return frustration > 0.6 or confusion > 0.7

    def _needs_difficulty_adjustment(self) -> bool:
        """Check if learning difficulty needs adjustment."""
        return self.state.efficiency_trend < 0.7  # 30% efficiency drop

    async def _update_state_from_context(self, context: Dict[str, Any]):
        """Update state from session context. Uses LLM-based emotion analysis."""
        if "problem_id" in context:
            self.state.current_problem_id = context["problem_id"]
        if "submitted_code" in context:
            self.state.submitted_code = context["submitted_code"]
        # Restore last_agent_type from context if available
        if "last_agent_type" in context and context["last_agent_type"]:
            self.state.last_agent_type = context["last_agent_type"]
        # Cache problem context so supervisor can use it for topic-anchored routing
        if "problem_context" in context and context["problem_context"]:
            self._problem_context = context["problem_context"]
        # Use LLM-based emotion analysis instead of keyword matching
        await self._analyze_emotional_state_async(
            context.get("user_input", ""),
            context.get("message_history", [])
        )

    async def _analyze_emotional_state_async(self, user_input: str, message_history: list):
        """Analyze emotional state using the EmotionAnalyzer LLM agent."""
        if self._emotion_analyzer is None:
            return
        try:
            scores = await self._emotion_analyzer.analyze(user_input, message_history)
            for key, val in scores.items():
                self.state.emotion_tags[key] = val
        except Exception as exc:
            logger.warning("Emotion analysis failed, keeping previous state: %s", exc)

    async def assess_knowledge_delta(self, user_input: str, agent_response: str, agent_type: str) -> Dict[str, float]:
        """Use LLM to assess the student's knowledge gains from this conversation turn.

        Returns a dict of {topic: mastery_delta} where mastery_delta is positive
        for gains and negative for losses. These deltas are applied to the
        knowledge_graph_position in the student state.
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
            "- topic should be a concise algorithm/CS concept (e.g. \"binary_search\", \"dp\", \"graph_bfs\")\n"
            "- delta is between -0.1 and 0.3 (positive = gained understanding, negative = confusion)\n"
            "- Only include topics that clearly appear in the exchange\n"
            "- Maximum 5 topics\n"
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

    async def get_next_actions(self, agent_response: str, agent_type: AgentType, suggester=None, state_delta: dict = None) -> list:
        """Generate next action suggestions via NextStepSuggester.

        If a suggester instance is provided, delegates to its ``suggest`` method.
        Falls back to an empty list if the suggester is unavailable or fails.
        ``state_delta`` is the knowledge delta computed by StateManager.compute_knowledge_delta().
        """
        if suggester is None:
            return []

        return await suggester.suggest(
            user_input=getattr(self, "_last_user_input", ""),
            agent_response=agent_response,
            agent_type=agent_type.value,
            state={
                "current_problem_id": self.state.current_problem_id,
                "emotion_tags": dict(self.state.emotion_tags),
                "efficiency_trend": self.state.efficiency_trend,
            },
            state_delta=state_delta,
        )