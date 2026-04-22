# ai-agent-lite

Lightweight FastAPI AI agent replacing youtu-agent. Streams LLM responses over WebSocket, compatible with the frontend-vue-ai-chat composable protocol.

## Quick Start (Docker)

```bash
# In project root (uses docker-compose)
docker compose up -d ai-agent-lite

# Health check (host port 8850 -> internal 8848)
curl http://127.0.0.1:8850/healthz
```

## Quick Start (Local)

```bash
pip install -r requirements.txt
LITE_LLM_BASE_URL=https://api.deepseek.com/v1 \
LITE_LLM_API_KEY=your-key \
LITE_LLM_MODEL=deepseek-chat \
uvicorn app.main:app --port 8848
```

## Endpoints

### HTTP
- `GET /healthz` - Liveness check. Returns `{"ok":true,"llm_enabled":bool,"model":"..."}`
- `GET /readyz` - Readiness check (dependency verification). *(planned)*
- `GET /metrics` - Prometheus metrics. *(planned)*

### WebSocket
- `WS /ws?session_id={sessionId}` - Chat endpoint

## WebSocket Protocol

### Client -> Server

```json
{"type": "raw", "content": "user message text", "session_id": "abc123"}
```

### Server -> Client

Init:
```json
{"type": "init", "content": {"default_agent": "ai-agent-lite"}}
```

Stream token:
```json
{"type": "raw", "content": "token text here"}
```

Finish:
```json
{"type": "finish"}
```

Error:
```json
{"type": "error", "content": "error description"}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| LITE_LLM_BASE_URL | No | - | OpenAI-compatible API base URL |
| LITE_LLM_API_KEY | No | - | API key for LLM provider |
| LITE_LLM_MODEL | No | deepseek-chat | Model name to use |
| LITE_LLM_TIMEOUT | No | 30 | Request timeout in seconds |
| OJ_API_URL | No | - | QDUOJ backend URL for OJ integration |

When LITE_LLM_BASE_URL + LITE_LLM_API_KEY are both set, LLM is enabled.
Otherwise the agent runs in mock mode (echo responses).

In docker-compose, these are mapped from .env UTU_LLM_* vars:
- LITE_LLM_BASE_URL=${UTU_LLM_BASE_URL}
- LITE_LLM_API_KEY=${UTU_LLM_API_KEY}
- LITE_LLM_MODEL=${UTU_LLM_MODEL}

## Session Storage

Current: in-memory dict (lost on container restart).
Planned: PostgreSQL-backed persistent storage.

## Port Mapping

| Scope | Port |
|-------|------|
| Internal (container) | 8848 |
| Host (docker-compose) | 8850 |
| Frontend ws proxy target | ws://ai-agent-lite:8848 |

## Architecture

```
frontend-vue-ai-chat
  |
  | WS /ws?session_id=X
  v
ai-agent-lite (FastAPI)
  |
  | HTTP /chat/completions (stream)
  v
LLM Provider (DeepSeek)
```

## Dependencies

- fastapi==0.115.0
- uvicorn==0.30.6
- httpx==0.27.2