# ai-agent-lite

Lightweight FastAPI AI agent powering the CDUT Student Training System. Features a Supervisor pattern with specialized worker agents for programming competition training. Streams LLM responses over WebSocket, compatible with the frontend-vue-ai-chat composable protocol.

## Architecture Overview

The system now uses a **Supervisor Pattern** with specialized worker agents:

```
┌─────────────────────────────────────────────────────────────┐
│                     Supervisor Pattern                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Input → Supervisor → Intelligent Routing → Worker     │
│                                                             │
│  ┌──────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │          │    │                 │    │                │  │
│  │  Input   │───►│   Supervisor    │───►│   CodeReviewer │  │
│  │          │    │                 │    │                │  │
│  └──────────┘    └─────────────────┘    └────────────────┘  │
│                                 │          ┌────────────────┐
│                                 │          │ProblemAnalyzer │
│                                 │          └────────────────┘
│                                 │          ┌────────────────┐
│                                 └─────────►│ ContestCoach   │
│                                            └────────────────┘
│                                            ┌────────────────┐
│                                            │LearningPartner │
│                                            └────────────────┘
│                                            ┌────────────────┐
│                                            │LearningManager │
│                                            └────────────────┘
└─────────────────────────────────────────────────────────────┘
```

## Worker Agents

1. **Code Reviewer** - Code quality, efficiency, and style evaluation
2. **Problem Analyzer** - Algorithm explanation and problem breakdown
3. **Contest Coach** - Competition strategy and performance optimization
4. **Learning Partner** - Emotional support and motivational guidance
5. **Learning Manager** - Personalized learning path recommendations
6. **Next Step Suggester** - Generates contextual next-step suggestions at the end of each conversation turn (not a content-producing worker; only runs after the primary worker finishes)

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
{"type":"init","data":{"type":"init","default_agent":"ai-agent-lite","agent_type":"supervisor","sub_agents":["code_reviewer","problem_analyzer","contest_coach","learning_partner","learning_manager"],"session_id":"<uuid>"}}
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
ai-agent-lite (FastAPI + Supervisor Pattern)
  ├── Supervisor (Intelligent routing + state management)
  ├── Code Reviewer (代码审查和优化建议)
  ├── Problem Analyzer (算法问题解析)
  ├── Contest Coach (竞赛策略指导)
  ├── Learning Partner (学习伙伴和情感支持)
  └── Learning Manager (个性化学习管理)
  |
  | HTTP /chat/completions
  v
LLM Provider (DeepSeek)
```

## Configuration

The supervisor pattern can be configured via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SUPERVISOR_ENABLED | No | true | Enable supervisor pattern routing |
| MAX_CONTEXT_MESSAGES | No | 20 | Number of historical messages for context |
| STATE_PERSISTENCE_INTERVAL | No | 60 | State persistence interval in seconds |
| EMOTION_ANALYSIS_ENABLED | No | true | Enable emotion-aware routing |

## Dependencies

- fastapi==0.115.0
- uvicorn==0.30.6
- httpx==0.27.2