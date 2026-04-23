# ai-agent-lite

Lightweight FastAPI AI agent powering the CDUT Student Training System. Streams LLM responses over WebSocket, compatible with the frontend-vue-ai-chat composable protocol.

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
LITE_LLM_API_KEY=*** \
LITE_LLM_MODEL=deepseek-chat \
uvicorn app.main:app --port 8848
```

## Endpoints

### HTTP
- `GET /healthz` - Liveness check. Returns `{"ok":true,"llm_enabled":bool,"model":"..."}`
- `GET /readyz` - Readiness check (DB + LLM dependency verification)
- `GET /metrics` - Prometheus metrics endpoint

### WebSocket
- `WS /ws?session_id={sessionId}&user_id={userId}` - Chat endpoint
  - `session_id` is optional. When invalid/missing, server creates a new UUID session.
  - `user_id` is optional. Defaults to `anonymous`.

## WebSocket Protocol

### Client -> Server

```json
{"type": "query", "content": {"query": "user message text"}}
```

Optional:
```json
{"type": "list_agents"}
```

### Server -> Client

Init:
```json
{"type":"init","data":{"type":"init","default_agent":"ai-agent-lite","agent_type":"simple","sub_agents":null,"session_id":"<uuid>"}}
```

Stream token:
```json
{"type":"raw","data":{"type":"text","delta":"token text here","inprogress":true}}
```

Finish:
```json
{"type":"finish"}
```

Error:
```json
{"type":"error","data":{"type":"error","code":"INVALID_INPUT","message":"error description"}}
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
- LITE_LLM_API_KEY=${UTU_...KEY}
- LITE_LLM_MODEL=${UTU_LLM_MODEL}

## Session Storage

Current: PostgreSQL-backed persistent storage in `ai_agent` schema.

Tables:
- `ai_agent.sessions`
- `ai_agent.messages`
- `ai_agent.audit_log`

`LITE_DATABASE_URL` defaults to the shared QDUOJ postgres container (`oj-postgres`) with logical isolation by schema.

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