"""
Request ID + timing middleware for ai-agent-lite.
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestMiddleware(BaseHTTPMiddleware):
    """Attach request_id and measure request duration."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = uuid.UUID(request_id) if isinstance(request_id, str) else request_id
        request.state.start_time = time.monotonic()

        response: Response = await call_next(request)
        duration = time.monotonic() - request.state.start_time
        response.headers["X-Request-ID"] = str(request_id)
        response.headers["X-Request-Duration"] = f"{duration:.4f}"
        return response