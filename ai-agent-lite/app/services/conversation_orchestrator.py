"""Conversation orchestrator — the core turn-processing pipeline.

This module owns the business logic for a single conversation turn:
    route → dispatch → stream → assess → suggest → persist

The WebSocket handler calls into this module via ``process_turn`` and
``process_system_context``, keeping protocol concerns out of business logic.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.di import get_supervisor, get_workers, get_suggester, get_agent_display_name
from app.i18n import TRACE
from app.models.enums import AgentType
from app.repositories import message_repo
from app.services.knowledge_assessor import KnowledgeAssessor
from app.services.problem_context_handler import (
    build_confirmation_message,
    build_default_suggestions,
    build_trace_payload,
    extract_problem_title,
)
from app.services.state_manager import state_manager

logger = logging.getLogger("ai-agent-lite.orchestrator")


async def process_system_context(
    current_state: Dict[str, Any],
    query_text: str,
    session_id: str,
) -> dict:
    """Handle a SYSTEM CONTEXT message (problem selection).

    Returns a dict with the WS events to emit:
        {"confirm_msg": str, "trace": dict, "suggestions": list[dict]}
    Also persists the updated state (side-effect).
    """
    current_state["current_problem_context"] = query_text
    await state_manager.save_state(session_id, current_state)

    problem_title = extract_problem_title(query_text)
    return {
        "confirm_msg": build_confirmation_message(problem_title),
        "trace": build_trace_payload(problem_title),
        "suggestions": build_default_suggestions(problem_title),
    }


async def process_turn(
    query_text: str,
    current_state: Dict[str, Any],
    context: list,
    current_problem_context: str,
    session_id,
    user_id: str,
    db,
    before_kg: dict,
    request_id: uuid.UUID,
) -> dict:
    """Execute one full conversation turn.

    Returns a dict describing all WS events to emit, so the caller
    (websocket.py) can handle the actual sending without knowing
    any business details.
    """
    supervisor = get_supervisor()
    workers = get_workers()
    suggester = get_suggester()

    # --- 1. Route request ---
    agent_type: AgentType = await supervisor.route_request(
        query_text,
        {
            "user_input": query_text,
            "message_history": context,
            "problem_id": current_state.get("current_problem_id"),
            "submitted_code": current_state.get("submitted_code"),
            "user_id": user_id,
            "last_agent_type": current_state.get("last_agent_type"),
            "problem_context": current_problem_context,
        },
        message_history=context,
    )

    # --- 2. Dispatch to worker ---
    worker_state = {**current_state, "current_problem_context": current_problem_context}
    agent_response = await workers[agent_type].process(query_text, worker_state, message_history=context)

    # --- 3. Knowledge delta assessment ---
    assessor = KnowledgeAssessor(supervisor.llm)
    kg_deltas = await assessor.assess(query_text, agent_response.content, agent_type.value)
    kg = current_state.get("knowledge_graph_position") or {}
    for topic, delta_val in kg_deltas.items():
        kg[topic] = round(kg.get(topic, 0.0) + delta_val, 3)
    current_state["knowledge_graph_position"] = kg

    # --- 4. Suggestion generation ---
    after_kg = dict(current_state.get("knowledge_graph_position", {}) or {})
    before_state_for_delta = {"knowledge_graph_position": before_kg}
    after_state_for_delta = {"knowledge_graph_position": after_kg}
    state_delta = state_manager.compute_knowledge_delta(before_state_for_delta, after_state_for_delta)

    next_actions = await suggester.suggest(
        user_input=query_text,
        agent_response=agent_response.content,
        agent_type=agent_type.value,
        state={
            "current_problem_id": current_state.get("current_problem_id", "N/A"),
            "emotion_tags": dict(supervisor.state.emotion_tags),
            "efficiency_trend": supervisor.state.efficiency_trend,
        },
        state_delta=state_delta,
    )

    # --- 5. Persist ---
    current_state["last_agent_type"] = agent_type.value
    await message_repo.create_message(db, session_id, role="user", content=query_text)
    if agent_response.content:
        await message_repo.create_message(db, session_id, role="assistant", content=agent_response.content)
    await state_manager.save_state(str(session_id), current_state)

    # --- 6. Audit ---
    from app.repositories import audit_repo
    await audit_repo.log_event(
        db, event_type="supervisor_complete", request_id=request_id,
        session_id=session_id, user_id=user_id,
        detail={"agent_type": agent_type.value},
    )

    suggestion_summary = "、".join(a.get("title", "") for a in next_actions) if next_actions else "无"

    # --- Build trace payloads from i18n constants ---
    ic = TRACE["intent_classification"]
    ir = TRACE["intent_result"]
    wp = TRACE["worker_processing"]
    sg = TRACE["suggestion_generation"]
    sr = TRACE["suggestion_result"]

    return {
        "agent_type": agent_type,
        "agent_content": agent_response.content,
        "intent_trace": {
            "stage": "intent_classification",
            "title": ic["title"],
            "detail": ic["detail"],
            "output": "",
        },
        "intent_result_trace": {
            "stage": "intent_result",
            "title": ir["title"],
            "detail": ir["detail_routed"].format(agent=get_agent_display_name(agent_type)),
            "output": f"Intent: {getattr(supervisor, '_last_intent', 'N/A')}\nAgent: {agent_type.value}",
        },
        "worker_trace": {
            "stage": "worker_processing",
            "title": wp["title_template"].format(agent=get_agent_display_name(agent_type)),
            "detail": wp["detail"],
            "output": "",
        },
        "suggestion_trace": {
            "stage": "suggestion_generation",
            "title": sg["title"],
            "detail": sg["detail"],
            "output": "",
        },
        "suggestion_result_trace": {
            "stage": "suggestion_result",
            "title": sr["title"],
            "detail": sr["detail_count"].format(count=len(next_actions)),
            "output": f"Suggestions: {suggestion_summary}",
        },
        "next_actions": next_actions,
        "updated_state": current_state,
    }