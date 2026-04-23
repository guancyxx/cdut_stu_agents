"""
ai-agent-lite: Lightweight FastAPI AI agent with persistent sessions.

WebSocket protocol:
  Client -> Server:  {"type":"query","content":{"query":"..."}, "session_id":"..."}
  Server -> Client:  {"type":"init","data":{...}}
  Server -> Client:  {"type":"raw","data":{"type":"text","delta":"...","inprogress":bool}}
  Server -> Client:  {"type":"finish"}
  Server -> Client:  {"type":"error","data":{"type":"error","code":"...","message":"..."}}
"""
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.database import get_session, init_db, async_session
from app.errors import AppError, ErrorCode
from app.llm_client import LlmClient
from app.metrics import ws_connections_active, ws_messages_total, llm_request_duration_seconds, llm_errors_total, db_operations_total, metrics_text
from app.middleware import RequestMiddleware
from app.repositories import session_repo, message_repo
from app.supervisor import Supervisor, AgentType
from app.workers import CodeReviewerAgent, ProblemAnalyzerAgent, ContestCoachAgent, LearningPartnerAgent, LearningManagerAgent
from app.state_manager import state_manager

logger = logging.getLogger("ai-agent-lite")

llm = LlmClient()

# Supervisor configuration
SUPERVISOR_ENABLED = True
MAX_CONTEXT_MESSAGES = 20
STATE_PERSISTENCE_INTERVAL = 60  # seconds
EMOTION_ANALYSIS_ENABLED = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized. LLM enabled=%s model=%s", llm.enabled, llm.model)
    yield


app = FastAPI(title="ai-agent-lite", lifespan=lifespan)
app.add_middleware(RequestMiddleware)


# ---------------------------------------------------------------------------
# HTTP Endpoints
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict:
    return {
        "ok": True,
        "llm_enabled": llm.enabled,
        "model": llm.model,
    }


@app.get("/readyz")
async def readyz() -> dict:
    """Readiness probe: check database connectivity."""
    try:
        async with async_session() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            await db.commit()
        db_ok = True
    except Exception as exc:
        logger.error("Readiness DB check failed: %s", exc)
        db_ok = False

    return {
        "ok": db_ok and llm.enabled,
        "db": db_ok,
        "llm": llm.enabled,
        "model": llm.model,
    }


@app.get("/metrics")
async def metrics() -> dict:
    return {"content": metrics_text(), "media_type": "text/plain"}


# ---------------------------------------------------------------------------
# WebSocket Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_session(
    db: AsyncSession,
    session_id_str: str,
    user_id: str,
) -> tuple:
    """Load existing session or create a new one. Returns (session_id_uuid, is_new)."""
    try:
        sid = uuid.UUID(session_id_str)
        existing = await session_repo.get_session(db, sid)
        if existing and existing.user_id == user_id:
            return existing.id, False
    except (ValueError, AttributeError):
        pass

    new_session = await session_repo.create_session(db, user_id=user_id)
    return new_session.id, True


async def _load_context(db: AsyncSession, session_id: uuid.UUID) -> list[dict]:
    """Load recent messages as LLM context dicts."""
    msgs = await message_repo.list_messages_as_dicts(db, session_id, limit=MAX_CONTEXT_MESSAGES)
    return msgs


async def _stream_llm_response(
    websocket: WebSocket,
    db: AsyncSession,
    session_id: uuid.UUID,
    request_id: uuid.UUID,
    user_id: str,
    query_text: str,
) -> str:
    """Call LLM, stream tokens to client, persist the assistant response. Returns full text."""
    ws_messages_total.labels(direction="in", msg_type="query").inc()

    # Persist user message
    await message_repo.create_message(db, session_id, role="user", content=query_text)
    db_operations_total.labels(operation="insert", table="messages").inc()

    # Build context
    context = await _load_context(db, session_id)
    # Include current message if not already in history
    if not context or context[-1].get("content") != query_text:
        context.append({"role": "user", "content": query_text})

    # Call LLM
    full_text = ""
    start_time = __import__("time").monotonic()
    try:
        async for chunk in llm.stream(context):
            full_text += chunk
            await websocket.send_json({
                "type": "raw",
                "data": {"type": "text", "delta": chunk, "inprogress": True},
            })
    except AppError as exc:
        llm_errors_total.labels(code=exc.code.value).inc()
        # Fallback to non-streaming
        await log_event(db, event_type="llm_stream_fallback", request_id=request_id,
                        session_id=session_id, user_id=user_id, detail={"code": exc.code.value})
        try:
            full_text = await llm.complete(context)
            await _send_text_stream(websocket, full_text)
        except AppError as inner_exc:
            await websocket.send_json(inner_exc.to_ws_dict())
            await websocket.send_json({"type": "finish"})
            await log_event(db, event_type="llm_error", request_id=request_id,
                            session_id=session_id, user_id=user_id,
                            detail={"code": inner_exc.code.value, "message": inner_exc.message})
            return ""

    duration = __import__("time").monotonic() - start_time
    llm_request_duration_seconds.observe(duration)
    ws_messages_total.labels(direction="out", msg_type="raw").inc()

    # Persist assistant message
    if full_text:
        await message_repo.create_message(db, session_id, role="assistant", content=full_text)
        db_operations_total.labels(operation="insert", table="messages").inc()

    await log_event(db, event_type="llm_complete", request_id=request_id,
                    session_id=session_id, user_id=user_id,
                    detail={"duration_s": round(duration, 3), "chars": len(full_text)})

    return full_text


