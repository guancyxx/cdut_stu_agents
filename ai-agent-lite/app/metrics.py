"""
Prometheus metrics for ai-agent-lite.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# WebSocket metrics
ws_connections_active = Gauge(
    "ws_connections_active", "Currently active WebSocket connections"
)
ws_messages_total = Counter(
    "ws_messages_total", "Total WS messages", ["direction", "msg_type"]
)

# LLM metrics
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds", "LLM request duration in seconds",
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)
llm_errors_total = Counter(
    "llm_errors_total", "Total LLM errors", ["code"]
)

# DB metrics
db_operations_total = Counter(
    "db_operations_total", "Total DB operations", ["operation", "table"]
)

# Submission fallback / DLQ metrics
submission_fallback_events_total = Counter(
    "submission_fallback_events_total",
    "Total submission fallback ingest events",
    ["outcome", "status_label", "source"],
)
submission_dlq_replay_runs_total = Counter(
    "submission_dlq_replay_runs_total",
    "Total submission DLQ replay runs",
    ["outcome"],
)
submission_dlq_replay_rows_total = Counter(
    "submission_dlq_replay_rows_total",
    "Total submission DLQ rows processed",
    ["outcome"],
)
submission_dlq_replay_duration_seconds = Histogram(
    "submission_dlq_replay_duration_seconds",
    "Submission DLQ replay duration in seconds",
    buckets=[0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30],
)
submission_dlq_pending_rows = Gauge(
    "submission_dlq_pending_rows",
    "Current pending submission DLQ rows",
)


def metrics_text() -> str:
    """Return Prometheus-format metrics text."""
    return generate_latest().decode("utf-8")