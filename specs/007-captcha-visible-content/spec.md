# Spec 007 — Captcha image must contain visible characters

## Background
Current local compat OJ captcha endpoint returns a transparent 1x1 placeholder GIF. The register page can load the image, but users see a blank block and cannot visually read any captcha content.

## Goal
Make `GET /api/captcha` return a browser-renderable captcha image that visibly displays characters.

## Scope
- Update `ai-agent-lite/app/routers/compat_oj_api.py` only.
- Keep existing API response contract: `{ error, data }`, where `data` is a data URL.

## Non-goals
- Implement captcha verification enforcement in login/register.
- Introduce external image libraries.
- Change frontend auth form behavior.

## Design
- Generate a 4-character uppercase alphanumeric captcha text.
- Render an inline SVG (`100x44`) with:
  - non-transparent background,
  - centered text,
  - light noise lines for readability realism.
- Base64-encode SVG and return as `data:image/svg+xml;base64,...`.

## Acceptance Criteria
1. `GET /api/captcha?refresh=1` returns 200 and `data` starts with `data:image/svg+xml;base64,`.
2. Decoded payload contains `<svg` and a `<text` node with 4 visible characters.
3. Register page captcha image is no longer visually blank.

## Verification
- Docker runtime probe:
  - `curl -s http://127.0.0.1:8850/api/captcha?refresh=1`
- Decode returned base64 and assert SVG text content exists.
- Through frontend proxy:
  - `curl -s http://127.0.0.1:5173/oj-api/api/captcha?refresh=1`
