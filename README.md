# AI + Programming Contest Training System

AI-powered programming contest training platform built on a lightweight FastAPI agent and QDUOJ Online Judge.

> Project specification (Chinese): [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md)

## Project Identity

- **Project Name**: AI + Programming Contest Training System
- **Domain**: Artificial Intelligence, Education Technology, Software Engineering
- **Type**: Applied Research & Platform Development
- **Duration**: 12 months (from 2025-04-24)
- **Full Spec**: See [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md) for background, research goals, innovation points, and expected outcomes

## System Architecture

```
+--------------------------------------------------------------+
| Browser (Student)                                            |
+------------------+-------------------------+------------------+
                  |                         |
                  v                         v
+------------------+              +---------------------------+
| frontend-vue    | /ws          | ai-agent-lite             |
| -ai-chat +------>------------>| (FastAPI + DeepSeek)       |
| Vue 3 + Vite    |<------------+| Supervisor + 5 Worker     |
| Port: 5173      | stream       | Agents                    |
+--+--------------+              | Port: 8848 (internal)     |
   |                             | Port: 8850 (host)         |
   | /oj-api                     +--+------------------------+
   | HTTP                           |
   v                                v
+--------------------+        +-------------+
| QDUOJ Backend      |<-------+ OJ Judge    |
| Port: 8000         |        | Server      |
+---------+----------+        +-------------+
          |
    +-----+------+
    |            |
+---+----+ +----+---+
| Postgres| | Redis  |
+---------+ +--------+
```

## Multi-Agent Architecture

The system implements 5 specialized AI agents aligned with the project specification:

| Agent | Chinese Name | Spec Role | Description |
|-------|-------------|-----------|-------------|
| CodeReviewer | Code Review Agent | Code Review Agent | Code quality, efficiency, and style assessment |
| ProblemAnalyzer | Problem Analysis Agent | Problem Analysis Agent | Algorithm explanation and problem decomposition |
| ContestCoach | Contest Coach Agent | Contest Coach Agent | Contest strategy and performance optimization |
| LearningPartner | Learning Partner Agent | Learning Partner Agent | Emotional support and learning motivation |
| LearningManager | Learning Management Agent | Learning Management Agent | Personalized learning path planning |

> The Supervisor pattern routes student queries to the most appropriate Worker Agent based on intent classification and emotional state analysis.

## Services

| Service | Container | Host Port | Internal Port | Status |
|----------------------|----------------------|-----------|---------------|---------|
| frontend-vue-ai-chat | cdut-vue-ai-chat | 5173 | 5173 | Active |
| ai-agent-lite | cdut-ai-agent-lite | 8850 | 8848 | Active |
| QDUOJ Backend | cdut-oj-backend | 8000 | 8000 | Active |
| QDUOJ Judge Server | cdut-oj-judge | - | 8080 | Active |
| PostgreSQL | cdut-oj-postgres | - | 5432 | Active |
| Redis | cdut-oj-redis | - | 6379 | Active |

## Project Structure

