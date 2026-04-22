# frontend-vue-ai-chat

Vue 3 + Vite frontend for the CDUT AI tutor system. Provides chat interface with OJ problem browsing and code submission.

## Features

- WebSocket chat with streaming AI responses (raw/finish/error protocol)
- OJ problem browsing and selection with auto-session creation
- Code editor with multi-language support (C++, Python, Java, C)
- Direct OJ submission from chat interface
- Problem detail display (description, samples, constraints)
- Per-session OJ submit drafts (language + code + state preserved across session switches)

## Architecture

```
Browser
  |
  +-- /ws     -> ws://ai-agent-lite:8848  (Vite proxy)
  +-- /oj-api -> http://oj-backend:8000    (Vite proxy, path rewrite)
```

## Quick Start (Docker)

```bash
# In project root
docker compose up -d vue-ai-chat
# Access: http://localhost:5173
```

## Quick Start (Local Dev)

```bash
npm install
npm run dev
# Access: http://localhost:5173
# Requires ai-agent-lite running on port 8848 (or configured proxy target)
```

## Key Composables

| Composable | Purpose |
|------------|---------|
| useChatSocket | WebSocket connection, message send/receive, reconnect |
| useChatFeature | Chat logic: send message, handle streaming response |
| useSessions | Session list CRUD, current session tracking |
| useOjAuthAndProblems | OJ login, problem fetch, problem detail |

## OJ Integration

- Auth: Cookie-based login via /oj-api proxy
- Problems: Fetch list + detail from QDUOJ backend API
- Submit: POST to /oj-api/submission with problem_id, language, code
- Result: Poll submission status via /oj-api/submission

## Environment Variables

None at build time. All service routing is via Vite dev server proxy (see vite.config.js).

## Port

- Dev server: 5173 (container and host)