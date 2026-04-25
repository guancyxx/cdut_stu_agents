"""WebSocket route handler — thin protocol layer only.

This module is responsible ONLY for the WebSocket protocol:
    connection lifecycle, message parsing, and dispatching to services.
All business logic lives in app/services/conversation_orchestrator.py
and app/services/problem_context_handler.py.
"""
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.config import settings
from app.errors import AppError, ErrorCode
from app.metrics import ws_connections_active
from app.models.ws_messages import WsRawMessage, WsQueryContent, WsQueryMessage
from app.repositories import audit_repo
from app.services.conversation_orchestrator import process_turn, process_system_context
from app.services.problem_context_handler import is_system_context
from app.services.session_service import get_or_create_session, load_context, extract_problem_context
from app.services.state_manager import state_manager
from app.services.stream_service import send_text_stream

logger = logging.getLogger("ai-agent-lite.ws")

router = APIRouter()


def _parse_ws_message(raw: str):
    """Parse and validate an inbound WS message.

    Returns (req_type, validated_query_content) on success.
    Returns (AppError, None) on validation failure.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AppError(ErrorCode.INVALID_INPUT, "Invalid JSON"), None

    try:
        raw_msg = WsRawMessage(type=data.get("type", ""))
    except ValidationError:
        return AppError(ErrorCode.INVALID_INPUT, f"Unsupported request type: {data.get('type')}"), None

    if raw_msg.type == "list_agents":
        return "list_agents", None

    try:
        query_msg = WsQueryMessage.model_validate(data)
        return "query", query_msg.content
    except ValidationError as exc:
        details = "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in exc.errors())
        return AppError(ErrorCode.INVALID_INPUT, f"Validation error: {details}"), None


@router.websocket("/ws")
async def ws_handler(websocket: WebSocket) -> None:
    """Main WebSocket handler — thin protocol layer."""
    from app.database import async_session
    from app.di import get_supervisor

    # Ensure services are initialised on first connection
    _ = get_supervisor()

    await websocket.accept()
    ws_connections_active.inc()

    session_id_str = websocket.query_params.get("session_id") or websocket.query_params.get("sid") or ""
    user_id = websocket.query_params.get("user_id") or "anonymous"
    request_id = uuid.uuid4()

    async with async_session() as db:
        session_id, is_new = await get_or_create_session(db, session_id_str, user_id)
        if is_new:
            session_id_str = str(session_id)

        await audit_repo.log_event(
            db, event_type="ws_connect", request_id=request_id,
            session_id=session_id, user_id=user_id, detail={"is_new": is_new})

        current_state = await state_manager.load_state(str(session_id))
        before_kg = dict(current_state.get("knowledge_graph_position", {}) or {})

        state_manager.update_from_context(current_state, {
            "problem_id": websocket.query_params.get("problem_id"),
            "user_id": user_id,
        })

        try:
            while True:
                raw_message = await websocket.receive_text()
                request_id = uuid.uuid4()

                result, query_content = _parse_ws_message(raw_message)

                if isinstance(result, AppError):
                    await websocket.send_json(result.to_ws_dict())
                    await websocket.send_json({"type": "finish"})
                    continue

                req_type = result

                if req_type == "list_agents":
                    await websocket.send_json({
                        "type": "list_agents",
                        "data": {"type": "list_agents", "agents": ["ai-agent-lite"]},
                    })
                    continue

                # req_type == "query"
                query_text = query_content.query
                context = await load_context(db, session_id)
                current_problem_context = current_state.get("current_problem_context", "")
                if not current_problem_context:
                    current_problem_context = extract_problem_context(context)

                # Handle SYSTEM CONTEXT (problem selection) — skip routing
                if is_system_context(query_text):
                    result_data = await process_system_context(current_state, query_text, str(session_id))
                    await send_text_stream(websocket, result_data["confirm_msg"])
                    await websocket.send_json({"type": "trace", "data": result_data["trace"]})
                    await websocket.send_json({"type": "next_suggestions", "data": {"suggestions": result_data["suggestions"]}})
                    await websocket.send_json({"type": "finish"})
                    continue

                if current_problem_context:
                    current_state["current_problem_context"] = current_problem_context

                # --- Normal query: full turn pipeline ---
                await websocket.send_json({"type": "trace", "data": {
                    "stage": "intent_classification", "title": "意图识别",
                    "detail": "正在分析用户意图，确定路由目标...", "output": "",
                }})

                turn = await process_turn(
                    query_text=query_text,
                    current_state=current_state,
                    context=context,
                    current_problem_context=current_problem_context,
                    session_id=session_id,
                    user_id=user_id,
                    db=db,
                    before_kg=before_kg,
                    request_id=request_id,
                )

                # Emit trace & stream events
                await websocket.send_json({"type": "trace", "data": turn["intent_result_trace"]})
                await websocket.send_json({"type": "trace", "data": turn["worker_trace"]})
                await send_text_stream(websocket, turn["agent_content"], turn["agent_type"])
                await websocket.send_json({"type": "trace", "data": turn["suggestion_trace"]})

                if turn["next_actions"]:
                    await websocket.send_json({"type": "next_suggestions", "data": {"suggestions": turn["next_actions"]}})

                await websocket.send_json({"type": "trace", "data": turn["suggestion_result_trace"]})
                await websocket.send_json({"type": "finish"})

                # Refresh before_kg for next turn
                before_kg = dict(turn["updated_state"].get("knowledge_graph_position", {}) or {})
                current_state = turn["updated_state"]

        except WebSocketDisconnect:
            await audit_repo.log_event(db, event_type="ws_disconnect", request_id=request_id,
                session_id=session_id, user_id=user_id)
        except Exception as exc:
            logger.exception("WS handler error: %s", exc)
            await audit_repo.log_event(db, event_type="ws_error", request_id=request_id,
                session_id=session_id, user_id=user_id, detail={"error": str(exc)})
    ws_connections_active.dec()