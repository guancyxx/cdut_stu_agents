"""Problem context handler — processes SYSTEM CONTEXT messages from the frontend.

When a student selects an OJ problem, the frontend sends a structured
message starting with "SYSTEM CONTEXT:".  This module isolates that
special-case handling from the main conversation flow.
"""
from app.i18n import DEFAULT_SUGGESTIONS, problem_loaded_msg


def is_system_context(text: str) -> bool:
    """Check whether an inbound message is a SYSTEM CONTEXT directive."""
    return text.startswith("SYSTEM CONTEXT:")


def extract_problem_title(context_text: str) -> str:
    """Parse the problem title from a SYSTEM CONTEXT message."""
    for line in context_text.split("\n"):
        if line.startswith("Title:"):
            return line.replace("Title:", "").strip()
    return ""


def build_confirmation_message(problem_title: str) -> str:
    """Build the confirmation message shown to the student."""
    return problem_loaded_msg(problem_title)


def build_default_suggestions(problem_title: str) -> list[dict[str, str]]:
    """Return the default suggestion list shown after a problem is loaded.

    Suggestions are phrased as what the student would naturally say next.
    """
    target = problem_title or "this problem"
    return [
        {**s, "target": target, "reason": s["reason"]}
        for s in DEFAULT_SUGGESTIONS
    ]


def build_trace_payload(problem_title: str) -> dict:
    """Build the trace event payload sent after processing SYSTEM CONTEXT."""
    return {
        "stage": "intent_result",
        "title": "Problem Loaded",
        "detail": f"Loaded problem: {problem_title or 'unknown'}",
        "output": "Intent: system_context_load (skipped routing)",
    }