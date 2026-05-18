# Spec 006 — Captcha Data URL Render Fix

## Objective
Fix local OJ register captcha image loading failure by returning a browser-safe data URL from `GET /api/captcha`.

## Problem
Current compat OJ captcha endpoint returns a minimal SVG data URL (`data:image/svg+xml;base64,PHN2Zy8+`) that may not render consistently in browser `<img>`.

## Scope
- Update `ai-agent-lite/app/routers/compat_oj_api.py` captcha response payload only.
- No auth flow change.
- No frontend logic change.

## Non-Goals
- Implement real captcha generation/validation.
- Modify register/login validation semantics.

## Design
- Keep endpoint path and response schema unchanged:
  - `{ "error": null, "data": "<data-url>" }`
- Replace current data URL with a valid tiny GIF data URL:
  - `data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==`

## Acceptance Criteria
1. `GET /api/captcha?refresh=1` returns 200 and `data` starts with `data:image/gif;base64,`.
2. Register form captcha `<img :src="ojUser.captchaSrc">` can load without broken-image icon.
3. Login/register APIs remain unaffected.

## Verification Plan (Docker-only)
1. Recreate `ai-agent-lite` service in local compose.
2. Curl check:
   - `curl -s http://127.0.0.1:8850/api/captcha?refresh=1`
   - verify gif data URL prefix.
3. Proxy path check:
   - `curl -s http://127.0.0.1:5173/oj-api/api/captcha?refresh=1`
4. Keep smoke check:
   - `/ai/healthz` returns 200.
