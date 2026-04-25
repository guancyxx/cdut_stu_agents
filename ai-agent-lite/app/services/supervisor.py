"""Supervisor agent — context-aware multi-agent router.

Routes student requests to specialized workers based on intent classification,
emotional state, and conversation continuity.

NOTE: Knowledge delta assessment and suggestion generation have been moved
to their own services (KnowledgeAssessor, NextStepSuggester) and are
orchestrated by conversation_orchestrator.py directly.
"""
import logging
from typing import Dict, Any, List

from app.models.enums import AgentType
from app.models.schemas import StudentState

logger = logging.getLogger("ai-agent-lite.supervisor")


class Supervisor:
    """Context-aware routing supervisor that orchestrates multi-agent conversations."""

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
        """Determine which agent should handle this request."""
        self._last_user_input = user_input
        self._message_history = message_history or []

        await self._update_state_from_context(session_context)

        intent = await self._classify_intent(user_input, self._message_history)
        self._last_intent = intent

        agent_type = self._determine_agent(intent, user_input, self._message_history)
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
        """Delegate intent classification to the IntentClassifier service."""
        from app.services.intent_classifier import IntentClassifier
        classifier = IntentClassifier(self.llm, self.state, self._problem_context)
        return await classifier.classify(user_input, message_history)

    def _determine_agent(
        self,
        intent: str,
        user_input: str,
        message_history: List[Dict[str, str]] = None,
    ) -> AgentType:
        """Context-aware agent selection with teaching flow continuity."""
        if self._needs_emotional_support():
            return AgentType.LEARNING_PARTNER

        if self._needs_difficulty_adjustment():
            return AgentType.LEARNING_MANAGER

        if intent == "casual":
            return AgentType.LEARNING_PARTNER

        if self._problem_context and intent in ("off_topic", "general_question"):
            if self.state.last_agent_type and self.state.last_agent_type in (
                "problem_analyzer", "learning_manager", "code_reviewer"
            ):
                try:
                    return AgentType(self.state.last_agent_type)
                except ValueError:
                    pass
            return AgentType.PROBLEM_ANALYZER

        if intent == "answer_to_coach" and self.state.last_agent_type:
            try:
                return AgentType(self.state.last_agent_type)
            except ValueError:
                pass

        if self.state.last_agent_type and self._is_continuation_of_same_flow(intent):
            try:
                return AgentType(self.state.last_agent_type)
            except ValueError:
                pass

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
        """Check if the current intent logically belongs to the previous agent's domain."""
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
        return self.state.efficiency_trend < 0.7

    async def _update_state_from_context(self, context: Dict[str, Any]):
        """Update state from session context. Uses LLM-based emotion analysis."""
        if "problem_id" in context:
            self.state.current_problem_id = context["problem_id"]
        if "submitted_code" in context:
            self.state.submitted_code = context["submitted_code"]
        if "last_agent_type" in context and context["last_agent_type"]:
            self.state.last_agent_type = context["last_agent_type"]
        if "problem_context" in context and context["problem_context"]:
            self._problem_context = context["problem_context"]
        await self._analyze_emotional_state_async(
            context.get("user_input", ""),
            context.get("message_history", []),
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