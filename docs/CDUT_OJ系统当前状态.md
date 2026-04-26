# CDUT OJ System - Current Status

**Updated**: 2026-04-26
**OJ Version**: QDUOJ v1.6.1
**System Status**: Running

---

## System Overview

### Core Info
- Deployment: Docker containers on Linux
- OJ Access: http://localhost:8000
- AI Chat: http://localhost:5173
- Database: PostgreSQL (backed up at backups/20260426/)
- Judge Service: Normal

### Active Services

| Container            | Service           | Status |
|----------------------|-------------------|--------|
| cdut-vue-ai-chat     | Frontend          | Active |
| cdut-ai-agent-lite   | AI Agent          | Active |
| cdut-oj-backend      | OJ Backend        | Active |
| cdut-oj-judge        | Judge Server      | Active |
| cdut-oj-postgres     | PostgreSQL        | Active |
| cdut-oj-redis        | Redis             | Active |

### Problem Set

| Item          | Count | Status |
|---------------|-------|--------|
| Total problems| 2683  | In database |
| Tags          | 46    | Configured |
| Difficulty    | 3     | Low/Mid/High |

> **Note**: Problem bank data has been backed up via Django `dumpdata`. Original FPS import source files and scripts have been removed. See `backups/20260426/` for complete database dumps.

---

## Completed Features

### 1. System Deployment
- [x] Docker environment on Linux
- [x] QDUOJ install + config
- [x] Database init
- [x] Judge service config

### 2. Problem Import
- [x] 2683 problems in database
- [x] Full database backup preserved (backups/20260426/)
- [x] Test case files backed up

### 3. Tag System
- [x] 46 tag categories
- [x] Tag-based problem filtering

### 4. AI Chat System
- [x] ai-agent-lite (FastAPI) as the sole AI agent
- [x] Vue 3 frontend with chat + problem panel
- [x] WebSocket streaming (raw/finish/error)
- [x] OJ problem browsing + code submission in chat UI
- [x] Per-session OJ submit draft (language, code, state)
- [x] LLM connected
- [x] EmotionAnalyzer (LLM-based 4-dimensional emotion scoring)
- [x] System prompt injection via LlmClient.SYSTEM_PROMPT + _inject_system()
- [x] NextStepSuggester removed (reduced 3x to 2-3x LLM calls per request)

---

## Known Limitations

- No rate limiting or abuse prevention
- ~~No structured code review output from AI~~ → CodeReviewerAgent provides structured analysis but non-standardized output format
- ~~No learning progress tracking~~ → LearningManagerAgent exists but uses LLM generation without algorithmic planning
- No intelligent problem recommendation system (PDF requirement #4, unimplemented)
- No programming thinking visualization (PDF requirement #5, unimplemented)
- No structured knowledge graph (current tag system is flat, not graph-based)

## Project Spec Gap Analysis

> See `docs/PROJECT_SPEC.md`

| PDF Expected Goal | Current Status | Gap |
|-------------------|----------------|-----|
| Contest knowledge graph | 46 flat tags / 2683 problems | No graph structure, no edge weights, no inference |
| Intelligent learning path | LLM generates (no algorithm) | Missing adaptive recommendation algorithm |
| AI code analysis | CodeReviewerAgent | Non-structured, no auto-judge integration |
| Intelligent problem recommendation | Not implemented | — |
| Programming thinking visualization | Not implemented | — |
| Virtual teaching assistant system | Completed | 6 Agent types (5 professional + 1 emotion) |

---

## Next Steps

### Short-term (completed)
- Persistent session + message storage (Postgres)
- User identity binding from OJ auth
- Unified error codes + timeout/retry
- Basic observability (metrics, healthz/readyz)
- Frontend -> backend WebSocket session/user binding
- LLM-based emotion analysis (EmotionAnalyzer)
- System prompt injection (Chinese-only policy)

### Medium-term
- Problem-context prompt template
- Code review structured output (align with PDF requirement #3)
- Judge result auto-analysis (WA/RE/TLE explanation)
- Expand test data coverage
- Intelligent problem recommendation (PDF requirement #4)

### Long-term
- Learning path recommendation with algorithmic planning (PDF requirement #2)
- Contest simulation mode
- 100+ problems with test data
- Knowledge graph construction (PDF requirement #1)
- Programming thinking visualization (PDF requirement #5)

---

## Maintenance

### Daily Check

```bash
docker compose ps
docker compose logs --tail 30 ai-agent-lite
docker compose logs --tail 30 oj-judge
curl http://127.0.0.1:8850/healthz
```

### Database Backup

```bash
# Full Django dumpdata backup
docker exec cdut-oj-backend python manage.py dumpdata -o /tmp/full_dump.json --format json --indent 2
docker cp cdut-oj-backend:/tmp/full_dump.json backups/$(date +%Y%m%d)/

# Test case files backup
docker exec cdut-oj-backend tar -czf /tmp/test_case_backup.tar.gz -C /data/test_case .
docker cp cdut-oj-backend:/tmp/test_case_backup.tar.gz backups/$(date +%Y%m%d)/
```

### Troubleshooting

- Judge stuck: `docker restart cdut-oj-judge`
- AI agent down: `docker compose restart ai-agent-lite`
- Problem invisible: http://localhost:8000/admin/problem -> set visible

---

System status: Running
Readiness: Small-scale trial phase
Recommended: Organize 10-20 students to try first 10 problems