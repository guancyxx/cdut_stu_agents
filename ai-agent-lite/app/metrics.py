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


def metrics_text() -> str:
    """Return Prometheus-format metrics text."""
    return generate_latest().decode("utf-8")