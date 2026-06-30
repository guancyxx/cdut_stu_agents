# Spec: Security Hardening — OJ Platform (ai-agent-lite)

Based on penetration test report: `docs/张科强--OJ_测试报告.md`  
Date: 2026-06-29  
Author: auto-generated from pentest findings

---

## Objective

Patch 12 security vulnerabilities identified in a black-box penetration test of the OJ AI agent
platform (`ai-agent-lite v0.1.0`). The primary risk is uncontrolled LLM API consumption (VULN-09,
estimated ¥86,400/month at 1000-concurrent abuse); secondary risks are privilege escalation and
data integrity breaches (forged AC records, database pollution).

No new features. The goal is the smallest correct diff that closes each vulnerability.

---

## Tech Stack

- Backend: FastAPI (Python) — `ai-agent-lite/app/`
- Auth model: cookie-based (`lite_user` httponly cookie = session identity)
- Admin guard: `app/utils/auth_helpers.py:require_admin_username` (raises 401/403)
- WebSocket: `app/routers/websocket.py`
- Config: `app/config.py` (Pydantic Settings, env-file based)

---

## Commands

```
# Run tests
cd ai-agent-lite && python -m pytest

# Lint
cd ai-agent-lite && ruff check app/

# Start dev server
cd ai-agent-lite && uvicorn app.main:app --reload
```

---

## Project Structure

```
ai-agent-lite/
  app/
    main.py                          # FastAPI app factory — docs_url config here
    config.py                        # Settings — add INTERNAL_API_SECRET here
    routers/
      websocket.py                   # VULN-09: add auth before accept()
      problem_upload.py              # VULN-02 / VULN-08: missing admin guard
      problem_audit.py               # VULN-04: entire router needs admin guard
      submission_events.py           # VULN-03: add internal-secret guard
      auth.py                        # VULN-05: fix CSRF token generation
      metrics_router.py              # VULN-06: add admin guard
    utils/
      auth_helpers.py                # existing require_admin_username — reuse as-is
```

---

## Code Style

Existing pattern for admin-guarded endpoints (from `problem_upload.py:173`):

```python
# inline import + call pattern (used in update_single_problem)
async def update_single_problem(problem_id: str, req: ..., request: Request):
    from app.utils.auth_helpers import require_admin_username
    await require_admin_username(request)
    ...

# router-level pattern (preferred — one line protects all endpoints)
from app.utils.auth_helpers import require_admin_username
from fastapi import Depends
router = APIRouter(prefix="/audit", dependencies=[Depends(require_admin_username)])
```

Use router-level `dependencies=` when all endpoints in a router need the same guard.
Use inline `await require_admin_username(request)` only for mixed routers.

---

## Vulnerability → Fix Mapping

### P0 — Fix immediately (active financial/integrity risk)

| ID | Vuln | File | Fix |
|----|------|------|-----|
| VULN-09 | WebSocket no auth → LLM abuse | `routers/websocket.py:59` | Check `lite_user` cookie before `websocket.accept()` |
| VULN-02 | `POST /admin/problems/create` no auth | `routers/problem_upload.py:124` | Add `await require_admin_username(request)` |
| VULN-04 | All `/audit/*` endpoints no auth | `routers/problem_audit.py:21` | Router-level `dependencies=[Depends(require_admin_username)]` |
| VULN-03 | `/submission-events/fallback` forgeable | `routers/submission_events.py:121` | Add `INTERNAL_API_SECRET` header check |

### P1 — Fix within 24h

| ID | Vuln | File | Fix |
|----|------|------|-----|
| VULN-01 | OpenAPI docs exposed | `main.py:45` | `docs_url=None, redoc_url=None, openapi_url=None` (env-gated) |
| VULN-05 | CSRF token hardcoded + JS-readable | `routers/auth.py:27,37,252,288` | `secrets.token_urlsafe(32)` per-session; keep non-httponly (SPA reads it) |
| VULN-06 | Prometheus metrics exposed | `routers/metrics_router.py:10` | Add `Depends(require_admin_username)` |
| VULN-08 | `/admin/problems/tags` no auth | `routers/problem_upload.py:321` | Add `Request` param + `await require_admin_username(request)` |

### P2 — Fix within 1 week

| ID | Vuln | File | Fix |
|----|------|------|-----|
| VULN-10 | Weak password min-length=6 | `routers/auth.py:161,216` | Raise min to 8; add complexity check |
| VULN-07 | Problem list unauthenticated | `routers/problems.py:16` | Require login cookie |
| VULN-11 | Captcha no rate limit | nginx config | `limit_req` at nginx layer (out of FastAPI scope) |
| VULN-12 | Chat history in localStorage | Vue frontend | Out of scope for this spec (no frontend files) |

