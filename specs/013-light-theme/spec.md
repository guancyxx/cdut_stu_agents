# Spec: Light Theme — 013

Status: approved | Author: Hermes Agent | Date: 2026-05-19

## Objective

Add a light theme to the OJ frontend. Users can switch between light and dark themes
without affecting any existing business state (auth, chat sessions, submission state,
problem context). The default theme follows the system preference
(`prefers-color-scheme`) on first visit; a manual override persists in `localStorage`.

## Tech Stack

- Vue 3 Composition API (existing)
- Plain CSS custom properties (existing 12-var design system)
- `localStorage` for persistence
- No new dependencies

## Implementation Approach

**Approach A: CSS-variable flip via `data-theme` attribute on `<html>`.**

- Define light-theme variable values in a `[data-theme="light"]` block
- Add a `data-theme` attribute binding the current theme to `<html>`
- A composable (`useTheme.js`) provides reactive `theme` + `toggleTheme()`
- A `<ThemeToggle>` button in the top nav (sun/moon icon)
- On mount: read `localStorage` → fall back to `prefers-color-scheme` → default dark
- On change: update `data-theme`, persist to `localStorage`

### Why not two separate stylesheets or a CSS preprocessor theme?

- The project already has a clean CSS-variable design system with 147 `var(--...)` references across 2,476 lines
- A single source of truth (`:root` / `[data-theme]`) keeps maintenance simple
- Avoids introducing new build tooling or dependencies

## Scope

### In scope

1. Define 12 light-theme variable values
2. Theme system: auto-detect, toggle, persist
3. `<ThemeToggle>` component in top nav
4. Hardcoded dark-only values audited and fixed (raw `rgba(255,255,255,...)`, unthemed `#hex` colors)
5. `color-scheme` dynamically set (light/dark) so native form controls match
6. Scrollbar styles adapt to theme

### Out of scope

- UI redesign or layout changes
- Theme picker with 3+ themes (only light/dark)
- Admin-configurable theme (only user-local)
- Syncing theme preference to backend (localStorage only)

## CSS Variables — Dark (existing) vs Light (new)

| Variable           | Dark value                          | Light value                         |
|---------------------|-------------------------------------|-------------------------------------|
| `--bg-marketing`    | `#08090a`                         | `#f8f9fa`                           |
| `--bg-panel`        | `#0f1011`                         | `#ffffff`                           |
| `--bg-surface`      | `#191a1b`                         | `#f1f3f5`                           |
| `--bg-soft`         | `rgba(255,255,255,0.02)`          | `rgba(0,0,0,0.02)`                  |
| `--bg-soft-hover`   | `rgba(255,255,255,0.04)`          | `rgba(0,0,0,0.04)`                  |
| `--border-subtle`   | `rgba(255,255,255,0.05)`          | `rgba(0,0,0,0.06)`                  |
| `--border-standard` | `rgba(255,255,255,0.08)`          | `rgba(0,0,0,0.10)`                  |
| `--text-primary`    | `#f7f8f8`                         | `#1a1a2e`                           |
| `--text-secondary`  | `#d0d6e0`                         | `#495057`                           |
| `--text-tertiary`   | `#8a8f98`                         | `#868e96`                           |
| `--brand`           | `#5e6ad2`                         | `#4c51bf`                           |
| `--brand-hover`     | `#828fff`                         | `#667eea`                           |
| `--success`         | `#10b981`                         | `#059669`                           |
| `--danger`          | `#ef4444`                         | `#dc2626`                           |

Additional variables needed for hardcoded colors currently in CSS:

| Variable              | Dark value          | Light value        |
|------------------------|---------------------|--------------------|
| `--brand-subtle-bg`    | `rgba(94,106,210,0.2)` | `rgba(76,81,191,0.1)` |
| `--brand-subtle-text`  | `#c7d2fe`           | `#4338ca`          |
| `--danger-subtle-bg`   | `rgba(239,68,68,0.2)` | `rgba(220,38,38,0.1)` |
| `--danger-subtle-text` | `#fecaca`           | `#991b1b`          |
| `--success-subtle-bg`  | `rgba(16,185,129,0.1)` | `rgba(5,150,105,0.1)` |
| `--success-subtle-text`| `#34d399`           | `#047857`          |
| `--nav-bg-gradient`    | `linear-gradient(...)` (dark) | `linear-gradient(...)` (light) |
| `--scrollbar-thumb`    | `rgba(130,143,255,0.35)` | `rgba(0,0,0,0.15)` |
| `--shadow-subtle`      | `rgba(0,0,0,0.3)`   | `rgba(0,0,0,0.08)` |

## Files Likely Touched

| File | Change |
|------|--------|
| `frontend-vue-ai-chat/src/assets/main.css` | Add `[data-theme="light"]` block, new variables, fix unthemed colors |
| `frontend-vue-ai-chat/src/composables/useTheme.js` | **New** — theme detection, toggle, persistence |
| `frontend-vue-ai-chat/src/components/ThemeToggle.vue` | **New** — sun/moon icon toggle button |
| `frontend-vue-ai-chat/src/App.vue` | Import `<ThemeToggle>`, bind `data-theme` on mount |
| `frontend-vue-ai-chat/src/main.js` | Minimal change — apply `data-theme` to `<html>` early to avoid FOUC |

## Constraints

- **No behavioral change to existing business logic**: auth, sessions, submissions, problem state completely untouched
- **No new dependencies**: pure Vue 3 + CSS + `localStorage`
- **Backward compatible**: if `localStorage` has no key or browser doesn't support `prefers-color-scheme`, default to dark (current behavior)
- **FOUC prevention**: `data-theme` must be set on `<html>` before Vue mounts (inline script in `index.html` or early in `main.js`)
- **Code comments in English only**

## Testing Strategy

- **Build verification**: `docker compose -p cdut build vue-ai-chat` must succeed
- **Manual test checklist**:
  - [ ] First visit (no `localStorage`): follows system `prefers-color-scheme`
  - [ ] Click toggle: theme flips immediately, no page reload
  - [ ] Refresh: theme persists from `localStorage`
  - [ ] All 6 pages render correctly in light theme (Home, Problemset, Contest, Admin, Profile, Auth)
  - [ ] ProblemSubmitPanel renders correctly in light theme
  - [ ] CodeEditor maintains correct colors in light theme
  - [ ] Native `<select>` / `<input>` controls match the theme (no white popups on dark)
  - [ ] Scrollbars match the theme
  - [ ] Login/logout keeps theme unchanged
  - [ ] Chat messages, submission results display correctly
  - [ ] System theme change while on page updates theme (if no manual override)

## Success Criteria

1. Light theme renders without visual glitches on all 6 pages
2. Theme toggle works in both directions with instant CSS-only transition (no flash)
3. Theme persists across page refreshes
4. No regressions in dark mode (identical to current)
5. No impact on auth, session, or submission business state
6. Docker build succeeds with zero new warnings

## Open Questions

- None — all decisions resolved via grill/discovery
