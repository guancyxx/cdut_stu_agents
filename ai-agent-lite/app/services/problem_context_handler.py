"""Problem context handler — processes SYSTEM CONTEXT messages from the frontend.

When a student selects an OJ problem, the frontend sends a structured
message starting with "SYSTEM CONTEXT:".  This module isolates that
special-case handling from the main conversation flow.
"""
from typing import Any


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
    """Build the Chinese confirmation message shown to the student."""
    if problem_title:
        return f"已加载题目「{problem_title}」，有什么想了解的随时问我。"
    return "已加载题目，有什么想了解的随时问我。"


def build_default_suggestions(problem_title: str) -> list[dict[str, str]]:
    """Return the default suggestion list shown after a problem is loaded."""
    target = problem_title or "当前题目"
    return [
        {"type": "learn", "title": "帮我分析题意", "target": target, "reason": "理解题目是解题的第一步"},
        {"type": "practice", "title": "给我一个提示", "target": target, "reason": "从提示开始思考"},
    ]


def build_trace_payload(problem_title: str) -> dict[str, Any]:
    """Build the trace event payload sent after processing SYSTEM CONTEXT."""
    return {
        "stage": "intent_result",
        "title": "题目已加载",
        "detail": f"已加载题目：{problem_title or '未知'}",
        "output": "Intent: system_context_load (skipped routing)",
    }