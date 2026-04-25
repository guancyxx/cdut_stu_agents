"""Dependency injection container — lazily initialises and caches all services.

This module is the single place where the application's object graph is
assembled.  Every other module imports from here rather than constructing
services inline.
"""
import logging
from typing import Dict, Optional

from app.models.enums import AgentType

logger = logging.getLogger("ai-agent-lite.di")

# ---------------------------------------------------------------------------
# Module-level singletons — created once on first access, then reused.
# ---------------------------------------------------------------------------
_llm_client = None
_supervisor = None
_workers: Optional[Dict[AgentType, object]] = None
_suggester = None
_emotion_analyzer = None


def get_llm_client():
    """Return the shared LlmClient singleton."""
    global _llm_client
    if _llm_client is None:
        from app.llm_client import LlmClient
        _llm_client = LlmClient()
    return _llm_client


def get_emotion_analyzer():
    """Return the shared EmotionAnalyzer singleton."""
    global _emotion_analyzer
    if _emotion_analyzer is None:
        from app.services.emotion_analyzer import EmotionAnalyzer
        _emotion_analyzer = EmotionAnalyzer(get_llm_client())
    return _emotion_analyzer


def get_supervisor():
    """Return the shared Supervisor singleton."""
    global _supervisor
    if _supervisor is None:
        from app.services.supervisor import Supervisor
        _supervisor = Supervisor(get_llm_client(), emotion_analyzer=get_emotion_analyzer())
    return _supervisor


def get_workers() -> Dict[AgentType, object]:
    """Return the shared worker-agent mapping singleton."""
    global _workers
    if _workers is None:
        from app.workers.code_reviewer import CodeReviewerAgent
        from app.workers.problem_analyzer import ProblemAnalyzerAgent
        from app.workers.contest_coach import ContestCoachAgent
        from app.workers.learning_partner import LearningPartnerAgent
        from app.workers.learning_manager import LearningManagerAgent

        llm = get_llm_client()
        _workers = {
            AgentType.CODE_REVIEWER: CodeReviewerAgent(llm),
            AgentType.PROBLEM_ANALYZER: ProblemAnalyzerAgent(llm),
            AgentType.CONTEST_COACH: ContestCoachAgent(llm),
            AgentType.LEARNING_PARTNER: LearningPartnerAgent(llm),
            AgentType.LEARNING_MANAGER: LearningManagerAgent(llm),
        }
    return _workers


def get_suggester():
    """Return the shared NextStepSuggester singleton."""
    global _suggester
    if _suggester is None:
        from app.services.next_step_suggester import NextStepSuggester
        _suggester = NextStepSuggester(get_llm_client())
    return _suggester


# ---------------------------------------------------------------------------
# Agent display metadata — centralised here so both WS handler and
# stream_service share a single source of truth.
# ---------------------------------------------------------------------------
AGENT_DISPLAY_INFO = {
    "code_reviewer": {
        "name": "代码审查专家",
        "description": "专注于代码质量、效率和风格评估，提供优化建议",
        "icon": "💻",
        "color": "#5a9fd4",
    },
    "problem_analyzer": {
        "name": "问题解析专家",
        "description": "擅长算法解释和问题拆解，帮助理解题目本质",
        "icon": "🧠",
        "color": "#9f5ad4",
    },
    "contest_coach": {
        "name": "竞赛教练",
        "description": "提供竞赛策略和表现优化建议，提高比赛成绩",
        "icon": "🏆",
        "color": "#d45a5a",
    },
    "learning_partner": {
        "name": "学习伙伴",
        "description": "提供情感支持和学习动力，陪伴学习旅程",
        "icon": "🤝",
        "color": "#5ad47a",
    },
    "learning_manager": {
        "name": "学习管理专家",
        "description": "制定个性化学习路径，管理学习进度和效率",
        "icon": "📊",
        "color": "#d4a05a",
    },
}


def get_agent_display_name(agent_type: AgentType) -> str:
    """Return the Chinese display name for an agent type."""
    return AGENT_DISPLAY_INFO.get(agent_type.value, {}).get("name", agent_type.value)