```
cdut_stu_agents/
+-- ai-agent-lite/          # Lightweight FastAPI AI agent (active)
|   +-- app/main.py         # Core: /ws endpoint + /healthz + session + LLM
|   +-- app/supervisor.py   # Supervisor: intent classification + routing
|   +-- app/workers.py      # 5 specialized Worker Agents
|   +-- app/llm_client.py   # LLM client with retry/fallback/stream
|   +-- app/state_manager.py# Student state persistence
|   +-- app/database.py     # DB connection pool + schema init
|   +-- app/models.py       # ORM: Session/Message/AuditLog
|   +-- Dockerfile
|   +-- requirements.txt
|   +-- README.md
+-- frontend-vue-ai-chat/   # Vue 3 frontend (active)
|   +-- src/
|   |   +-- App.vue         # Main layout: chat + problem panel + OJ submit
|   |   +-- composables/    # useChatSocket, useChatFeature, useSessions, ...
|   |   +-- services/       # apiClient, OJ auth
|   |   +-- components/     # CodeEditor, ...
|   +-- vite.config.js      # /ws -> ai-agent-lite, /oj-api -> oj-backend
|   +-- Dockerfile
+-- qduoj/                  # QDUOJ deployment config & persistent data
+-- fps-problems/           # FPS problem set (609 problems)
+-- custom_agents/          # Custom agent configs
+-- scripts/                # Utility scripts (test case import, etc.)
+-- specs/                  # Feature specifications
|   +-- 001-ai-tutor/spec.md # AI tutor feature spec
+-- docs/                   # Documentation center
|   +-- PROJECT_SPEC.md     # Full project specification (from PDF)
|   +-- README.md           # Doc index
|   +-- guides/             # Usage guides
|   +-- reports/            # Phase completion reports
|   +-- archive/            # Historical documents
+-- docker-compose.yml      # Unified service orchestration
+-- .env                    # Environment variables
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

| Service | URL |
|----------------|---------------------------|
| AI Chat | http://localhost:5173 |
| OJ Backend API | http://localhost:8000/api |
| OJ Admin | http://localhost:8000/admin |
| AI Agent Health| http://localhost:8850/healthz |

Default admin: `root` / `rootroot` (change on first login)

## Tech Stack

### AI Agent
- Backend: FastAPI + uvicorn (Python 3.11)
- Architecture: Supervisor pattern with 5 specialized Worker Agents
- LLM: DeepSeek-V3 (via OpenAI-compatible API)
- Protocol: WebSocket (raw/finish/error/agent_info messages)
- Persistence: PostgreSQL (ai_agent schema)

### Frontend
- Framework: Vue 3 + Vite
- WebSocket client: native WebSocket in composables
- OJ integration: REST API proxy via Vite dev server
- Staged attachment flow: code + result review before sending

### Online Judge
- System: QDUOJ (Qingdao University OJ) v1.6.1
- Backend: Django + DRF
- Judge: Docker-isolated container
- Database: PostgreSQL 10
- Cache: Redis 4

### Infrastructure
- All services: Docker Compose on bridge network
- Data persistence: host-mounted volumes under ./qduoj/data and ./data
- Observability: /healthz, /readyz, /metrics (Prometheus)

## Research Goals (from Project Spec)

1. Build a complete AI-assisted contest training system
2. Construct a knowledge graph and problem bank with 3000+ problems
3. Achieve 85%+ accuracy in code analysis and feedback
4. Improve student problem-solving efficiency by 30%+, contest scores by 20%+
5. Develop a replicable AI-assisted programming education model
6. Implement 5+ specialized AI Agents for different training needs

> Full research content, technical roadmap, and innovation points: [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md)

## Development Roadmap

### Phase 1: Foundation (completed)
- [x] Docker environment + QDUOJ deployment
- [x] FPS problem import (609 problems, 24 with test data)
- [x] AI chat WebSocket protocol (raw/finish/error/agent_info)
- [x] Vue 3 frontend with chat + problem panel + OJ submit
- [x] ai-agent-lite service with Supervisor + 5 Worker Agents

### Phase 2: Stability (completed)
- [x] Persistent session and message storage (PostgreSQL)
- [x] User identity binding from OJ auth
- [x] Unified error codes, timeout, retry logic
- [x] /readyz + Prometheus metrics endpoint
- [x] Remove hardcoded next-step suggestions (reduces 3x LLM calls to 2x)
- [x] Chinese-only language policy enforced across all user-facing prompts

### Phase 3: Intelligence (in progress)
- [ ] **[P0]** Reduce per-request LLM calls from 2x to 1x (merge intent + response)
- [ ] **[P0]** Enable LLM streaming in workers.py (llm_client supports it but unused)
- [ ] **[P1]** Fix Supervisor re-instantiation per WS connection (state overhead)
- [ ] **[P1]** Add race-condition guards in state_manager.py (active_states dict)
- [ ] **[P1]** Problem-context prompt template (inject OJ problem into system prompt)
- [ ] **[P1]** Scope guard (tutor_policy.py) — reject non-programming queries
- [ ] **[P1]** Boundary router (boundary_router.py) — fine-grained routing
- [ ] **[P2]** Structured code review output (response_formatter.py)
- [ ] **[P2]** Auto-analysis of WA/RE/TLE judge results
- [ ] **[P2]** Learning record + knowledge point tagging
- [ ] **[P2]** Online retrieval (web_retrieval.py)
- [ ] **[P2]** Frontend: use agent_info events instead of regex fallback in useChatSocket

### Phase 4: Knowledge & Intelligence (planned — aligned with Project Spec)
- [ ] Contest knowledge graph construction (3000+ problems target)
- [ ] Learning path intelligent planning (personalized recommendation)
- [ ] Programming thinking visualization (algorithm to visual expression)
- [ ] Emotional intelligence interaction (sentiment model beyond keywords)
- [ ] Contest simulation mode (real environment + pressure training)

### Phase 5: Scale & Evaluation
- [ ] Rate limiting per user/IP
- [ ] Load testing (50+ concurrent)
- [ ] A/B testing for algorithm effectiveness
- [ ] Student performance tracking and evaluation (30% efficiency, 20% score improvement)
- [ ] Regional promotion and commercialization feasibility study

## License

MIT
