# Spec: 题库页管理入口下沉 + 管理页改为账户管理

## Objective

本次改造目标：

1. 题库页面将“刷新”按钮改名为“搜索”。
2. 题库页面新增“新增题目”按钮（仅管理员可见）。点击后以弹窗形式展示当前“管理页”已有内容（题目管理 + 创建比赛）。
3. 题库列表每个题目增加“编辑”按钮（仅管理员可见），支持编辑并保存题目。
4. 路由 `/admin` 页面从“题目管理页”改为“账户管理页”，实现对系统账号（`ai_agent.local_users`）的完整管理能力。
5. 题库页“新增题目”弹窗移除“Create Contest”入口；编辑题目与新增单题复用同一表单组件与字段结构。
6. 弹窗视觉精简：去除不必要标题，仅保留必要关闭与操作按钮，保持简洁一致。
7. 题库列表中每个题目卡片需支持“整卡可点击进入题目”，而非仅局部区域可点击。
8. 全站滚动条视觉需统一：使用统一的滚动条样式工具类，避免同页出现隐藏/细条/不同配色混用。
9. 题库页点击题目卡片进入主页会话时，必须自动把该题目的结构化上下文消息发送给 AI（含题号、标题、难度、题面），且目标会话必须与所选题目会话一致。

## Scope

### In scope
- 前端：`ProblemsetPage.vue`、`AdminPage.vue`、`apiClient.js`、必要组件与样式。
- 后端：新增账号管理 API；扩展题目管理 API 支持更新题目。
- 权限：所有管理操作需 `admin_type >= 1`。

### Out of scope
- 不改数据库 schema。
- 不新增 Docker 服务。
- 不调整现有登录认证协议（保持 cookie + session）。

## Tech Stack

- Frontend: Vue 3 + Vite
- Backend: FastAPI (ai-agent-lite)
- DB: PostgreSQL（`ai_agent.local_users` + `problem` 相关表）

## Current State

- `ProblemsetPage.vue` 现有操作按钮为“刷新”。
- 现有 `AdminPage.vue` 内容是“创建比赛 + 题目管理上传组件”。
- 账号管理 API 不存在。
- 题目更新 API 不存在（仅创建与批量导入）。

## Design

### A. Problemset 页面改造

1) 将工具栏按钮文本“刷新”改为“搜索”。
2) 新增管理员操作区：
   - `新增题目` 按钮：打开 `AdminWorkspaceModal`，内容复用原 `AdminPage`（`ContestCreateModal` + `AdminProblemUpload`）。
3) 每个题目卡片增加 `编辑` 按钮（仅管理员可见）：
   - 打开 `ProblemEditModal`。
   - 弹窗加载题目详情并允许编辑核心字段。
   - 保存后调用后端更新 API，成功后刷新题库列表。
4) 新增/编辑表单一致性：
   - `新增单题` 与 `编辑题目` 使用同一份字段定义与组件结构（标题、难度、来源、描述、输入输出、提示、标签、样例、测试数据、模板代码、SPJ、可见性）。
   - 通过 `mode=create|edit` 切换提交行为，不允许两套独立字段实现继续分叉。
5) 弹窗极简规范：
   - 去除内容区冗余标题（如“新增题目 / 题目管理”“题目管理”等重复文案）。
   - 保留关闭按钮和底部操作按钮；减少视觉噪音。
6) 题目卡片交互规范：
   - 题库页每个题目卡片（`.problem-item`）整体区域可点击，点击后进入题目会话。
   - 管理员“编辑”按钮作为卡片内独立操作，需阻止事件冒泡，避免触发进入题目。
7) 滚动条统一规范：
   - 在全局样式中定义统一滚动条工具类（例如 `.scrollbar-unified`）。
   - `problem-list / problem-detail-middle / submit-result-area / session-list / chat-main` 等滚动容器统一使用该样式。
   - 不再对同类容器混用“隐藏滚动条”和“细滚动条”两套方案。

### D. UI 约束（本次新增）

