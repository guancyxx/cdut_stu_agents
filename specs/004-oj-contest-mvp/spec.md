# Spec: OJ Contest Mode MVP

## Objective
Deliver a minimal, end-to-end contest workflow in cdut_stu_agents OJ runtime:
1) Admin can create and publish a contest with selected problems.
2) Logged-in user can list contests, enter one active contest, and view countdown.
3) User can submit solutions within contest context.
4) User can view contest result/rank after contest ends.
5) Existing normal problem practice flow remains stable.

## Assumptions
1. Contest mode is scoped to current ai-agent-lite + frontend-vue-ai-chat runtime only (no qduoj service dependency).
2. Contest ranking for MVP uses simple ACM-like scoring: solved_count desc, total_time_ms asc.
3. Contest problem set references existing `public.problem._id` values.
4. User identity source remains `lite_user` cookie username.
5. No anti-cheat, no freeze board, no virtual participation in MVP.

## Commands (Docker-only)
- Build backend/frontend:
  - `docker compose build ai-agent-lite vue-ai-chat`
- Recreate app containers (preserve Postgres/Redis):
  - `docker stop cdut-ai-agent-lite cdut-vue-ai-chat && docker rm cdut-ai-agent-lite cdut-vue-ai-chat && docker compose create ai-agent-lite vue-ai-chat && docker compose start ai-agent-lite vue-ai-chat`
- Backend health:
  - `curl -s -o /tmp/health.json -w '%{http_code}\n' http://localhost:8850/api/v1/health`
- Contest API smoke:
  - `curl -s http://localhost:8850/api/contest/list | python3 -m json.tool`

## Project Structure
- Backend API/router:
  - `ai-agent-lite/app/routers/compat_oj_api.py`
- Backend schema migration/bootstrap (SQL-based, lightweight):
  - `ai-agent-lite/app/routers/compat_oj_api.py` (startup ensure function)
- Frontend API client:
  - `frontend-vue-ai-chat/src/services/apiClient.js`
- Frontend state/composable:
  - `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
- Frontend UI:
  - `frontend-vue-ai-chat/src/App.vue`

## API Design (MVP)
All endpoints are under existing compat prefix `/api` in ai-agent-lite:

1) `POST /api/contest/create`
- Auth: admin only (`admin_type >= 1`)
- Body:
  - `title: string`
  - `description?: string`
  - `start_time: ISO8601`
  - `end_time: ISO8601`
  - `problem_ids: string[]` (problem `_id`)
- Return: `{ error: null, data: { contest_id } }`

2) `GET /api/contest/list`
- Query: optional `status` (`upcoming|running|ended|all`)
- Return: list of contests with computed status by server time.

3) `GET /api/contest/detail?contest_id=<id>`
- Return contest base info + problems + user join state.

4) `POST /api/contest/join`
- Body: `{ contest_id: string }`
- Creates participant row if absent.

5) `POST /api/contest/submission`
- Body:
  - `contest_id: string`
  - `problem_id: string`
  - `language: string`
  - `code: string`
- Reuse existing judge pipeline, but store contest linkage and rank-impact metadata.

6) `GET /api/contest/rank?contest_id=<id>`
- Return sorted ranking list with solved_count / penalty_time_ms.

## Data Model (new tables, schema ai_agent)
1) `ai_agent.contests`
- `id uuid pk`
- `title varchar(255)`
- `description text`
- `start_time timestamptz`
- `end_time timestamptz`
- `status varchar(16)` (stored advisory, computed view still allowed)
- `created_by varchar(64)`
- `created_at timestamptz`
- `updated_at timestamptz`

2) `ai_agent.contest_problems`
- `id uuid pk`
- `contest_id uuid fk -> contests.id`
- `problem_id varchar(64)` (maps to `public.problem._id`)
- `display_order int`
- unique `(contest_id, problem_id)`

3) `ai_agent.contest_participants`
- `id uuid pk`
- `contest_id uuid fk`
- `user_id varchar(64)`
- `joined_at timestamptz`
- unique `(contest_id, user_id)`

4) Extend `ai_agent.submissions` (backward compatible)
- add nullable `contest_id uuid`
- add nullable `is_contest boolean default false`

## Contest State Rules
- `upcoming`: now < start_time
- `running`: start_time <= now < end_time
- `ended`: now >= end_time
- Contest submission allowed only in `running` state and participant joined.

## Ranking Rules (MVP)
- For each participant/problem: first AC locks problem as solved.
- solved_count: number of solved problems.
- penalty_time_ms: sum of AC submission elapsed from contest start + wrong submission penalties before AC (20min each).
- Sort: solved_count DESC, penalty_time_ms ASC, joined_at ASC.

## Security & Boundaries
- Always:
  - Validate contest time window (`end_time > start_time`).
  - Validate problem_ids exist in `public.problem`.
  - Enforce admin-only create.
  - Enforce running-state + participant membership for contest submissions.
- Ask first:
  - Any scoring rule change from MVP ACM-like behavior.
  - Any cross-service integration with external OJ runtime.
- Never:
  - Break existing `/api/submission` non-contest flow.
  - Introduce host-runtime-only verification commands.

## Testing Strategy
- API smoke tests for create/list/detail/join/contest-submission/rank.
- Regression smoke for non-contest problem submit/list/detail.
- Docker build + recreate verification for ai-agent-lite and vue-ai-chat.

## Success Criteria
1. Admin can create one contest with >=1 existing problem.
2. User can see contest list, open detail, join running contest.
3. User can submit in contest and get judged result.
4. Rank endpoint returns deterministic sorted rows.
5. Normal non-contest OJ submit path still works.
6. Docker build and smoke checks pass.

## Known Gaps (2026-05-19 audit)
1. Contest page lacks lifecycle guidance and action gating:
   - upcoming/running/ended state exists but no explicit operator guidance text.
   - contest create entry is exposed globally for admins but without workflow hints.
2. No countdown/remaining time display in contest detail despite spec objective.
3. Rank visibility is not gated by contest state (currently visible throughout), inconsistent with “after contest ends” objective.
4. Join/submit controls are not fully state-driven (e.g., upcoming/ended needs explicit disabled state + reason).

## Additional Acceptance Criteria (this round)
1. Contest detail must show clear lifecycle status + countdown/remaining text.
2. Join button behavior:
   - upcoming: disabled with reason
   - running: enabled (if not joined)
   - ended: disabled with reason
3. Submit area behavior:
   - hidden or read-only unless contest is running and user joined.
   - explicit warning text for disallowed states.
4. Rank area behavior:
   - for MVP keep list available, but add state banner clarifying provisional/final semantics by lifecycle.
5. Admin create contest workflow must include immediate refresh/select/focus after creation.

## Open Questions
1. Keep rank fully visible during running state with “provisional” label (chosen for MVP).
2. Do not add freeze board/rejudge in this round.

## Follow-up UX Expansion (2026-05-19)
Contest information architecture and visual redesign requirements are tracked in:
- `specs/014-contest-page-experience/spec.md`
- `specs/014-contest-page-experience/tasks.md`

This MVP spec remains the backend/flow baseline; new page-structure and light-theme texture work should follow Spec 014.
