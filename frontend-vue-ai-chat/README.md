# frontend-vue-ai-chat

Vue 3 + Vite frontend for the CDUT AI tutor system. Provides chat interface with OJ problem browsing and code submission.

## Features

- WebSocket chat with streaming AI responses (raw/finish/error protocol)
- WebSocket identity/session binding (`session_id` + `user_id` query params)
- Server session UUID sync from `init` event to frontend local metadata
- OJ problem browsing and selection with auto-session creation
- Problem pagination with 21 items per page and numeric page buttons
- Code editor with multi-language support (C++, Python, Java, C)
- Direct OJ submission from chat interface
- Problem detail display (description, samples, constraints)
- Per-session OJ submit drafts (language + code + state preserved across session switches)
- Staged attachment flow: "发给AI" button stages code and submission results as attachment chips above chat input; user reviews and clicks 发送 to deliver

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

## Staged Attachment Flow

The "发给AI" button in the OJ submission panel does **not** send immediately. Instead:

1. Clicking "发给AI" builds one or more attachment objects and adds them to `pendingAttachments`.
2. Attachments appear as removable chips above the chat input textarea.
3. The 发送 button becomes active when there are pending attachments (with or without text).
4. On send, attachments are encoded into the user message as `[Attachment] filename` headers with fenced code blocks, then cleared.
5. If a previous submission result (success/error) exists, it is also staged as an attachment alongside the code.

Attachment object shape:
```js
{ filename: string, content: string, type: 'code' | 'result' }
```

This flow gives users a chance to review before sending and allows combining code + result in a single message.

## OJ Integration

- Auth: Cookie-based login via /oj-api proxy
- Problems: Fetch list + detail from QDUOJ backend API (offset + limit pagination)
- Submit: POST to /oj-api/submission with problem_id, language, code
- Result: Poll submission status via /oj-api/submission

## Environment Variables

None at build time. All service routing is via Vite dev server proxy (see vite.config.js).

## Port

- Dev server: 5173 (container and host)