"""Prometheus metrics endpoint."""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.metrics import metrics_text

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    return metrics_text()