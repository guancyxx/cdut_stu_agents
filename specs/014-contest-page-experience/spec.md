# Spec: Contest Page Experience Refresh + Light Theme Texture

Status: approved | Author: Hermes Agent | Date: 2026-05-19

## Objective

Implement a full UX refresh for the contest page and refine light theme texture quality.

1. Light theme visual polish: reduce pale/flat feel while preserving readability and consistency.
2. Contest page admin action update:
   - Replace list-header "刷新" with "新增比赛" (admin-only).
   - Clicking opens create modal.
3. Create contest modal structure:
   - Two tabs: "比赛信息" and "题目信息".
   - Problem tab uses two-column layout:
     - Left: selected problem cards (vertical list).
     - Right: card-grid problem browser with filters and circular selector.
4. Contest list redesign:
   - Vertical contest cards sorted by time descending.
   - Card actions: 详情 (modal, no problem details), 报名/参加.
   - Contest list supports collapse/expand.
5. Contest main area redesign:
   - Non-list area treated as one composite workspace.
   - No selected contest: inspirational empty state page.
   - Selected contest: split layout (left contest info/workspace, right leaderboard).
   - Contest info panel:
     - Upper: contest details (collapsible).
     - Lower: participation area.
       - Before start: countdown.
       - Running: split two columns:
         - Left: vertical problem cards.
         - Right: submit area, reuse existing OJ submit interaction style.

## Scope

### In scope

- `frontend-vue-ai-chat/src/pages/ContestPage.vue`
- `frontend-vue-ai-chat/src/components/ContestCreateModal.vue`
- `frontend-vue-ai-chat/src/assets/main.css`
- `specs/004-oj-contest-mvp/spec.md` (alignment update)
- `specs/004-oj-contest-mvp/tasks.md` (task alignment)

### Out of scope

- Backend contest API contract changes.
- Ranking rule changes.
- Non-contest pages structural redesign.

## UX Rules

1. Admin-only create entry:
   - Student view must not show create button.
2. Contest card actions:
   - 详情 opens detail modal that excludes problem-level details.
   - 报名/参加 follows existing lifecycle gate and join rules.
3. Submit panel reuse:
   - Reuse current contest submit logic and editor behavior.
   - No change in submission payload contract.
4. Collapse behavior:
   - Contest list collapse only affects list column visibility.
   - Main workspace remains functional.
5. Sorting:
   - Contest list sorted by `start_time` desc (fallback `created_at` desc).

## Light Theme Texture Requirements

1. Keep semantic tokens as source of truth.
2. Improve depth in light mode by adjusting:
   - panel/surface contrast,
   - subtle gradients,
   - shadows and border definition.
3. Avoid hardcoded dark literals in newly added contest styles.
4. Maintain dark mode parity.

## Acceptance Criteria

1. Contest list header uses admin-only "新增比赛" action (no refresh button).
2. Create modal has two tabs and two-column problem selection area with card-grid + circular selector.
3. Contest cards show details and join actions; list supports collapse.
4. Empty inspirational state shown when no contest selected.
5. Selected contest view shows left contest workspace + right leaderboard.
6. Contest details panel is collapsible.
7. Pre-start shows countdown; running shows problem list + submit area split.
8. Light mode visuals are less pale and visibly layered while preserving readability.
9. Docker frontend build succeeds.
10. OJ 提交区的编辑器与提交按钮必须是上下两排布局，按钮不得与编辑器同排。
11. OJ 提交区编辑器在任意断点下不得超出父容器宽度。
12. 亮色主题下编辑题目弹窗不得出现暗色背景，需跟随主题变量。
13. 折叠操作按钮必须位于区域最右侧，采用图标按钮形态。
14. 比赛卡片需要提升信息层级与排版，整卡可点击，操作按钮固定在右上角并同排显示。
15. 赛题区在比赛进行中需撑满可用高度，题目列表必须采用卡片式并支持整卡点击。
16. 比赛进行中右侧区域需同时展示代码编辑区与 OJ 提交结果区，并共同撑满父容器。
17. 比赛卡片、赛题卡片与折叠图标按钮需要具备清晰的 hover/focus-visible/active 微交互反馈。
18. 键盘导航到整卡可点击元素时，需有可见焦点态，不得仅依赖浏览器默认样式。
19. 比赛页交互动效时长与缓动曲线需通过统一 motion tokens 管理，避免同类组件各自定义。
20. 比赛卡片、赛题卡片、折叠图标按钮与比赛卡片操作按钮需使用同一动效节奏体系。
21. 新增比赛弹窗的题目信息卡片必须清晰显示题目标题：标题对比度满足可读性，支持至少两行展示并在超长时安全截断。
22. 比赛页面在桌面端与常见笔记本视口下，除顶部导航外的内容区需动态撑满可用高度，不得出现主工作区塌陷。
23. 比赛提交链路需正确传递比赛题目标识，参赛中提交不得因 `Problem not in contest` 的前后端字段不一致而失败。

## Verification

- Docker-only build:
  - `docker compose build vue-ai-chat`
- Static checks:
  - contest list action visibility by `isAdmin`.
  - create modal tab switch state and problem selection state.
  - contest selection drives empty-state/workspace switching.
- UI behavior smoke (manual):
  - collapse list,
  - open detail modal,
  - join action gating,
  - countdown + running workspace render,
  - card/button hover/focus-visible/active interaction checks,
  - motion token consistency checks for key interactive elements.

## Risks

1. Large template/CSS refactor can break responsive layout.
2. Existing submit flow might regress if state coupling is altered.

## Mitigations

1. Keep submission methods and payload untouched.
2. Keep existing computed state gates and reuse them in new layout.
3. Build and grep verification before commit.
