"""Centralized application configuration.

All environment variable reads are concentrated here.
Other modules should import ``settings`` instead of calling os.getenv directly.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # Database
    db_url: str = os.getenv(
        "LITE_DATABASE_URL",
        "postgresql+asyncpg://onlinejudge:onlinejudge@oj-postgres:5432/onlinejudge",
    )
    db_schema: str = os.getenv("LITE_DB_SCHEMA", "ai_agent")

    # LLM
    llm_base_url: str = os.getenv("LITE_LLM_BASE_URL", "").strip()
    llm_api_key: str = os.getenv("LITE_LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LITE_LLM_MODEL", "deepseek-chat").strip()
    llm_timeout: float = float(os.getenv("LITE_LLM_TIMEOUT", "30"))
    llm_max_retries: int = 2
    llm_retry_delay: float = 2.0

    # Application
    max_context_messages: int = int(os.getenv("LITE_MAX_CONTEXT_MESSAGES", "20"))
    supervisor_enabled: bool = os.getenv("LITE_SUPERVISOR_ENABLED", "1") == "1"
    emotion_analysis_enabled: bool = os.getenv("LITE_EMOTION_ANALYSIS_ENABLED", "1") == "1"
    state_persistence_interval: int = int(os.getenv("LITE_STATE_PERSISTENCE_INTERVAL", "60"))

    # WebSocket
    ws_chunk_size: int = int(os.getenv("LITE_WS_CHUNK_SIZE", "80"))


settings = Settings()