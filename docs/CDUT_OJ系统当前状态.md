# CDUT OJ System - Current Status

**Updated**: 2026-04-22
**OJ Version**: QDUOJ v1.6.1
**System Status**: Running

---

## System Overview

### Core Info
- Deployment: Docker containers on Linux
- OJ Access: http://localhost:8000
- AI Chat: http://localhost:5173
- Database: PostgreSQL (backed up)
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
| Total problems| 609   | Imported |
| With test data| 24    | Usable for judging |
| Tags          | 19    | Configured |
| Difficulty    | 3     | Low/Mid/High |

---

## Completed Features

### 1. System Deployment
- [x] Docker environment on Linux
- [x] QDUOJ install + config
- [x] Database init
- [x] Judge service config

### 2. Problem Import
- [x] 609 FPS problems imported
- [x] Title, description, samples
- [x] Time/memory limits set
- [x] Difficulty levels assigned

### 3. Tag System
- [x] 19 tag categories
- [x] Smart tag matching
- [x] 100% problem coverage
- [x] Filter by tag

### 4. Test Data
- [x] 2 manually added (A+B, Narcissistic Number)
- [x] 22 batch-added
- [x] Test case format verified
- [x] Judge flow tested

### 5. Judge System
- [x] AC/WA correct
- [x] Time stats accurate
- [x] Memory stats accurate
- [x] Multi test-case support

### 6. AI Chat System
- [x] ai-agent-lite (FastAPI) as the sole AI agent
- [x] Vue 3 frontend with chat + problem panel
- [x] WebSocket streaming (raw/finish/error)
- [x] OJ problem browsing + code submission in chat UI
- [x] Per-session OJ submit draft (language, code, state)
- [x] LLM connected (DeepSeek via API)

---

## Available Problems (24 with test data)

### Very Easy (3) - Week 1-2
1. fps-4063: Hello World (basic output)
2. fps-2b9c: Expression output (I/O)
3. fps-161f: Print characters (string repeat)

### Easy (5) - Week 3-4
4. fps-1386: Character type check (conditionals)
5. fps-1001: Is it a square (conditionals + float)
6. fps-124c: Collect bottle caps (logic)
7. fps-2df6: Palindrome (string)
8. fps-158c: GCD (math)

### Medium (8) - Week 5-8
9. fps-124d: For-loop sum (loop)
10. fps-1710: Snail letter (nested loop)
11. fps-1cb9: Kakutani conjecture (while loop)
12. fps-1013: Find position of 10 (loop control)
13. fps-1795: Array distance (array)
14. fps-2bb8: Reverse output (array)
15. fps-2622: Interval output (array)
16. fps-1b71: Odd increasing sequence (array + sort)

### Hard (6) - Week 9-12
17. fps-107d: Counting (enumeration)
18. fps-14a5: Ming's random numbers (dedup + sort)
19. fps-1767: Minimum loss (greedy)
20. fps-32bd: Nth largest (sort)
21. fps-30a4: Spiral matrix (2D array)
22. fps-4180: Constant trick (math enumeration)

### Test Problems (2)
23. fps-d16b: A+B Problem
24. fps-48c5: Narcissistic Number

---

## Known Limitations

- No rate limiting or abuse prevention
- Only 24 of 609 problems have test data (4%)
- No structured code review output from AI
- No learning progress tracking

---

## Next Steps

### Short-term (completed)
- Persistent session + message storage (Postgres)
- User identity binding from OJ auth
- Unified error codes + timeout/retry
- Basic observability (metrics, healthz/readyz)
- Frontend -> backend WebSocket session/user binding (`session_id` + `user_id` query)

### Medium-term
- Problem-context prompt template
- Code review structured output
- Judge result auto-analysis (WA/RE/TLE explanation)
- Expand test data to 50+ problems

### Long-term
- Learning path recommendation
- Contest simulation mode
- 100+ problems with test data

---

## Maintenance

### Daily Check

```bash
docker compose ps
docker compose logs --tail 30 ai-agent-lite
docker compose logs --tail 30 oj-judge
curl http://127.0.0.1:8850/healthz
```

### Weekly Backup

```bash
docker exec cdut-oj-postgres pg_dump -U onlinejudge onlinejudge > backup_$(date +%Y%m%d).sql
```

### Troubleshooting

- Judge stuck: `docker restart cdut-oj-judge`
- AI agent down: `docker compose restart ai-agent-lite`
- Problem invisible: http://localhost:8000/admin/problem -> set visible

---

System status: Running
Readiness: Small-scale trial phase
Recommended: Organize 10-20 students to try first 10 problems