"""Streaming service — text chunking and agent info dispatch over WebSocket."""
import logging
from typing import Optional

from fastapi import WebSocket

from app.models.enums import AgentType

logger = logging.getLogger("ai-agent-lite.stream")

# Module-level singleton LLM client (shared across all connections).
_llm_client = None


def get_llm_client():
    """Return the shared LlmClient singleton, creating it on first access."""
    global _llm_client
    if _llm_client is None:
        from app.llm_client import LlmClient
        _llm_client = LlmClient()
    return _llm_client


# Agent metadata mapping (used by _send_text_stream for agent_info events).
_AGENT_INFO = {
    "code_reviewer": {
        "name": "代码审查专家",
        "description": "专注于代码质量、效率和风格评估，提供优化建议",
        "icon": "💻",
        "color": "#5a9fd4",
    },
    "problem_analyzer": {
        "name": "问题解析专家",
        "description": "擅长算法解释和问题拆解，帮助理解题目本质",
        "icon": "🧠",
        "color": "#9f5ad4",
    },
    "contest_coach": {
        "name": "竞赛教练",
        "description": "提供竞赛策略和表现优化建议，提高比赛成绩",
        "icon": "🏆",
        "color": "#d45a5a",
    },
    "learning_partner": {
        "name": "学习伙伴",
        "description": "提供情感支持和学习动力，陪伴学习旅程",
        "icon": "🤝",
        "color": "#5ad47a",
    },
    "learning_manager": {
        "name": "学习管理专家",
        "description": "制定个性化学习路径，管理学习进度和效率",
        "icon": "📊",
        "color": "#d4a05a",
    },
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
        agent_data = _AGENT_INFO.get(agent_key, {
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