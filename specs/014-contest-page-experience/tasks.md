# Tasks: Contest Page Experience Refresh + Light Theme Texture

Spec: `specs/014-contest-page-experience/spec.md`

## Phase 1: Spec alignment and safety baseline

- [x] Task 1: Align existing contest MVP spec/tasks to reference this UX expansion.
  - Files:
    - `specs/004-oj-contest-mvp/spec.md`
    - `specs/004-oj-contest-mvp/tasks.md`

## Phase 2: Contest page layout and interactions

- [x] Task 2: Refactor contest page to support collapsible list + workspace split.
  - Acceptance:
    - List column collapsible.
    - No selected contest shows inspirational empty state.
    - Selected contest shows left workspace + right leaderboard.
  - Files:
    - `frontend-vue-ai-chat/src/pages/ContestPage.vue`

- [x] Task 3: Replace list refresh action with admin-only create entry and add contest detail modal.
  - Acceptance:
    - Admin sees "新增比赛" in list header.
    - Contest cards include 详情 and 报名/参加 actions.
    - Detail modal excludes problem list details.
  - Files:
    - `frontend-vue-ai-chat/src/pages/ContestPage.vue`

- [x] Task 4: Implement workspace internals (collapsible detail, countdown, running split submit area).
  - Acceptance:
    - Detail panel collapsible.
    - Upcoming shows countdown.
    - Running shows problem cards + submit zone split.
  - Files:
    - `frontend-vue-ai-chat/src/pages/ContestPage.vue`

## Phase 3: Create modal redesign

- [x] Task 5: Rebuild create modal with tabbed structure and two-column problem selection UX.
  - Acceptance:
    - Tabs: 比赛信息 / 题目信息.
    - Problem tab: left selected cards, right filterable grid with circular selector.
  - Files:
    - `frontend-vue-ai-chat/src/components/ContestCreateModal.vue`

## Phase 4: Light theme texture polish

- [x] Task 6: Tune light theme tokens and container depth styles to reduce pale/flat feeling.
  - Acceptance:
    - Improved layered appearance in light mode.
    - Dark mode unchanged in behavior.
  - Files:
    - `frontend-vue-ai-chat/src/assets/main.css`

## Phase 5: Validation and ship

- [ ] Task 7: Docker build and static behavior verification.
  - Verify:
    - `docker compose build vue-ai-chat`
    - grep checks for new contest CSS hooks and no hardcoded dark colors in new blocks.

- [ ] Task 8: Commit, push, and create PR.
