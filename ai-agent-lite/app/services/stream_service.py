"""Streaming service — text chunking and agent info dispatch over WebSocket."""
import logging
from typing import Optional

from fastapi import WebSocket

from app.models.enums import AgentType

logger = logging.getLogger("ai-agent-lite.stream")


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
        from app.di import AGENT_DISPLAY_INFO
        agent_key = agent_type.value
        agent_data = AGENT_DISPLAY_INFO.get(agent_key, {
            "name": agent_key.replace("_", " ").title(),
            "description": "",
            "icon": "🤖",
            "color": "#666666",
        })
        await websocket.send_json({
            "type": "agent_info",
            "data": {
                "agent_type": agent_key,
                "agent_name": agent_data["name"],
                "agent_description": agent_data["description"],
                "agent_icon": agent_data["icon"],
                "agent_color": agent_data["color"],
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