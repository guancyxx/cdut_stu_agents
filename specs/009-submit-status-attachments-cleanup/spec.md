# Spec: Submission status, attachment handoff, and QDOJ cleanup

## Objective
Fix submission UX and deployment drift in CDUT OJ runtime:
1) Submission result should not stay pending due to frontend polling mismatch.
2) After submit, code/result attachments should be staged above chat input, not auto-sent to AI.
3) Code attachment should contain only user-authored editable code, not full template/test wrapper.
4) Sync validated remote compose DB connection settings back to repo.
5) Clean internal docs/code comments that still describe active runtime as QDOJ.

## Scope
- Frontend submit flow and polling query behavior.
- Compose runtime env consistency for ai-agent-lite and worker.
- Internal documentation wording cleanup for current architecture truth.

## Non-Goals
- No change to judge scoring rules.
- No change to submission DB schema.
- No historical document archival/refactor beyond current active references.

## Commands
- Build backend/frontend:
  - `docker compose build ai-agent-lite vue-ai-chat`
- Refresh runtime:
  - `docker compose up -d --force-recreate ai-agent-lite vue-ai-chat`
- Health check:
  - `curl -sf http://127.0.0.1:8850/healthz`
  - `curl -sf http://127.0.0.1:5173/oj-api/ai/healthz`
- Quick submission verification: run python request script against `/oj-api`.

## Design

### A. Fix pending-all-the-time symptom
Frontend polling currently constrains submission list by problem id in a way that may not match actual returned id shape (`id` vs `_id`/display id), causing missed row match and timeout fallback.

Decision:
- Poll with `myself=1,limit=20,page=1` only.
- Match target submission by `submission_id` from submit response.

Expected:
- Frontend always sees the row for submitted id as long as it is in latest page.
- Status transitions from pending/judging to final states correctly.

### B. Attachment staging instead of auto send
Decision:
- Keep creating pending attachments (code/result/next-problem).
- Remove auto `sendMessage()` call from submit success path.
- Show explicit UI state message telling user attachments are staged and require manual send.

Expected:
- User can review/edit context before sending to AI.

### C. Attachment code content trimming
Decision:
- Submit payload still uses merged template+editable code (`buildSubmissionCode`).
- Attachment content uses `normalizedEditableCode` only.

Expected:
- Attachment no longer contains full hidden template/test scaffolding.

### D. Compose drift sync
Decision:
- `LITE_DATABASE_URL` in repo compose aligns with validated remote runtime:
  - `postgresql+asyncpg://onlinejudge:onlinejudge@cdut-oj-postgres:5432/onlinejudge`
- Apply for both `ai-agent-lite` and `ai-agent-worker`.

Expected:
- Avoid next redeploy regression from stale DB host/user/db.

### E. QDOJ residual cleanup
Decision:
- Replace active runtime descriptions using QDOJ wording in key docs/comments with neutral/current wording (legacy OJ / OJ backend).
- Keep migration artifact file names unchanged for traceability.

Expected:
- Internal docs match current architecture reality.

## Boundaries
- Always:
  - Keep Docker-only verification.
  - Verify health + submit flow before PR.
- Ask first:
  - Any DB schema change.
  - Any removal of historical migration documents.
- Never:
  - Re-introduce direct QDOJ runtime dependency.
  - Auto-send submission attachments to AI.

## Success Criteria
- Submission polling returns final status for new submission (not always pending/timeout path).
- Submit flow stages attachments without auto AI send.
- Code attachment content equals user editable code only.
- Repo compose DB settings match validated remote configuration.
- Key internal docs/comments no longer claim active runtime is QDOJ.
