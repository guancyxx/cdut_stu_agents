# QDUOJ Integration

**Updated**: 2026-04-22

## Current Architecture

```
frontend-vue-ai-chat (Vue 3, port 5173)
  |
  +-- /ws proxy ---> ws://ai-agent-lite:8848   (AI chat)
  +-- /oj-api proxy -> http://oj-backend:8000   (OJ REST API)
  |
  v
ai-agent-lite (FastAPI, port 8848 internal / 8850 host)
  |
  | HTTP (streaming)
  v
DeepSeek LLM API

QDUOJ Backend (Django, port 8000)
  |
  +-- QDUOJ Judge Server (port 8080 internal)
  +-- PostgreSQL (port 5432 internal)
  +-- Redis (port 6379 internal)
```

Legacy: youtu-agent (port 8848) runs in docker-compose but frontend no longer routes to it.

## Integration Points

### 1. OJ API (Backend -> Frontend)

The Vue frontend proxies `/oj-api/*` to `http://oj-backend:8000/*`.

Key endpoints used:
- `POST /api/login` - User authentication
- `GET /api/problem` - Problem list
- `GET /api/problem/{id}` - Problem detail
- `POST /api/submission` - Code submission
- `GET /api/submission/{id}` - Submission status

### 2. AI Chat (Frontend -> ai-agent-lite)

WebSocket connection via `/ws`.

Request/response contract:
- Send: `{type:"query", content:{query:"..."}}`
- Receive init: `{type:"init", data:{..., session_id:"<uuid>"}}`
- Receive stream: `{type:"raw", data:{type:"text", delta:"...", inprogress:true|false}}`
- End: `{type:"finish"}`
- Error: `{type:"error", data:{type:"error", code:"...", message:"..."}}`

Connection query params:
- `session_id` optional
- `user_id` optional (recommended; defaults to `anonymous`)

### 3. AI Agent -> OJ API (Planned)

ai-agent-lite can call OJ backend API to:
- Fetch problem details for context injection
- Check submission status
- Provide WA/RE/TLE analysis

Currently not implemented. Planned for Phase 3.

## Data Flow: Student Workflow

1. Student opens http://localhost:5173
2. Logs in to OJ via frontend (credentials sent to /oj-api/login)
3. Browses problem list (fetched from QDUOJ)
4. Selects a problem -> auto-creates AI chat session
5. Asks AI for hints while viewing problem details
6. Writes code in editor, submits to OJ via /oj-api
7. Views judge result (AC/WA/RE/TLE)
8. Asks AI to explain judge result (if not AC)

## Configuration

### Vite Proxy (frontend-vue-ai-chat/vite.config.js)

```js
proxy: {
  '/ws': { target: 'ws://ai-agent-lite:8848', ws: true },
  '/oj-api': { target: 'http://oj-backend:8000', changeOrigin: true,
               rewrite: (path) => path.replace(/^\/oj-api/, '') },
}
```

### Environment Variables (.env)

```
UTU_LLM_BASE_URL=https://api.deepseek.com/v1
UTU_LLM_API_KEY=sk-...
UTU_LLM_MODEL=deepseek-chat
```

Mapped in docker-compose:
- LITE_LLM_BASE_URL=${UTU_LLM_BASE_URL}
- LITE_LLM_API_KEY=${UTU_...KEY}
- LITE_LLM_MODEL=${UTU_LLM_MODEL}
- LITE_DATABASE_URL=postgresql+asyncpg://onlinejudge:${POSTGRES_PASSWORD:-onlinejudge}@oj-postgres:5432/onlinejudge
- LITE_DB_SCHEMA=ai_agent

## Planned Enhancements

- ai-agent-lite directly fetches problem context from OJ API
- AI auto-analyzes WA/RE/TLE results
- Structured code review output (issue type, severity, suggestion)
- Learning progress tracking with knowledge point tagging