async def _send_text_stream(websocket: WebSocket, content: str, chunk_size: int = 80) -> None:
    """Send a complete string as chunked streaming messages."""
    if not content:
        await websocket.send_json({"type": "raw", "data": {"type": "text", "delta": "", "inprogress": False}})
        return
    start = 0
    total = len(content)
    while start < total:
        end = min(start + chunk_size, total)
        piece = content[start:end]
        await websocket.send_json({
            "type": "raw",
            "data": {"type": "text", "delta": piece, "inprogress": end < total},
        })
        start = end


# ---------------------------------------------------------------------------
# WebSocket Handler
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def ws_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    ws_connections_active.inc()

    session_id_str = websocket.query_params.get("session_id") or websocket.query_params.get("sid") or ""
    user_id = websocket.query_params.get("user_id") or "anonymous"

    request_id = uuid.uuid4()

    # Open DB session for this connection
    async with async_session() as db:
        # Resolve or create the session
        session_id, is_new = await _get_or_create_session(db, session_id_str, user_id)
        if is_new:
            # Update session_id_str to the newly generated UUID
            session_id_str = str(session_id)

        await log_event(db, event_type="ws_connect", request_id=request_id,
                        session_id=session_id, user_id=user_id,
                        detail={"is_new": is_new})

        # Initialize supervisor and workers
        supervisor = Supervisor(llm)
        workers = {
            AgentType.CODE_REVIEWER: CodeReviewerAgent(llm),
            AgentType.PROBLEM_ANALYZER: ProblemAnalyzerAgent(llm),
            AgentType.CONTEST_COACH: ContestCoachAgent(llm),
            AgentType.LEARNING_PARTNER: LearningPartnerAgent(llm),
            AgentType.LEARNING_MANAGER: LearningManagerAgent(llm)
        }
        
        # Load or initialize state
        current_state = await state_manager.load_state(str(session_id))
        state_manager.update_from_context(current_state, {
            "problem_id": websocket.query_params.get("problem_id"),
            "user_id": user_id
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
                        AppError(ErrorCode.INVALID_INPUT, f"Unsupported request type: {req_type}").to_ws_dict()
                    )
                    await websocket.send_json({"type": "finish"})
                    continue

                content = request.get("content") or {}
                query_text = str(content.get("query", "")).strip()
                if not query_text:
                    await websocket.send_json(
                        AppError(ErrorCode.INVALID_INPUT, "Query cannot be empty").to_ws_dict()
                    )
                    await websocket.send_json({"type": "finish"})
                    continue

                # Use supervisor pattern for advanced routing
                agent_type = await supervisor.route_request(query_text, {
                    "message_history": context,
                    "problem_id": current_state.get("current_problem_id"),
                    "submitted_code": current_state.get("submitted_code"),
                    "user_id": user_id
                })
                
                # Dispatch to specialized worker
                selected_worker = workers[agent_type]
                agent_response = await selected_worker.process(query_text, current_state)
                
                # Generate next actions
                next_actions = await supervisor.get_next_actions(agent_response.content, agent_type)
                
                # Combine response with next actions
                full_response = f"{agent_response.content}\n\n---\n\n**下一步建议:**\n"
                for action in next_actions:
                    full_response += f"• {action['title']}: {action['reason']}\n"
                
                # Send response
                await _send_text_stream(websocket, full_response)
                
                # Persist assistant message
                if full_response:
                    await message_repo.create_message(db, session_id, role="assistant", content=full_response)
                    db_operations_total.labels(operation="insert", table="messages").inc()
                
                # Update state with this interaction
                await state_manager.save_state(str(session_id), current_state)
                
                await log_event(db, event_type="supervisor_complete", request_id=request_id,
                                session_id=session_id, user_id=user_id,
                                detail={"agent_type": agent_type.value, "next_actions_count": len(next_actions)})
                
                await websocket.send_json({"type": "finish"})

        except WebSocketDisconnect:
            await log_event(db, event_type="ws_disconnect", request_id=request_id,
                            session_id=session_id, user_id=user_id)
        except Exception as exc:
            logger.exception("WS handler error: %s", exc)
            await log_event(db, event_type="ws_error", request_id=request_id,
                            session_id=session_id, user_id=user_id,
                            detail={"error": str(exc)})
    ws_connections_active.dec()