"""Shared utility functions for prompt construction."""
from typing import Any, Dict, List


def build_history_block(
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


def build_problem_anchor_block(state: Dict[str, Any]) -> str:
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