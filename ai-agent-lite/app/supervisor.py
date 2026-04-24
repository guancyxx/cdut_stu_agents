"""
Supervisor Agent - Central router for multi-agent orchestration
Based on student state and intent to dispatch to specialized workers.
"""
from enum import Enum
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
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

    async def route_request(self, user_input: str, session_context: Dict[str, Any]) -> AgentType:
        """Determine which agent should handle this request based on intent and state."""

        # Store user input for downstream suggestion context
        self._last_user_input = user_input

        # Update state from context (now async — includes LLM emotion analysis)
        await self._update_state_from_context(session_context)

        # Intent classification with LLM
        intent = await self._classify_intent(user_input)

        # Store for trace output
        self._last_intent = intent

        # State-aware routing logic
        agent_type = self._determine_agent(intent, user_input)

        logger.info(f"Supervisor routing: intent={intent}, agent={agent_type}")
        return agent_type

    async def _classify_intent(self, user_input: str) -> str:
        """Use LLM to classify user intent."""
        prompt = f"""
        Classify the student's intent from programming competition training:

        Input: "{user_input}"

        Possible intents:
        - code_review: Request for code analysis, optimization, or style feedback
        - problem_help: Need help understanding or solving a problem
        - contest_prep: Seeking competition strategies or pressure simulation
        - emotional_support: Expressing frustration, confusion, or need for motivation
        - learning_plan: Request for study recommendations or progress tracking
        - general_question: Other algorithm/data structure questions

        Return ONLY the intent name.
        """

        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return response.strip().lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "general_question"

    def _determine_agent(self, intent: str, user_input: str) -> AgentType:
        """State-aware agent selection."""

        # Emotional state override - always prioritize emotional support
        if self._needs_emotional_support():
            return AgentType.LEARNING_PARTNER

        # Performance-based routing
        if self._needs_difficulty_adjustment():
            return AgentType.LEARNING_MANAGER

        # Intent-based routing
        intent_mapping = {
            "code_review": AgentType.CODE_REVIEWER,
            "problem_help": AgentType.PROBLEM_ANALYZER,
            "contest_prep": AgentType.CONTEST_COACH,
            "emotional_support": AgentType.LEARNING_PARTNER,
            "learning_plan": AgentType.LEARNING_MANAGER,
            "general_question": AgentType.PROBLEM_ANALYZER
        }

        return intent_mapping.get(intent, AgentType.PROBLEM_ANALYZER)

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