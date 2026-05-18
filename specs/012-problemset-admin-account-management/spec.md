# Spec: 题库页管理入口下沉 + 管理页改为账户管理

## Objective

本次改造目标：

1. 题库页面将“刷新”按钮改名为“搜索”。
2. 题库页面新增“新增题目”按钮（仅管理员可见）。点击后以弹窗形式展示当前“管理页”已有内容（题目管理 + 创建比赛）。
3. 题库列表每个题目增加“编辑”按钮（仅管理员可见），支持编辑并保存题目。
4. 路由 `/admin` 页面从“题目管理页”改为“账户管理页”，实现对系统账号（`ai_agent.local_users`）的完整管理能力。

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

## Success Criteria

1. 题库页面按钮文案变更为“搜索”。
2. 管理员可在题库页面打开“新增题目”弹窗并执行原管理操作。
3. 管理员可对题目执行编辑并保存。
4. `/admin` 页面完成账户管理能力并可稳定使用。
5. 所有变更通过 Docker 构建、运行、接口与页面验证。