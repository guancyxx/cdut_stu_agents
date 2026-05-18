# Task Plan: 题库页管理入口下沉 + 管理页账户管理

> 依赖 Spec: `specs/012-problemset-admin-account-management/spec.md`

## Task 1 [S] 前端：题库页按钮与管理员操作入口
- 目标：将“刷新”改为“搜索”；新增仅管理员可见“新增题目”按钮。
- 验收：管理员可见按钮，普通用户不可见；搜索行为不变。
- 文件：
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`
  - `frontend-vue-ai-chat/src/assets/main.css`

## Task 2 [M] 前端：新增题目弹窗（复用旧管理页内容）
- 目标：实现 `AdminWorkspaceModal`，弹窗中承载原 `AdminPage` 的“创建比赛 + 题目管理上传”。
- 验收：点击“新增题目”后弹窗打开，功能可用。
- 文件：
  - `frontend-vue-ai-chat/src/components/AdminWorkspaceModal.vue`
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`

## Task 3 [M] 后端：题目更新 API
- 目标：新增 `PUT /admin/problems/{problem_id}` 支持更新题目字段与标签。
- 验收：管理员可更新题目并返回成功；非管理员被拒绝。
- 文件：
  - `ai-agent-lite/app/routers/problem_upload.py`
  - `ai-agent-lite/app/services/problem_service.py`

## Task 4 [M] 前端：题库题目编辑功能
- 目标：每个题目卡片新增“编辑”按钮（仅管理员），实现编辑弹窗并调用更新 API。
- 验收：保存后刷新列表，改动生效。
- 文件：
  - `frontend-vue-ai-chat/src/components/ProblemEditModal.vue`
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`
  - `frontend-vue-ai-chat/src/services/apiClient.js`

## Task 5 [L] 后端：账户管理 API（完整 CRUD）
- 目标：实现 `/admin/accounts` 列表/新增/更新/删除。
- 验收：管理员可完成 CRUD；关键限制生效（不能删自己、权限限制）。
- 文件：
  - `ai-agent-lite/app/routers/admin_accounts.py`
  - `ai-agent-lite/app/main.py`
  - `ai-agent-lite/app/utils/auth_helpers.py`（复用）

## Task 6 [M] 前端：管理页改为账户管理
- 目标：`/admin` 页面改造成账户管理 UI（列表 + 新增 + 编辑 + 删除）。
- 验收：管理员能完成账户 CRUD，错误提示清晰。
- 文件：
  - `frontend-vue-ai-chat/src/pages/AdminPage.vue`
  - `frontend-vue-ai-chat/src/services/apiClient.js`
  - `frontend-vue-ai-chat/src/assets/main.css`

## Task 7 [S] Docker 验证与回归
- 目标：构建、重启、路由/权限/功能验收。
- 验收：所有成功标准满足。
- 命令：
  - `docker compose build vue-ai-chat ai-agent-lite`
  - `docker compose up -d vue-ai-chat ai-agent-lite`

## Task 8 [S] Git 流程收尾
- 目标：提交、推送、PR、合并、同步 master、重启本地服务。
- 验收：PR 合并后本地 master 与远端一致，服务正常。