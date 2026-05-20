# CDUT OJ System - Current Status

Updated: 2026-05-20
Status: Running

---

## 1) Runtime Overview

Current runtime is fully migrated to ai-agent-lite + isolate sandbox.

Active containers:
- cdut-vue-ai-chat
- cdut-ai-agent-lite
- cdut-ai-agent-celery-worker
- cdut-sandbox
- cdut-postgres
- cdut-redis

Legacy QDUOJ runtime has been fully removed.

Single database policy:
- only `cdut-postgres` is retained
- schema in use:
  - `public` (problem bank)
  - `ai_agent` (accounts/sessions/submissions)

---

## 2) Data Status

- Problem tables synced from local:
  - `public.problem`
  - `public.problem_tag`
  - `public.problem_tags`
- Test case root:
  - host: `./data/test_cases`
  - container: `/data/test_cases`
- Account policy after migration:
  - keep admin only
  - non-admin accounts cleared

---

## 3) Health Checks

```bash
curl -sS http://127.0.0.1:8850/healthz
curl -sS http://127.0.0.1:8899/health
docker compose ps
```

Submission smoke test:
1. login as admin
2. POST `/api/submission`
3. GET `/api/submission?id=...`
4. verify row persisted in `ai_agent.submissions`

---

## 4) Notes

- QDUOJ runtime dependencies have been removed from deployment.
- Any old docs/scripts referencing `cdut-oj-*` are obsolete and should not be used.
