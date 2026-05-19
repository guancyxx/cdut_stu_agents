# Tasks: Light Theme Fixup — Theme Icon + Light Audit

Spec: `specs/013-light-theme/spec.md`

## Phase 1: Theme toggle icon clarity

- [x] Task 1: Ensure top navigation renders an obvious day/night toggle icon button.
  - Acceptance:
    - Theme toggle button displays sun icon in dark mode and moon icon in light mode.
    - Button keeps accessible aria-label/title text aligned with action.
  - Verify:
    - Code inspection in `ThemeToggle.vue` and `App.vue`.
    - Docker frontend build succeeds.
  - Files:
    - `frontend-vue-ai-chat/src/components/ThemeToggle.vue`
    - `frontend-vue-ai-chat/src/App.vue`

## Phase 2: Light theme consistency audit and fix

- [x] Task 2: Replace hardcoded dark-only values in global/app-level style blocks with theme variables.
  - Acceptance:
    - Admin action button styles in `App.vue` use CSS variables.
    - Main layout card/panel and language selector dropdowns no longer force dark colors in light mode.
  - Verify:
    - grep checks show no hardcoded dark hex for these sections.
    - Docker frontend build succeeds.
  - Files:
    - `frontend-vue-ai-chat/src/App.vue`
    - `frontend-vue-ai-chat/src/assets/main.css`

- [x] Task 3: Normalize submit-result and test-case visual tokens to theme-aware variables.
  - Acceptance:
    - Result status colors rely on semantic tokens (`--success/--danger/--warning` + subtle variants).
    - Borders/backgrounds use shared soft/border tokens where appropriate.
  - Verify:
    - grep checks for previously hardcoded status colors in result panel sections.
    - Docker frontend build succeeds.
  - Files:
    - `frontend-vue-ai-chat/src/assets/main.css`

## Phase 3: Validation

- [x] Task 4: Run Docker-only frontend build and static theme-audit grep checks.
  - Acceptance:
    - `docker compose build vue-ai-chat` passes.
    - Expected hardcoded dark-only fragments in audited sections are removed.
  - Verify:
    - Build output success.
    - search_files output captures remaining intentional base-token definitions only.
