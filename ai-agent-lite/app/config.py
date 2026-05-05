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

    # LLM (local Ollama — used by background audit tasks)
    # qwen3.6 is a thinking model; _call_ollama sends think=False to disable reasoning
    ollama_base_url: str = os.getenv("LITE_OLLAMA_BASE_URL", "http://172.17.0.1:11435").strip()
    ollama_model: str = os.getenv("LITE_OLLAMA_MODEL", "qwen3.6:latest").strip()
    ollama_timeout: float = float(os.getenv("LITE_OLLAMA_TIMEOUT", "300"))

    # LLM (Xiaomi MiniMax API — used by problem auditor)
    # Replace Ollama with Xiaomi's mimo-v2-pro for better audit quality and speed.
    xiaomi_api_key: str = os.getenv("LITE_XIAOMI_API_KEY", "").strip()
    xiaomi_api_url: str = os.getenv(
        "LITE_XIAOMI_API_URL",
        "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
    ).strip()
    xiaomi_model: str = os.getenv("LITE_XIAOMI_MODEL", "mimo-v2-pro").strip()
    xiaomi_timeout: float = float(os.getenv("LITE_XIAOMI_TIMEOUT", "180"))

    # Audit rate control: process 3 problems every 5 minutes (300s).
    # Beat fires every 100s; with ~1 problem done in ~60s, 3 in 5 min.
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