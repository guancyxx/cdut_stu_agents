"""Streaming service — text chunking and agent info dispatch over WebSocket."""
import logging
from typing import Optional

from fastapi import WebSocket

from app.models.enums import AgentType
from app.i18n import AGENT_DISPLAY

logger = logging.getLogger("ai-agent-lite.stream")

# Default agent styling for frontend display
_AGENT_STYLING = {
    "code_reviewer": {"icon": "\U0001f50d", "color": "#4CAF50"},
    "problem_analyzer": {"icon": "\U0001f4ca", "color": "#2196F3"},
    "contest_coach": {"icon": "\U0001f3c6", "color": "#FF9800"},
    "learning_partner": {"icon": "\U0001f91d", "color": "#9C27B0"},
    "learning_manager": {"icon": "\U0001f4da", "color": "#607D8B"},
}


async def send_text_stream(
    websocket: WebSocket,
    content: str,
    agent_type: Optional[AgentType] = None,
    chunk_size: int = 80,
) -> None:
    """Send a complete string as chunked streaming messages with optional agent info."""
    if not content:
        await websocket.send_json({"type": "raw", "data": {"type": "text", "delta": "", "inprogress": False}})
        return

    # Send agent info at the beginning if available
    if agent_type:
        agent_key = agent_type.value
        display = AGENT_DISPLAY.get(agent_key)
        styling = _AGENT_STYLING.get(agent_key, {"icon": "\U0001f916", "color": "#666666"})
        await websocket.send_json({
            "type": "agent_info",
            "data": {
                "agent_type": agent_key,
                "agent_name": display.name if display else agent_key.replace("_", " ").title(),
                "agent_description": display.description if display else "",
                "agent_icon": styling["icon"],
                "agent_color": styling["color"],
            },
        })

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