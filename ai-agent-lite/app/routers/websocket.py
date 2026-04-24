"""WebSocket route handler.

This module is responsible ONLY for the WebSocket protocol layer:
message parsing, validation, and dispatching to the session service.
All business logic lives in services/.
"""
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.errors import AppError, ErrorCode
from app.metrics import ws_connections_active
from app.models.enums import AgentType
from app.repositories import audit_repo, message_repo
from app.services.session_service import get_or_create_session, load_context, extract_problem_context
from app.services.stream_service import send_text_stream
from app.services.state_manager import state_manager

logger = logging.getLogger("ai-agent-lite.ws")

router = APIRouter()

# Module-level singletons — shared across all WS connections
# (avoiding per-connection re-creation per BUG-5 fix)
_workers = None
_supervisor = None
_suggester = None
_emotion_analyzer = None


def _ensure_agents():
    """Lazily initialise supervisor, workers, and suggester on first WS connection."""
    global _workers, _supervisor, _suggester, _emotion_analyzer
    if _workers is not None:
        return

    from app.services.stream_service import get_llm_client
    from app.services.emotion_analyzer import EmotionAnalyzer
    from app.services.next_step_suggester import NextStepSuggester
    from app.services.intent_classifier import IntentClassifier
    from app.services.supervisor import Supervisor
    from app.workers.code_reviewer import CodeReviewerAgent
    from app.workers.problem_analyzer import ProblemAnalyzerAgent
    from app.workers.contest_coach import ContestCoachAgent
    from app.workers.learning_partner import LearningPartnerAgent
    from app.workers.learning_manager import LearningManagerAgent

    llm = get_llm_client()
    _emotion_analyzer = EmotionAnalyzer(llm)
    _supervisor = Supervisor(llm, emotion_analyzer=_emotion_analyzer)
    _workers = {
        AgentType.CODE_REVIEWER: CodeReviewerAgent(llm),
        AgentType.PROBLEM_ANALYZER: ProblemAnalyzerAgent(llm),
        AgentType.CONTEST_COACH: ContestCoachAgent(llm),
        AgentType.LEARNING_PARTNER: LearningPartnerAgent(llm),
        AgentType.LEARNING_MANAGER: LearningManagerAgent(llm),
    }
    _suggester = NextStepSuggester(llm)


