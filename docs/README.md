# CDUT OJ - Documentation Center

## Directory Structure

```
docs/
+-- README.md                          # This index
+-- CDUT_OJ_system_status.md           # System status overview
+-- FPS_IMPORT_GUIDE.md                # FPS problem import guide
+-- QDUOJ_DEPLOYED.md                  # Deployment record
+-- QDUOJ_DEPLOYMENT.md                # Deployment detailed doc
+-- QDUOJ_INTEGRATION.md               # Integration doc
+-- guides/
|   +-- problem_admin_guide.md         # OJ admin guide
|   +-- problem_recommendation_guide.md # Teaching guide
+-- reports/
|   +-- fps_import_report.md           # Phase 2: 609 problem import
|   +-- fps_fix_report.md              # Phase 3: tag system
|   +-- judge_test_report.md           # Phase 4: judge verification
|   +-- test_data_report.md            # Phase 5: 24-problem test data
+-- archive/                            # Historical documents
    +-- INTEGRATION_SUCCESS.md
    +-- INTEGRATION_SUMMARY.md
    +-- INTEGRATION_VERIFICATION.md
    +-- INTEGRATED_DEPLOYMENT.md
    +-- QDUOJ_DEPLOYMENT_SUCCESS.md
    +-- milestone_table*.md
```

> Note: Chinese-named files in guides/ and reports/ are being gradually
> renamed to English for consistency. Both old and new names may coexist
> during transition.

---

## Quick Navigation

### New User Path

1. System overview -> CDUT_OJ_system_status.md (10 min)
2. What problems are available -> guides/problem_recommendation_guide.md (15 min)
3. Admin operations -> guides/problem_admin_guide.md (10 min)

### Developer Path

1. Architecture -> ../README.md
2. AI Agent API -> ../ai-agent-lite/README.md
3. Frontend -> ../frontend-vue-ai-chat/README.md
4. Integration -> QDUOJ_INTEGRATION.md

---

## Service Access

| Service          | URL                         |
|------------------|-----------------------------|
| AI Chat Frontend | http://localhost:5173       |
| OJ Backend API   | http://localhost:8000/api    |
| OJ Admin Panel   | http://localhost:8000/admin  |
| AI Agent Health   | http://localhost:8850/healthz |
| Problem List     | http://localhost:8000/problem |

---

## System Status Snapshot

**Last updated**: 2026-04-22

- OK  System running
- OK  Judge service normal
- OK  AI agent (ai-agent-lite) active, LLM connected
- OK  ai-agent-lite persistence enabled (PostgreSQL schema: ai_agent)
- OK  ai-agent-lite readiness and metrics endpoints enabled
- OK  609 problems imported, 24 with test data
- OK  Frontend (vue-ai-chat) serving on port 5173
- INFO  ai-agent-lite is the sole AI agent service

---

## Project Phases

### Phase 1: Foundation (completed)
- System deployment
- 609-problem FPS import
- Tag classification (19 tags)
- Judge verification
- 24-problem test data
- AI chat with WebSocket protocol

### Phase 2: Stability (completed)
- Persistent session storage (PostgreSQL, ai_agent schema)
- User identity binding support (`user_id` from ws query)
- Error handling hardening (unified error payload + retries/fallback)
- Observability (healthz, readyz, metrics, basic middleware)

### Phase 3: Intelligence (planned)
- Problem-context prompt engineering
- Code review structure
- Judge result auto-analysis
- Learning progress tracking

---

## For System Administrators

1. Deployment & Maintenance
   - QDUOJ_DEPLOYMENT.md
   - CDUT_OJ_system_status.md

2. Problem Management
   - FPS_IMPORT_GUIDE.md
   - guides/problem_admin_guide.md

## For Teachers

1. Teaching Usage
   - guides/problem_recommendation_guide.md
   - reports/test_data_report.md

2. Problem Management
   - guides/problem_admin_guide.md

## For Developers

1. Technical
   - FPS_IMPORT_GUIDE.md
   - QDUOJ_INTEGRATION.md

2. Testing
   - reports/judge_test_report.md

---

Maintained by CDUT Student Agents Team