"""Unified error codes and AppError exception for ai-agent-lite."""
from app.models.enums import ErrorCode


class AppError(Exception):
    """Application-level error with structured code and detail."""

    def __init__(self, code: ErrorCode, message: str, detail: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)

    def to_ws_dict(self) -> dict:
        """Format for WebSocket error message."""
        payload = {
            "type": "error",
            "data": {
                "type": "error",
                "code": self.code.value,
                "message": self.message,
            },
        }
        return payload