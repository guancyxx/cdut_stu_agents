# ai-agent-lite V1 Development Task List (P0 Stability Milestone)

**Created**: 2026-04-22
**Goal**: Transform ai-agent-lite from demo to production-minimal: persistent sessions, user identity, error hardening, observability.

## Database Schema

### Table: sessions

```sql
CREATE TABLE sessions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       VARCHAR(64) NOT NULL,
  problem_id    VARCHAR(32),
  title         VARCHAR(256),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  status        VARCHAR(16) NOT NULL DEFAULT 'active'  -- active / archived
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_problem ON sessions(problem_id);
```

### Table: messages

```sql
CREATE TABLE messages (
  id            BIGSERIAL PRIMARY KEY,
  session_id    UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role          VARCHAR(16) NOT NULL,  -- user / assistant / system
  content       TEXT NOT NULL,
  msg_type      VARCHAR(16) NOT NULL DEFAULT 'text',  -- text / code / error
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_session ON messages(session_id, created_at);
```

### Table: audit_log

```sql
CREATE TABLE audit_log (
  id            BIGSERIAL PRIMARY KEY,
  request_id    UUID NOT NULL,
  session_id    UUID,
  user_id       VARCHAR(64),
  event_type    VARCHAR(32) NOT NULL,  -- ws_connect / ws_message / llm_call / oj_submit / error
  detail        JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_request ON audit_log(request_id);
CREATE INDEX idx_audit_time ON audit_log(created_at);
```

---

## File-Level Task Breakdown

### Commit 1: Database setup + models
**Files to create/modify**:
- `ai-agent-lite/app/database.py` (new) - connection pool, init_db, get_db
- `ai-agent-lite/app/models.py` (new) - SQLAlchemy models for sessions, messages, audit_log
- `ai-agent-lite/requirements.txt` (modify) - add sqlalchemy>=2.0, asyncpg, psycopg2-binary
- `ai-agent-lite/Dockerfile` (modify) - add postgres client libs if needed
- `docker-compose.yml` (modify) - add LITE_DATABASE_URL env var to ai-agent-lite service

**Verification**:
- python -c "from app.models import Session, Message, AuditLog"
- Tables created in existing postgres container

### Commit 2: Persistent session repository
**Files to create/modify**:
- `ai-agent-lite/app/repositories/session_repo.py` (new) - CRUD for sessions
- `ai-agent-lite/app/repositories/message_repo.py` (new) - CRUD for messages
- `ai-agent-lite/app/repositories/__init__.py` (new)

**Key methods**:
- SessionRepo: create, get_by_id, list_by_user, update_status
- MessageRepo: create, list_by_session (paginated), count_by_session

**Verification**:
- Unit test: create session -> get -> list -> verify

### Commit 3: Replace in-memory sessions with DB-backed
**Files to modify**:
- `ai-agent-lite/app/main.py` - remove SessionState dataclass, inject repo deps
- `ai-agent-lite/app/main.py` - ws handler: create/load session from DB, append messages

**Key changes**:
- On WS connect: load session by session_id from DB (or create if new)
- On user message: insert message row (role=user)
- On assistant response: insert message row (role=assistant)
- History for LLM context: query messages from DB instead of in-memory list

**Verification**:
- WS smoke test: send message, restart container, send again -> history persists
- healthz still returns ok

### Commit 4: User identity binding
**Files to create/modify**:
- `ai-agent-lite/app/auth.py` (new) - extract user_id from OJ cookie or token
- `ai-agent-lite/app/main.py` - add user_id to WS query param or header extraction
- `ai-agent-lite/app/main.py` - include user_id in session creation

**Key decisions**:
- Option A: Frontend passes OJ auth cookie to WS handshake (transparent via proxy)
- Option B: Frontend sends user_id in first WS message or query param
- Pref: Option A if cookie is accessible, else Option B

**Verification**:
- Two different user_ids -> different session lists, no cross-access

### Commit 5: Unified error codes + timeout/retry
**Files to create/modify**:
- `ai-agent-lite/app/errors.py` (new) - ErrorCode enum, AppError exception class
- `ai-agent-lite/app/llm_client.py` (new or extract from main.py) - LLMAdapter with retry + timeout
- `ai-agent-lite/app/main.py` - use LLMAdapter, catch AppError, send type:error with code

**Error code scheme**:
- LLM_TIMEOUT: LLM request exceeded timeout
- LLM_RATE_LIMIT: Provider returned 429
- LLM_SERVER_ERROR: Provider returned 5xx
- INVALID_INPUT: Message validation failed
- SESSION_NOT_FOUND: Session ID not found
- INTERNAL: Unexpected server error

**Retry policy**:
- Retry on: 429 (up to 2x with exponential backoff), 5xx (1x after 2s)
- No retry on: validation error, auth error
- Max total wait: 30s

**Verification**:
- Test with invalid API key -> proper error code returned
- Test with timeout -> LLM_TIMEOUT error code

### Commit 6: Observability - /readyz + metrics
**Files to create/modify**:
- `ai-agent-lite/app/main.py` - add GET /readyz endpoint
- `ai-agent-lite/app/metrics.py` (new) - Prometheus counter/histogram definitions
- `ai-agent-lite/app/main.py` - add GET /metrics endpoint
- `ai-agent-lite/app/middleware.py` (new) - request_id + timing middleware
- `ai-agent-lite/requirements.txt` - add prometheus-client

**Metrics**:
- ws_connections_total (counter)
- ws_messages_total (counter, label: direction=in/out, type=raw/finish/error)
- llm_request_duration_seconds (histogram)
- llm_errors_total (counter, label: code)

**Ready check**:
- DB connection ok
- LLM API reachable (or mock mode)

**Verification**:
- curl /readyz -> 200 when DB up, 503 when DB down
- curl /metrics -> Prometheus text format

### Commit 7: Audit logging
**Files to create/modify**:
- `ai-agent-lite/app/audit.py` (new) - async audit logger
- `ai-agent-lite/app/main.py` - log WS connect/disconnect, messages, LLM calls, errors

**Rules**:
- Log all WS connect/disconnect with user_id, session_id, request_id
- Log LLM call duration, model, token count estimate
- Log errors with code and detail
- Never log API keys, passwords, PII (mask in detail JSON)
- Async write (fire-and-forget, no blocking on WS handler)

**Verification**:
- Send WS message -> audit_log row appears with correct event_type

---

## Dependency Updates

```
# requirements.txt additions
sqlalchemy>=2.0
asyncpg>=0.29
prometheus-client>=0.20
```

## docker-compose.yml Changes

ai-agent-lite service needs:
- LITE_DATABASE_URL=postgresql+asyncpg://onlinejudge:password@oj-postgres:5432/onlinejudge
- (or use a dedicated DB; for simplicity reuse existing QDUOJ postgres with separate schema)

## Execution Order

```
Commit 1 (DB + models)
  -> Commit 2 (repos)
  -> Commit 3 (replace in-memory)
  -> Commit 4 (user identity)
  -> Commit 5 (errors + retry)   [independent of 4, can parallel]
  -> Commit 6 (observability)    [depends on 5 for error metrics]
  -> Commit 7 (audit)            [depends on 6 for request_id]
```

Estimated effort: 1-2 days for commits 1-4, 1 day for 5-7.