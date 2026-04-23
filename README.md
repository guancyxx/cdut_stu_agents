# CDUT Student Contest Training System

AI-powered programming contest training platform built on a lightweight FastAPI agent and QDUOJ Online Judge.

## System Architecture

```
+--------------------------------------------------------------+
|                  Browser (Student)                            |
+------------------+-------------------------+------------------+
                   |                         |
                   v                         v
+------------------+            +---------------------------+
|  frontend-vue   |   /ws      |  ai-agent-lite            |
|  -ai-chat        +---------->|  (FastAPI + DeepSeek)     |
|  Vue 3 + Vite    |<----------+  Port: 8848 (internal)   |
|  Port: 5173     |  stream    |  Port: 8850 (host)       |
+--+--------------+            +--+------------------------+
   |                               |
   | /oj-api                       | HTTP
   v                               v
+--------------------+        +-------------+
|  QDUOJ Backend     |<-------+  OJ Judge  |
|  Port: 8000        |        |  Server     |
+---------+----------+        +-------------+
          |
    +-----+------+
    |            |
+---+----+ +----+---+
| Postgres| | Redis  |
+---------+ +--------+
```

## Services

| Service              | Container            | Host Port | Internal Port | Status  |
|----------------------|----------------------|-----------|---------------|---------|
| frontend-vue-ai-chat | cdut-vue-ai-chat     | 5173      | 5173          | Active  |
| ai-agent-lite        | cdut-ai-agent-lite   | 8850      | 8848          | Active  |
| QDUOJ Backend        | cdut-oj-backend      | 8000      | 8000          | Active  |
| QDUOJ Judge Server   | cdut-oj-judge        | -         | 8080          | Active  |
| PostgreSQL           | cdut-oj-postgres     | -         | 5432          | Active  |
| Redis                | cdut-oj-redis        | -         | 6379          | Active  |

## Project Structure

```
cdut_stu_agents/
+-- ai-agent-lite/              # Lightweight FastAPI AI agent (active)
|   +-- app/main.py             # Core: /ws endpoint + /healthz + session + LLM
|   +-- Dockerfile
|   +-- requirements.txt
|   +-- README.md
+-- frontend-vue-ai-chat/       # Vue 3 frontend (active)
|   +-- src/
|   |   +-- App.vue             # Main layout: chat + problem panel + OJ submit
|   |   +-- composables/        # useChatSocket, useChatFeature, useSessions, ...
|   |   +-- services/           # apiClient, OJ auth
|   |   +-- components/         # CodeEditor, ...
|   +-- vite.config.js          # /ws -> ai-agent-lite, /oj-api -> oj-backend
|   +-- Dockerfile
+-- qduoj/                      # QDUOJ deployment config & persistent data
+-- fps-problems/               # FPS problem set (609 problems)
+-- custom_agents/              # Custom agent configs
+-- scripts/                    # Utility scripts (test case import, etc.)
+-- specs/                      # Feature specifications
|   +-- 001-ai-tutor/spec.md    # AI tutor feature spec
+-- docs/                       # Documentation center
|   +-- README.md               # Doc index
|   +-- guides/                 # Usage guides
|   +-- reports/                # Phase completion reports
|   +-- archive/                # Historical documents
+-- docker-compose.yml          # Unified service orchestration
+-- .env                        # Environment variables
```

## Quick Start

### Prerequisites

- Docker + Docker Compose (Linux)
- DeepSeek API Key (configured in .env)
- 8GB+ RAM, 20GB+ disk

### Deploy All Services

```bash
# Start everything
docker compose up -d

# Verify
docker compose ps
curl http://127.0.0.1:8850/healthz
curl http://127.0.0.1:8000/api/health_check
```

### Access

| Service        | URL                       |
|----------------|---------------------------|
| AI Chat        | http://localhost:5173     |
| OJ Backend API | http://localhost:8000/api |
| OJ Admin       | http://localhost:8000/admin |
| AI Agent Health| http://localhost:8850/healthz |

Default admin: `root` / `rootroot` (change on first login)

## Tech Stack

### AI Agent
- Backend: FastAPI + uvicorn (Python 3.11)
- LLM: DeepSeek-V3 (via OpenAI-compatible API)
- Protocol: WebSocket (raw/finish/error messages)
- Persistence: PostgreSQL (ai_agent schema)

### Frontend
- Framework: Vue 3 + Vite
- WebSocket client: native WebSocket in composables
- OJ integration: REST API proxy via Vite dev server

### Online Judge
- System: QDUOJ (Qingdao University OJ) v1.6.1
- Backend: Django + DRF
- Judge: Docker-isolated container
- Database: PostgreSQL 10
- Cache: Redis 4

### Infrastructure
- All services: Docker Compose on bridge network
- Data persistence: host-mounted volumes under ./qduoj/data and ./data

## Development

### Rebuild a single service

```bash
docker compose up -d --build ai-agent-lite
docker compose up -d --build vue-ai-chat
```

### View logs

```bash
docker compose logs -f ai-agent-lite
docker compose logs -f vue-ai-chat
```

### Shell into a container

```bash
docker compose exec ai-agent-lite sh
docker compose exec oj-backend bash
```

## Development Roadmap

### Phase 1: Foundation (completed)
- [x] Docker environment + QDUOJ deployment
- [x] FPS problem import (609 problems, 24 with test data)
- [x] AI chat WebSocket protocol (raw/finish/error)
- [x] Vue 3 frontend with chat + problem panel + OJ submit
- [x] ai-agent-lite service operational

### Phase 2: Stability (in progress)
- [ ] Persistent session and message storage (Postgres)
- [ ] User identity binding from OJ auth
- [ ] Unified error codes, timeout, retry logic
- [ ] /readyz + Prometheus metrics endpoint
- [ ] Context compression for long conversations

### Phase 3: Intelligence
- [ ] Problem-context prompt template
- [ ] Structured code review output (issue type, severity, fix)
- [ ] Auto-analysis of WA/RE/TLE judge results
- [ ] Learning record + knowledge point tagging

### Phase 4: Scale
- [ ] Rate limiting per user/IP
- [ ] Load testing (50+ concurrent)
- [ ] Personalized learning path recommendation
- [ ] Contest simulation mode

## License

MIT