# CDUT OJ - Documentation Center

## Directory Structure

```
docs/
+-- README.md                 # This index
+-- PROJECT_SPEC.md           # Full project specification (from official PDF)
+-- CDUT_OJ_system_status.md  # System status overview
+-- AI_AGENT_PROMPT_CHAIN.md  # AI Agent prompt chain & routing logic
+-- guides/
|   +-- problem_recommendation_guide.md  # Teaching problem guide
|   +-- problem_admin_guide.md           # OJ admin guide
+-- plans/
    +-- ai-agent-lite-v1-tasks.md        # V1 dev task list (completed)
```

---

## Quick Navigation

### Project Overview

1. Full project specification -> PROJECT_SPEC.md (background, research goals, innovation, outcomes)
2. System architecture -> ../README.md
3. AI Agent details -> ../ai-agent-lite/README.md
4. Frontend details -> ../frontend-vue-ai-chat/README.md

### New User Path

1. System overview -> CDUT_OJ_system_status.md (10 min)
2. What problems are available -> guides/problem_recommendation_guide.md (15 min)
3. Admin operations -> guides/problem_admin_guide.md (10 min)

### Developer Path

1. Architecture -> ../README.md
2. AI Agent API -> ../ai-agent-lite/README.md
3. Frontend -> ../frontend-vue-ai-chat/README.md
4. AI prompt chain -> AI_AGENT_PROMPT_CHAIN.md
5. Feature spec -> ../specs/001-ai-tutor/spec.md

---

## Service Access

| Service | URL |
|------------------|-----------------------------|
| AI Chat Frontend | http://localhost:5173 |
| OJ Backend API | http://localhost:8000/api |
| OJ Admin Panel | http://localhost:8000/admin |
| AI Agent Health | http://localhost:8850/healthz |

---

## System Status Snapshot

**Last updated**: 2026-04-26

- OK System running
- OK Judge service normal
- OK AI agent (ai-agent-lite) active, LLM connected
- OK ai-agent-lite persistence enabled (PostgreSQL schema: ai_agent)
- OK ai-agent-lite readiness and metrics endpoints enabled
- OK Supervisor pattern with 5 Worker Agents operational
- OK 2683 problems in database (backed up)
- OK Frontend (vue-ai-chat) serving on port 5173
- INFO ai-agent-lite is the sole AI agent service
- INFO Project spec documented in PROJECT_SPEC.md

---

## Project Phases

### Phase 1: Foundation (completed)
- System deployment
- Problem bank imported (2683 problems, backed up at backups/)
- Tag classification (19 tags)
- Judge verification
- AI chat with WebSocket protocol
- Supervisor + 5 Worker Agents

### Phase 2: Stability (completed)
- Persistent session storage (PostgreSQL, ai_agent schema)
- User identity binding support (user_id from ws query)
- Error handling hardening (unified error payload + retries/fallback)
- Observability (healthz, readyz, metrics, basic middleware)
- Chinese-only language policy enforced
- NextStepSuggester removed (3x LLM calls -> 2x)

### Phase 3: Intelligence (in progress)
- Problem-context prompt engineering
- Code review structure (response_formatter.py)
- Judge result auto-analysis
- Learning progress tracking
- Scope guard (tutor_policy.py)
- Boundary router (boundary_router.py)
- LLM streaming in workers (2x -> 1x calls)

### Phase 4: Knowledge & Intelligence (planned — from Project Spec)
- Contest knowledge graph construction (3000+ problems)
- Learning path intelligent planning
- Programming thinking visualization
- Emotional intelligence interaction
- Contest simulation mode

### Phase 5: Scale & Evaluation (planned — from Project Spec)
- Rate limiting per user/IP
- Load testing (50+ concurrent)
- A/B testing for algorithm effectiveness
- Student performance evaluation
- Regional promotion feasibility

---

## For System Administrators

1. Deployment & Maintenance
   - CDUT_OJ_system_status.md

2. Problem Management
   - guides/problem_admin_guide.md

## For Teachers

1. Teaching Usage
   - guides/problem_recommendation_guide.md

## For Developers

1. Technical
   - PROJECT_SPEC.md (project scope and research goals)
   - AI_AGENT_PROMPT_CHAIN.md

2. AI Agent
   - ../ai-agent-lite/README.md
   - ../specs/001-ai-tutor/spec.md

---

Maintained by CDUT Student Agents Team