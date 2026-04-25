"""User-facing string constants — centralized to keep Chinese out of code files.

All end-user visible text (displayed in the frontend) is centralized here.
Internal trace/debug messages use English directly in code.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDisplayInfo:
    """Display metadata for each agent role — shown in the frontend trace panel."""
    name: str
    description: str


AGENT_DISPLAY: dict[str, AgentDisplayInfo] = {
    "code_reviewer": AgentDisplayInfo(
        name="Code Reviewer",
        description="Code quality, efficiency, and style evaluation with optimization tips",
    ),
    "problem_analyzer": AgentDisplayInfo(
        name="Problem Analyzer",
        description="Algorithm explanation and problem decomposition for deeper understanding",
    ),
    "contest_coach": AgentDisplayInfo(
        name="Contest Coach",
        description="Competition strategy and performance optimization guidance",
    ),
    "learning_partner": AgentDisplayInfo(
        name="Learning Partner",
        description="Warm emotional support and study motivation companion",
    ),
    "learning_manager": AgentDisplayInfo(
        name="Learning Manager",
        description="Personalized study planning, progress tracking, and learning efficiency",
    ),
}

# ── Default suggestions shown after a problem is loaded ────────────────────
# These are phrased as what the student would naturally say/ask next.
DEFAULT_SUGGESTIONS = [
    {
        "type": "learn",
        "title": "What is this problem testing?",
        "target": "$problem_title",
        "reason": "Understand the core concept before diving into code",
    },
    {
        "type": "practice",
        "title": "Give me a hint to get started",
        "target": "$problem_title",
        "reason": "A small nudge is better than staring at the screen",
    },
]

# ── Confirmation messages sent to the frontend ─────────────────────────────

def problem_loaded_msg(problem_title: str) -> str:
    """Build the confirmation shown when a problem is loaded."""
    if problem_title:
        return f'Alright, problem "{problem_title}" is loaded. Let\'s figure out where to start.'
    return "Problem loaded. Ask me anything whenever you're stuck!"


ERROR_FALLBACK = {
    "learning_partner": "I'm here — take your time, we can keep going.",
    "learning_manager": "Something went wrong, please try again in a moment.",
    "code_reviewer": "Code analysis temporarily unavailable.",
    "problem_analyzer": "Problem analysis temporarily unavailable.",
    "contest_coach": "Competition coaching temporarily unavailable.",
}