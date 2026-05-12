# Task Plan: OJ Contest Mode MVP

Depends on: `specs/004-oj-contest-mvp/spec.md`

## Phase 1: Backend Foundation

### Task 1 [S] Create contest schema bootstrap and helper queries
- Acceptance:
  - Ensure `ai_agent.contests`, `ai_agent.contest_problems`, `ai_agent.contest_participants` exist.
  - Add nullable `contest_id` + `is_contest` on `ai_agent.submissions` if missing.
- Verify:
  - `curl http://localhost:8850/api/contest/list` returns JSON instead of 404/500.
- Files:
  - `ai-agent-lite/app/routers/compat_oj_api.py`

### Task 2 [M] Implement contest CRUD-lite endpoints
- Acceptance:
  - `POST /api/contest/create`
  - `GET /api/contest/list`
  - `GET /api/contest/detail`
  - `POST /api/contest/join`
- Verify:
  - Admin create success and list/detail reflect created contest.
- Files:
  - `ai-agent-lite/app/routers/compat_oj_api.py`
- Depends on: Task 1

### Task 3 [M] Implement contest submission + rank endpoint
- Acceptance:
  - `POST /api/contest/submission` works in running contest for joined user.
  - `GET /api/contest/rank` returns sorted rows by MVP rule.
- Verify:
  - Submit at least one solution and rank output updates.
- Files:
  - `ai-agent-lite/app/routers/compat_oj_api.py`
- Depends on: Task 2

## Checkpoint A
- Backend endpoints pass curl smoke.
- Non-contest `/api/submission` regression smoke passes.

## Phase 2: Frontend Integration

### Task 4 [S] API client contest methods
- Acceptance:
  - Add create/list/detail/join/contestSubmit/rank methods in api client.
- Verify:
  - Methods hit expected paths and parse JSON.
- Files:
  - `frontend-vue-ai-chat/src/services/apiClient.js`

### Task 5 [M] Composable state for contest data
- Acceptance:
  - `useOjAuthAndProblems` exposes contest list/detail/rank loading actions.
  - Adds local contest join/submission orchestrator.
- Verify:
  - Data can be fetched and stored without breaking existing problem flow.
- Files:
  - `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
- Depends on: Task 4

### Task 6 [L] App.vue contest UI
- Acceptance:
  - New contest tab for users.
  - Contest list + detail + countdown + join button + rank table.
  - Admin page adds contest-create panel (basic form).
- Verify:
  - User can complete list->join->submit->view rank path.
- Files:
  - `frontend-vue-ai-chat/src/App.vue`
- Depends on: Task 5

## Checkpoint B
- End-to-end contest MVP flow works in local Docker stack.

## Phase 3: Regression and Ship

### Task 7 [S] Regression and docs sync
- Acceptance:
  - Non-contest practice mode unaffected.
  - Spec/docs updated with final API notes.
- Verify:
  - Problem list + normal submission smoke pass.
- Files:
  - `specs/004-oj-contest-mvp/spec.md` (final touch)

### Task 8 [S] PR and task-board state sync
- Acceptance:
  - Commit, push branch, create PR.
  - Update ShuJieTai task `6c621441-3b3f-4780-8055-0493244d796e` to completed after merge-ready.
- Verify:
  - PR URL + task PATCH response 200.

## Dependency Graph
Task1 -> Task2 -> Task3 -> Task4 -> Task5 -> Task6 -> Task7 -> Task8