- `AdminWorkspaceModal` 内不显示 `Create Contest` 按钮。
- `ContestCreateModal` 不在“新增题目”入口链路中出现。
- 编辑弹窗标题改为简洁风格（不显示冗余前缀与 ID 拼接文案）。

### B. 管理页面重构

`/admin` 对应 `AdminPage.vue` 改为“账户管理页面”：

- 账号列表（用户名、邮箱、学号、管理员等级、创建时间）。
- 新增账号（用户名、密码、邮箱、学号、管理员等级）。
- 编辑账号（邮箱、学号、管理员等级、可选重置密码）。
- 删除账号（禁止删除当前登录账号；保留至少一个管理员）。

### C. 后端 API 设计

#### 1) 题目更新

- `PUT /admin/problems/{problem_id}`
- 权限：`admin_type >= 1`
- 支持更新字段：
  - `title, description, input_description, output_description`
  - `hint, source, difficulty, time_limit, memory_limit`
  - `visible, tags`
- 返回：`{ success, message, problem_id }`

#### 2) 账户管理

- `GET /admin/accounts`
- `POST /admin/accounts`
- `PUT /admin/accounts/{username}`
- `DELETE /admin/accounts/{username}`

权限规则：
- 所有接口需管理员。
- 创建/编辑时 `admin_type` 仅允许 `0/1/2`。
- 普通 Admin（1）不能将他人提升为 Super Admin（2）。
- 不允许删除当前登录账号。

## Frontend API Client Extension

在 `frontend-vue-ai-chat/src/services/apiClient.js` 增加：
- `adminUpdateProblem(problemId, payload)`
- `adminListAccounts()`
- `adminCreateAccount(payload)`
- `adminUpdateAccount(username, payload)`
- `adminDeleteAccount(username)`

## Validation Plan

全部走 Docker 验证：

1. `docker compose build vue-ai-chat ai-agent-lite`
2. `docker compose up -d vue-ai-chat ai-agent-lite`
3. 路由与权限检查：
   - 普通用户：看不到题库“新增题目/编辑”按钮，`/admin` 被拦截。
   - 管理员：可见并可操作。
4. 功能回归：
   - 题库“搜索”按钮工作正常。
   - 新增题目弹窗可打开且复用旧管理内容。
   - 编辑题目保存成功，题库刷新可见。
   - 账户 CRUD 流程完整可用。
   - 题库点击题目后跳转到主页，会话中可观察到题目上下文已注入（无用户额外输入也能看到上下文加载行为）。

## Known Gaps (2026-05-19 audit)
1. Account management API and UI exist, but flow safeguards still need explicit contract confirmation in spec:
   - create/edit/delete success/error feedback consistency;
   - loading-state button disable and optimistic reset behavior;
   - non-super-admin privilege escalation guard is UI-enforced and must remain backend-enforced.
2. Light theme mismatch remains for key account form controls (input/select background hardcoded dark).
3. Account operation path lacks explicit verification checklist for full CRUD + permission boundary matrix.

## Additional Acceptance Criteria (this round)
1. Account create/edit/delete must each provide deterministic success/error message and refresh list once.
2. Delete flow must keep guards:
   - cannot delete current login account;
   - backend must keep at least one super admin (already required, verify regression).
3. Admin type privilege rules remain dual-enforced (frontend + backend).
4. Account form controls must be fully theme-token based; no dark hardcode.
5. Verification matrix must include:
   - super admin creates admin/user;
   - admin cannot create/promote super admin;
   - self-delete blocked;
   - CRUD happy path under docker runtime.

## Success Criteria

1. 题库页面按钮文案变更为“搜索”。
2. 管理员可在题库页面打开“新增题目”弹窗并执行原管理操作。
3. 管理员可对题目执行编辑并保存。
4. `/admin` 页面完成账户管理能力并可稳定使用。
5. 所有变更通过 Docker 构建、运行、接口与页面验证。
6. 账户管理流程通过权限矩阵验证，且主题样式在亮色模式下无暗底输入控件。