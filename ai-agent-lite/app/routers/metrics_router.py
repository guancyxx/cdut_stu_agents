"""Prometheus metrics endpoint — admin only."""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.metrics import metrics_text
from app.utils.auth_helpers import require_admin_username

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(_: str = Depends(require_admin_username)) -> str:
    return metrics_text()