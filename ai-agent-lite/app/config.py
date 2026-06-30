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
        "postgresql+asyncpg://cdut:cdut_oj_2024@cdut-postgres:5432/cdut_oj",
    )
    db_schema: str = os.getenv("LITE_DB_SCHEMA", "ai_agent")

    # LLM (cloud API — used by chat agents)
    llm_base_url: str = os.getenv("LITE_LLM_BASE_URL", "").strip()
    llm_api_key: str = os.getenv("LITE_LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LITE_LLM_MODEL", "deepseek-chat").strip()
    llm_timeout: float = float(os.getenv("LITE_LLM_TIMEOUT", "30"))
    llm_max_retries: int = 2
    llm_retry_delay: float = 2.0

    # Background-audit LLM
    audit_llm_provider: str = os.getenv("LITE_AUDIT_LLM_PROVIDER", "xiaomi").strip()
    audit_llm_api_key: str = os.getenv("LITE_AUDIT_LLM_API_KEY", "").strip()
    audit_llm_base_url: str = os.getenv(
        "LITE_AUDIT_LLM_BASE_URL",
        "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
    ).strip()
    audit_llm_model: str = os.getenv("LITE_AUDIT_LLM_MODEL", "mimo-v2-pro").strip()
    audit_llm_timeout: float = float(os.getenv("LITE_AUDIT_LLM_TIMEOUT", "180"))

    audit_beat_interval: int = int(os.getenv("LITE_AUDIT_BEAT_INTERVAL", "100"))

    # Celery / Redis
    celery_broker_url: str = os.getenv("LITE_CELERY_BROKER", "redis://cdut-redis:6379/1")
    celery_result_backend: str = os.getenv("LITE_CELERY_BACKEND", "redis://cdut-redis:6379/2")

    # Judge sandbox
    judge_sandbox_url: str = os.getenv("LITE_JUDGE_SANDBOX_URL", "http://cdut-sandbox:8899")

    # Application
    max_context_messages: int = int(os.getenv("LITE_MAX_CONTEXT_MESSAGES", "20"))
    supervisor_enabled: bool = os.getenv("LITE_SUPERVISOR_ENABLED", "1") == "1"
    emotion_analysis_enabled: bool = os.getenv("LITE_EMOTION_ANALYSIS_ENABLED", "1") == "1"
    state_persistence_interval: int = int(os.getenv("LITE_STATE_PERSISTENCE_INTERVAL", "60"))

    # WebSocket
    ws_chunk_size: int = int(os.getenv("LITE_WS_CHUNK_SIZE", "80"))

    # Security — shared secret for internal service-to-service calls
    internal_api_secret: str = os.getenv("LITE_INTERNAL_API_SECRET", "").strip()

    # Problem auditor
    audit_batch_size: int = int(os.getenv("LITE_AUDIT_BATCH_SIZE", "50"))
    audit_concurrency: int = int(os.getenv("LITE_AUDIT_CONCURRENCY", "2"))
    audit_problem_id_prefix: str = os.getenv("LITE_AUDIT_PROBLEM_ID_PREFIX", "").strip()


settings = Settings()
