"""Health and readiness check endpoints."""
from fastapi import APIRouter

from app.config import settings

router = APIRouter()

# LLM client is injected at app startup; resolved lazily via module import.
from app.services.stream_service import get_llm_client  # noqa: E402


@router.get("/healthz")
async def healthz() -> dict:
    llm = get_llm_client()
    return {
        "ok": True,
        "llm_enabled": llm.enabled,
        "model": llm.model,
    }


@router.get("/readyz")
async def readyz() -> dict:
    from app.database import async_session
    from sqlalchemy import text

    llm = get_llm_client()
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
            await db.commit()
        db_ok = True
    except Exception as exc:
        import logging
        logging.getLogger("ai-agent-lite").error("Readiness DB check failed: %s", exc)
        db_ok = False

    return {
        "ok": db_ok and llm.enabled,
        "db": db_ok,
        "llm": llm.enabled,
        "model": llm.model,
    }