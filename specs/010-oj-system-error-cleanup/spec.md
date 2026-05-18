# Spec: Fix OJ submit showing System Error and remove obsolete logic

## Background
Users report OJ submit result shown as `System Error` in UI. Recent logs show many latest submissions are persisted with `verdict=SE` and `compile_error=Problem not found: <numeric_id>`.

## Root Cause
- Frontend submits numeric `problem_id` (database integer id).
- Judge service queries problem by `_id` string only (`WHERE _id = :pid`).
- For numeric ids like `2690`, query misses, so judge returns `SE` with `Problem not found`.
- UI maps `SE` to `System Error`.

This is not sandbox failure; it is identifier mismatch.

## Requirements
1. Submission judging must support both problem identifiers:
   - display id (`_id`, e.g., `LQ1266`, `custom-50d1`)
   - numeric id (`id`, integer as string)
2. Remove obsolete/legacy comments referencing QDUOJ in touched code.
3. Keep behavior stable for existing successful `_id` submissions.
4. End-to-end verification via Docker compose only.

## Design
### Backend
- File: `ai-agent-lite/app/services/judge_service.py`
- Change `_get_problem_info(problem_id)` SQL:
  - from: `WHERE _id = :pid`
  - to: `WHERE _id = :pid OR CAST(id AS TEXT) = :pid`
- Keep return shape unchanged.

### Code cleanup
- File: `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
  - Remove outdated QDUOJ-specific comments around status map.

## Validation plan
1. Rebuild/recreate services: `ai-agent-lite`, `ai-agent-celery-worker`, `vue-ai-chat`.
2. API E2E flow through `5173/oj-api`:
   - captcha -> register -> login -> problem list -> submit -> submissions poll.
3. Acceptance criteria:
   - new submission appears in list
   - result is not forced to `SYSTEM_ERROR` due to `Problem not found`
   - ai-agent-lite logs no `Problem not found: <id>` for new submit

## Non-goals
- No fallback-event protocol change.
- No schema migration.
