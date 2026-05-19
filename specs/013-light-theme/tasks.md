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

- [x] Task 1.1: Increase theme icon visual weight and button hit area for better discoverability.
  - Acceptance:
    - Theme icon keeps sun/moon semantics and remains centered.
    - Icon stroke and size are visibly stronger in both light/dark themes.
    - Button tap/click area is at least 42x42.
  - Verify:
    - Code inspection in `ThemeToggle.vue` (`.theme-icon` + button dimensions).
    - Docker frontend build succeeds.
  - Files:
    - `frontend-vue-ai-chat/src/components/ThemeToggle.vue`

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

## Phase 3: Theme consistency follow-up (2026-05-19)

- [ ] Task 4: Make `CodeEditor` theme-aware (light/dark) instead of hardcoding oneDark.
  - Acceptance:
    - Contest submit editor follows current UI theme.
    - Dark mode keeps existing readability; light mode removes dark canvas mismatch.
  - Verify:
    - Code inspection in `CodeEditor.vue`.
    - Docker frontend build succeeds.
  - Files:
    - `frontend-vue-ai-chat/src/components/CodeEditor.vue`

- [ ] Task 5: Remove hardcoded dark background in admin account inputs/selects.
  - Acceptance:
    - `.admin-account-form-grid input/select` use theme tokens only.
    - Light mode account form no longer shows dark-only fields.
  - Verify:
    - grep check confirms no `background: rgba(16, 18, 20, 0.9)` in admin account form block.
    - Docker frontend build succeeds.
  - Files:
    - `frontend-vue-ai-chat/src/assets/main.css`

## Phase 4: Validation

- [ ] Task 6: Run Docker-only frontend build and targeted light-theme regression checks.
  - Acceptance:
    - `docker compose build vue-ai-chat` passes.
    - Contest code editor + admin account inputs render theme-consistent.
  - Verify:
    - Build output success.
    - Light-theme manual sanity on Contest/Admin pages.
    - search_files output for removed hardcoded dark fragments.