@router.websocket("/ws")
async def ws_handler(websocket: WebSocket) -> None:
    """Main WebSocket handler — thin orchestration layer."""
    from app.database import async_session

    _ensure_agents()

    await websocket.accept()
    ws_connections_active.inc()

    session_id_str = websocket.query_params.get("session_id") or websocket.query_params.get("sid") or ""
    user_id = websocket.query_params.get("user_id") or "anonymous"
    request_id = uuid.uuid4()

    async with async_session() as db:
        # Resolve or create session
        session_id, is_new = await get_or_create_session(db, session_id_str, user_id)
        if is_new:
            session_id_str = str(session_id)

        await audit_repo.log_event(
            db, event_type="ws_connect", request_id=request_id,
            session_id=session_id, user_id=user_id, detail={"is_new": is_new})

        # Load or initialise state
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

                try:
                    request = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.send_json(AppError(ErrorCode.INVALID_INPUT, "Invalid JSON").to_ws_dict())
                    await websocket.send_json({"type": "finish"})
                    continue

                req_type = request.get("type")

                if req_type == "list_agents":
                    await websocket.send_json({
                        "type": "list_agents",
                        "data": {"type": "list_agents", "agents": ["ai-agent-lite"]},
                    })
                    continue

                if req_type != "query":
                    await websocket.send_json(
                        AppError(ErrorCode.INVALID_INPUT, f"Unsupported request type: {req_type}").to_ws_dict())
                    await websocket.send_json({"type": "finish"})
                    continue

                content = request.get("content") or {}
                query_text = str(content.get("query", "")).strip()
                if not query_text:
                    await websocket.send_json(
                        AppError(ErrorCode.INVALID_INPUT, "Query cannot be empty").to_ws_dict())
                    await websocket.send_json({"type": "finish"})
                    continue

                # Load conversation context
                context = await load_context(db, session_id)

                # Resolve current problem context
                current_problem_context = current_state.get("current_problem_context", "")
                if not current_problem_context:
                    current_problem_context = extract_problem_context(context)

                # Handle SYSTEM CONTEXT (problem selection) — skip routing
                if query_text.startswith("SYSTEM CONTEXT:"):
                    current_problem_context = query_text
                    current_state["current_problem_context"] = current_problem_context
                    await state_manager.save_state(str(session_id), current_state)

                    problem_title = ""
                    for line in query_text.split("\n"):
                        if line.startswith("Title:"):
                            problem_title = line.replace("Title:", "").strip()
                            break
                    confirm_msg = f"已加载题目「{problem_title}」，有什么想了解的随时问我。" if problem_title else "已加载题目，有什么想了解的随时问我。"
                    await send_text_stream(websocket, confirm_msg)

                    await websocket.send_json({
                        "type": "trace",
                        "data": {
                            "stage": "intent_result",
                            "title": "题目已加载",
                            "detail": f"已加载题目：{problem_title or '未知'}",
                            "output": "Intent: system_context_load (skipped routing)",
                        },
                    })
                    await websocket.send_json({
                        "type": "next_suggestions",
                        "data": {"suggestions": [
                            {"type": "learn", "title": "帮我分析题意", "target": problem_title, "reason": "理解题目是解题的第一步"},
                            {"type": "practice", "title": "给我一个提示", "target": problem_title, "reason": "从提示开始思考"},
                        ]},
                    })
                    await websocket.send_json({"type": "finish"})
                    continue

                if current_problem_context:
                    current_state["current_problem_context"] = current_problem_context

                # Trace 1: intent classification
                await websocket.send_json({
                    "type": "trace",
                    "data": {"stage": "intent_classification", "title": "意图识别", "detail": "正在分析用户意图，确定路由目标...", "output": ""},
                })

                agent_type = await _supervisor.route_request(
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

                await websocket.send_json({
                    "type": "trace",
                    "data": {
                        "stage": "intent_result",
                        "title": "意图识别完成",
                        "detail": f"已路由至 {agent_type.value} 处理",
                        "output": f"Intent: {getattr(_supervisor, '_last_intent', 'N/A')}\nAgent: {agent_type.value}",
                    },
                })

                # Dispatch to worker
                agent_display_name = _super_agent_name(agent_type)
                await websocket.send_json({
                    "type": "trace",
                    "data": {"stage": "worker_processing", "title": f"{agent_display_name} 处理中", "detail": "正在生成回复...", "output": ""},
                })

                selected_worker = _workers[agent_type]
                worker_state = {**current_state, "current_problem_context": current_problem_context}
                agent_response = await selected_worker.process(query_text, worker_state, message_history=context)

                # Send response stream
                await send_text_stream(websocket, agent_response.content, agent_type)

                # Knowledge delta assessment and state update
                kg_deltas = await _supervisor.assess_knowledge_delta(
                    query_text, agent_response.content, agent_type.value)
                kg = current_state.get("knowledge_graph_position") or {}
                for topic, delta_val in kg_deltas.items():
                    kg[topic] = round(kg.get(topic, 0.0) + delta_val, 3)
                current_state["knowledge_graph_position"] = kg

                # Trace 2: suggestion generation
                await websocket.send_json({
                    "type": "trace",
                    "data": {"stage": "suggestion_generation", "title": "生成下一步建议", "detail": "正在分析知识变化，生成个性化建议...", "output": ""},
                })

                after_kg = dict(current_state.get("knowledge_graph_position", {}) or {})
                before_state_for_delta = {"knowledge_graph_position": before_kg}
                after_state_for_delta = {"knowledge_graph_position": after_kg}
                state_delta = state_manager.compute_knowledge_delta(before_state_for_delta, after_state_for_delta)

                next_actions = await _supervisor.get_next_actions(
                    agent_response.content, agent_type, suggester=_suggester, state_delta=state_delta)

                if next_actions:
                    await websocket.send_json({"type": "next_suggestions", "data": {"suggestions": next_actions}})

                suggestion_summary = ", ".join(a.get("title", "") for a in next_actions) if next_actions else "无"
                await websocket.send_json({
                    "type": "trace",
                    "data": {"stage": "suggestion_result", "title": "建议生成完成", "detail": f"已生成 {len(next_actions)} 条建议", "output": suggestion_summary},
                })

                # Track which agent handled this turn
                current_state["last_agent_type"] = agent_type.value

                # Persist both user and assistant messages
                await message_repo.create_message(db, session_id, role="user", content=query_text)
                if agent_response.content:
                    await message_repo.create_message(db, session_id, role="assistant", content=agent_response.content)

                await state_manager.save_state(str(session_id), current_state)

                # Refresh before_kg for next turn's delta computation
                before_kg = dict(current_state.get("knowledge_graph_position", {}) or {})

                await audit_repo.log_event(db, event_type="supervisor_complete", request_id=request_id,
                    session_id=session_id, user_id=user_id,
                    detail={"agent_type": agent_type.value})

                await websocket.send_json({"type": "finish"})

        except WebSocketDisconnect:
            await audit_repo.log_event(db, event_type="ws_disconnect", request_id=request_id,
                session_id=session_id, user_id=user_id)
        except Exception as exc:
            logger.exception("WS handler error: %s", exc)
            await audit_repo.log_event(db, event_type="ws_error", request_id=request_id,
                session_id=session_id, user_id=user_id, detail={"error": str(exc)})
    ws_connections_active.dec()


def _super_agent_name(agent_type: AgentType) -> str:
    """Chinese display name for agent types (kept near the WS layer where it's used)."""
    mapping = {
        "code_reviewer": "代码审查专家",
        "problem_analyzer": "问题解析专家",
        "contest_coach": "竞赛教练",
        "learning_partner": "学习伙伴",
        "learning_manager": "学习管理专家",
    }
    return mapping.get(agent_type.value, agent_type.value)