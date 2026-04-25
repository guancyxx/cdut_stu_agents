"""Dependency Injection container — factory functions for service instances.

Provides centralized access to LLM client, supervisor, workers, and suggester.
Application code should use these getters rather than constructing services inline.
"""
import logging

from app.llm_client import LlmClient
from app.services.supervisor import Supervisor
from app.services.next_step_suggester import NextStepSuggester
from app.services.emotion_analyzer import EmotionAnalyzer
from app.i18n import AGENT_DISPLAY, AgentDisplayInfo

logger = logging.getLogger("ai-agent-lite.di")

# ── Singleton instances ─────────────────────────────────────────────────────
_llm: LlmClient | None = None
_supervisor: Supervisor | None = None
_workers: dict | None = None
_suggester: NextStepSuggester | None = None
_emotion_analyzer: EmotionAnalyzer | None = None


def get_llm_client() -> LlmClient:
    """Return the shared LLM client singleton."""
    global _llm
    if _llm is None:
        _llm = LlmClient()
    return _llm


def get_supervisor() -> Supervisor:
    """Return the shared Supervisor singleton."""
    global _supervisor
    if _supervisor is None:
        _supervisor = Supervisor(get_llm_client())
    return _supervisor


def get_workers() -> dict:
    """Return the dict of worker agent instances (lazy-initialized)."""
    global _workers
    if _workers is None:
        from app.workers import (
            CodeReviewerAgent,
            ProblemAnalyzerAgent,
            ContestCoachAgent,
            LearningPartnerAgent,
            LearningManagerAgent,
        )
        llm = get_llm_client()
        _workers = {
            AgentType.CODE_REVIEWER: CodeReviewerAgent(llm),
            AgentType.PROBLEM_ANALYZER: ProblemAnalyzerAgent(llm),
            AgentType.CONTEST_COACH: ContestCoachAgent(llm),
            AgentType.LEARNING_PARTNER: LearningPartnerAgent(llm),
            AgentType.LEARNING_MANAGER: LearningManagerAgent(llm),
        }
    return _workers


def get_suggester() -> NextStepSuggester:
    """Return the shared NextStepSuggester singleton."""
    global _suggester
    if _suggester is None:
        _suggester = NextStepSuggester(get_llm_client())
    return _suggester


def get_emotion_analyzer() -> EmotionAnalyzer:
    """Return the shared EmotionAnalyzer singleton."""
    global _emotion_analyzer
    if _emotion_analyzer is None:
        _emotion_analyzer = EmotionAnalyzer(get_llm_client())
    return _emotion_analyzer


def get_agent_display_name(agent_type) -> str:
    """Return the human-readable display name for an agent type."""
    from app.models.enums import AgentType
    if isinstance(agent_type, AgentType):
        key = agent_type.value
    else:
        key = str(agent_type)
    info: AgentDisplayInfo | None = AGENT_DISPLAY.get(key)
    return info.name if info else key


# Late import to avoid circular dependency
from app.models.enums import AgentType as _AT  # noqa: E402