---

## VULN-09 Detail: WebSocket Auth

Current flow (insecure):
```
client connects → websocket.accept() → read user_id from query param (trusts it) → proceed
```

Fixed flow:
```
client connects → read lite_user cookie → query DB (async_session) → 401/close if invalid → accept()
```

The `require_admin_username` function cannot be reused directly (WebSocket context differs from HTTP
Request). Instead, inline a session lookup using `current_username(request)` logic adapted for
WebSocket cookies.

```python
from app.utils.auth_helpers import current_username

@router.websocket("/ws")
async def ws_handler(websocket: WebSocket) -> None:
    authed_user = websocket.cookies.get("lite_user")
    if not authed_user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await websocket.accept()
    user_id = authed_user   # trust cookie, not query param
    ...
```

Note: `user_id` is currently taken from query param `?user_id=...` which the attacker forges.
After fix, override it from the trusted `lite_user` cookie.

---

## VULN-03 Detail: Submission Events Internal Secret

This endpoint is called service-to-service (OJ test-case runner → FastAPI). Add a shared secret:

1. Add `INTERNAL_API_SECRET: str = ""` to `app/config.py` Settings
2. In the endpoint, if `settings.internal_api_secret` is set, require matching
   `X-Internal-Secret` request header.
3. Deploy: set `INTERNAL_API_SECRET=<random>` in `.env`; configure the OJ runner to send it.

---

## VULN-05 Detail: CSRF Token

Current: hardcoded `"lite-csrf-token"` set on captcha, profile, register, login.

Fixed: generate `secrets.token_urlsafe(32)` and store it in the `csrftoken` cookie.
The frontend already reads `document.cookie` for the token and sends it as `X-CSRFToken` —
this requires no frontend change, just make the token non-constant.

The token does NOT need to be validated server-side in this PR (server-side CSRF validation is a
separate larger refactor; SameSite=Lax on the session cookie already blocks cross-site requests).
The immediate fix is removing the constant value so XSS can't pre-forge requests with it.

---

## VULN-01 Detail: OpenAPI Docs

Disable via environment flag. Keep enabled in non-production environments:

```python
# main.py
import os
_docs = None if os.getenv("DISABLE_DOCS", "0") == "1" else "/docs"
_redoc = None if os.getenv("DISABLE_DOCS", "0") == "1" else "/redoc"
_openapi = None if os.getenv("DISABLE_DOCS", "0") == "1" else "/openapi.json"

app = FastAPI(title="ai-agent-lite", docs_url=_docs, redoc_url=_redoc, openapi_url=_openapi, ...)
```

Set `DISABLE_DOCS=1` in production `.env`.

---

## Boundaries

- **Always**: run `require_admin_username` before any data-mutating admin endpoint
- **Ask first**: changes to nginx config, `.env` secrets, Vue frontend code
- **Never**: skip or bypass `require_admin_username`; use hardcoded secrets in source; commit `.env`

---

## Success Criteria

- [ ] `POST /admin/problems/create` returns 401/403 for unauthenticated requests
- [ ] `GET/POST /audit/*` returns 401/403 for unauthenticated requests
- [ ] `GET /metrics` returns 401/403 for unauthenticated requests
- [ ] `GET /admin/problems/tags` returns 401/403 for unauthenticated requests
- [ ] `WS /ws` with no `lite_user` cookie closes with code 4001
- [ ] `POST /submission-events/fallback` without secret header returns 403 (when secret is set)
- [ ] `csrftoken` cookie value differs between sessions (not hardcoded)
- [ ] `/openapi.json` returns 404 when `DISABLE_DOCS=1`
- [ ] Password registration rejects passwords shorter than 8 characters
- [ ] All existing admin-protected endpoints (accounts) continue to work

---

## Open Questions

1. **VULN-07 (problem list auth)**: Is this intentional public access? If OJ is meant to be open
   to unregistered visitors, requiring login would break the UX. Recommend confirming before
   implementing the auth gate. This spec marks it as P2 and out of current implementation scope.

2. **VULN-11 (captcha rate limit)**: Requires nginx config change — out of FastAPI scope.
   Deploy-side fix: add `limit_req_zone` to nginx.

3. **VULN-12 (localStorage)**: Requires Vue frontend changes — out of FastAPI scope.

4. **VULN-10 (root/123456 password)**: Operational fix — reset via admin interface immediately.
   Code-level: raise min password length to 8 in this PR.
