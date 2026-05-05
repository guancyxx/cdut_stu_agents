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

    # LLM (cloud API — used by chat agents)
    llm_base_url: str = os.getenv("LITE_LLM_BASE_URL", "").strip()
    llm_api_key: str = os.getenv("LITE_LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LITE_LLM_MODEL", "deepseek-chat").strip()
    llm_timeout: float = float(os.getenv("LITE_LLM_TIMEOUT", "30"))
    llm_max_retries: int = 2
    llm_retry_delay: float = 2.0

    # ------------------------------------------------------------------
    # Background-audit LLM — provider-agnostic.
    #
    # Switch provider by setting LITE_AUDIT_LLM_PROVIDER:
    #   "xiaomi"  → xiaomimimo.com (cloud, OpenAI-compatible, thinking model)
    #   "ollama"  → local GPU (GPU required, qwen3.6 with think=False)
    #
    # All provider-specific details (base_url, model, timeout) share the
    # LITE_AUDIT_LLM_ prefix.  The caller reads *one* config surface
    # regardless of which provider is active.
    # ------------------------------------------------------------------
    audit_llm_provider: str = os.getenv("LITE_AUDIT_LLM_PROVIDER", "xiaomi").strip()
    audit_llm_api_key: str = os.getenv("LITE_AUDIT_LLM_API_KEY", "").strip()
    audit_llm_base_url: str = os.getenv(
        "LITE_AUDIT_LLM_BASE_URL",
        "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
    ).strip()
    audit_llm_model: str = os.getenv("LITE_AUDIT_LLM_MODEL", "mimo-v2-pro").strip()
    audit_llm_timeout: float = float(os.getenv("LITE_AUDIT_LLM_TIMEOUT", "180"))

    # Audit rate control: 3 problems / 5 min (~100 s between ticks).
    audit_beat_interval: int = int(os.getenv("LITE_AUDIT_BEAT_INTERVAL", "100"))

    # OJ Admin API (used by problem auditor to fetch/patch problems)
    oj_api_url: str = os.getenv("OJ_API_URL", "http://oj-backend:8000").strip()
    oj_admin_user: str = os.getenv("OJ_ADMIN_USER", "root")
    oj_admin_pass: str = os.getenv("OJ_ADMIN_PASS", "rootroot")

    # Celery / Redis
    celery_broker_url: str = os.getenv("LITE_CELERY_BROKER", "redis://oj-redis:6379/1")
    celery_result_backend: str = os.getenv("LITE_CELERY_BACKEND", "redis://oj-redis:6379/2")

    # Application
    max_context_messages: int = int(os.getenv("LITE_MAX_CONTEXT_MESSAGES", "20"))
    supervisor_enabled: bool = os.getenv("LITE_SUPERVISOR_ENABLED", "1") == "1"
    emotion_analysis_enabled: bool = os.getenv("LITE_EMOTION_ANALYSIS_ENABLED", "1") == "1"
    state_persistence_interval: int = int(os.getenv("LITE_STATE_PERSISTENCE_INTERVAL", "60"))

    # WebSocket
    ws_chunk_size: int = int(os.getenv("LITE_WS_CHUNK_SIZE", "80"))

    # Problem auditor
    audit_batch_size: int = int(os.getenv("LITE_AUDIT_BATCH_SIZE", "50"))
    audit_concurrency: int = int(os.getenv("LITE_AUDIT_CONCURRENCY", "2"))


settings = Settings()
