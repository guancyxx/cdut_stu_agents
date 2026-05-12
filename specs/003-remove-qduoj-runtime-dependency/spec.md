# Spec: Remove QDUOJ Runtime Dependency Completely

## Objective
Fully remove runtime dependency on QDUOJ services and APIs. Frontend and ai-agent-lite must run independently with cdut-postgres/cdut-redis/cdut-sandbox only.

## Scope
1. Replace frontend /oj-api proxy target from oj-backend to ai-agent-lite.
2. Implement QDUOJ-compatible API surface in ai-agent-lite for current frontend usage:
   - GET /api/profile
   - GET /api/captcha
   - POST /api/login
   - POST /api/register
   - POST /api/logout
   - GET /api/problem/
   - GET /api/submissions
   - GET /api/submission
3. Keep judge path on /api/submit (already migrated) and bridge compatibility endpoints to ai_agent.submissions.
4. Fix /oj/test_case_content submission detail source from legacy submission table to ai_agent.submissions.
5. Remove repository-level QDUOJ submodule linkage (.gitmodules + qduoj submodule pointer).
6. Update docs that still instruct using oj-backend/oj-judge runtime.

## Non-goals
- Rewriting all frontend naming (e.g. useOjAuthAndProblems symbol names).
- Migrating historical backup artifacts under backups/.

## Design
- Add new router `compat_oj_api.py` in ai-agent-lite/app/routers.
- Use direct PostgreSQL queries (public.problem + ai_agent.submissions + ai_agent.local_users).
- Provide cookie-based lightweight session for frontend compatibility (`lite_user`, `csrftoken`).
- Map modern verdict strings to legacy numeric status codes expected by frontend.

## Data Model Additions
- `ai_agent.local_users`
  - id bigserial pk
  - username varchar(32) unique not null
  - password_hash varchar(128) not null
  - email varchar(120) nullable
  - admin_type integer default 0
  - created_at timestamptz
  - updated_at timestamptz

## Security
- Password hashing is Django-compatible PBKDF2-SHA256 (legacy-hash compatible for migrated users).
- Generic auth failure messages.
- Input length validation and username regex whitelist.
- Http...[truncated]

## Verification
- docker compose build ai-agent-lite vue-ai-chat
- docker compose up -d --force-recreate ai-agent-lite vue-ai-chat
- API smoke tests:
  - /api/register -> /api/login -> /api/profile -> /api/logout
  - /api/problem/?limit=21&offset=0
  - /api/submission then /api/submissions and /api/submission?id=...
  - /oj/test_case_con...[truncated]- frontend build via Docker succeeds.

## Success Criteria
- No runtime requests to oj-backend/oj-judge/oj-postgres/oj-redis.
- Frontend can login/register, list problems, submit, and view submission detail against ai-agent-lite only.
- Repository no longer tracks qduoj submodule in root git metadata.
