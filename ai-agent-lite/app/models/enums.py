"""Enumerations for the ai-agent-lite domain."""
from enum import Enum


class AgentType(str, Enum):
    CODE_REVIEWER = "code_reviewer"
    PROBLEM_ANALYZER = "problem_analyzer"
    CONTEST_COACH = "contest_coach"
    LEARNING_PARTNER = "learning_partner"
    LEARNING_MANAGER = "learning_manager"
    NEXT_STEP_SUGGESTER = "next_step_suggester"


class CompletionStatus(str, Enum):
    COMPLETE = "complete"
    NEEDS_FOLLOWUP = "needs_followup"
    ERROR = "error"


class ErrorCode(str, Enum):
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_SERVER_ERROR = "LLM_SERVER_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    INTERNAL = "INTERNAL"