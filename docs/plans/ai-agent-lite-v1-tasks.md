# ai-agent-lite V1 Development Task List (P0 Stability Milestone)

**Created**: 2026-04-22
**Updated**: 2026-04-23
**Status**: Completed

All 7 commits have been implemented and verified.

## Post-V1 Next Action (executed on 2026-04-23)

- Goal: complete frontend-to-backend identity/session binding to match V1 backend capability.
- Action: frontend WebSocket now connects with `session_id` + `user_id` query params, and syncs server-returned UUID `session_id` from `init` event back into local session metadata.
- Expected result:
  - One frontend session maps to one backend persistent session.
  - `user_id` is attached from OJ authenticated profile when available.
  - Existing local history remains mapped after server session ID normalization.


## Implementation Summary

| Commit | Description | Files | Status |
|--------|-------------|-------|--------|
| C1 | Database setup + models | database.py, models.py, requirements.txt, Dockerfile, docker-compose.yml | Done |
| C2 | Persistent session/message repositories | session_repo.py, message_repo.py | Done |
| C3 | Replace in-memory with DB-backed | main.py (rewrite) | Done |
| C4 | User identity binding | main.py (user_id from ws query param) | Done |
| C5 | Unified error codes + retry | errors.py, llm_client.py | Done |
| C6 | Observability (/readyz + metrics) | metrics.py, middleware.py, main.py | Done |
| C7 | Audit logging | audit.py | Done |

## Verification Results

- healthz: `{"ok":true,"llm_enabled":true,"model":"deepseek-chat"}`
- readyz: `{"ok":true,"db":true,"llm":true,"model":"deepseek-chat"}`
- metrics: Prometheus-format endpoint returning ws_connections_active, ws_messages_total, llm_request_duration_seconds, db_operations_total
- WS test: session created in DB, messages persisted, LLM streaming works
- DB tables: sessions, messages, audit_log created in ai_agent schema
- Audit log: ws_connect, llm_complete, ws_disconnect events recorded

## Database Schema (in ai_agent schema)

### sessions
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| user_id | VARCHAR(64) | From WS query param |
| problem_id | VARCHAR(32) | Optional |
| title | VARCHAR(256) | Optional |
| status | VARCHAR(16) | active/archived |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### messages
| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL | Primary key |
| session_id | UUID | FK to sessions |
| role | VARCHAR(16) | user/assistant/system |
| content | TEXT | |
| msg_type | VARCHAR(16) | text/code/error |
| created_at | TIMESTAMPTZ | |

### audit_log
| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL | Primary key |
| request_id | UUID | |
| session_id | UUID | Nullable |
| user_id | VARCHAR(64) | Nullable |
| event_type | VARCHAR(32) | ws_connect/disconnect/llm_complete/error |
| detail | JSONB | Masked (no PII/keys) |
| created_at | TIMESTAMPTZ | |

## Architecture

```
Browser
  |
  | WS /ws?session_id=X&user_id=Y
  v
ai-agent-lite (FastAPI)
  |
  +-- /healthz  (liveness)
  +-- /readyz   (readiness: DB + LLM)
  +-- /metrics   (Prometheus)
  +-- /ws        (WebSocket chat)
  |
  | PostgreSQL (ai_agent schema)
  |   sessions / messages / audit_log
  |
  | DeepSeek API (streaming)
```