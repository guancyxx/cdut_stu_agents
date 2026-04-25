"""
ai-agent-lite: Lightweight FastAPI AI agent with persistent sessions.

WebSocket protocol:
  Client -> Server:  {"type":"query","content":{"query":"..."}, "session_id":"..."}
  Server -> Client:  {"type":"init","data":{...}}
  Server -> Client:  {"type":"raw","data":{"type":"text","delta":"...","inprogress":bool}}
  Server -> Client:  {"type":"finish"}
  Server -> Client:  {"type":"error","data":{"type":"error","code":"...","message":"..."}}
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.middleware import RequestMiddleware
from app.routers import health, metrics_router, problem_audit, websocket

logger = logging.getLogger("ai-agent-lite")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    logger.info("Initializing database...")
    await init_db()
    from app.di import get_llm_client
    llm = get_llm_client()
    logger.info("Database initialized. LLM enabled=%s model=%s", llm.enabled, llm.model)
    yield


def create_app() -> FastAPI:
    """Application factory — compose routes and middleware."""
    app = FastAPI(title="ai-agent-lite", lifespan=lifespan)
    app.add_middleware(RequestMiddleware)
    app.include_router(health.router)
    app.include_router(metrics_router.router)
    app.include_router(problem_audit.router)
    app.include_router(websocket.router)
    return app


app = create_app()