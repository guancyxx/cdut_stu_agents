# Task Plan: 题库页管理入口下沉 + 管理页账户管理

> 依赖 Spec: `specs/012-problemset-admin-account-management/spec.md`

## Task 1 [S] 前端：题库页按钮与管理员操作入口
- 目标：将“刷新”改为“搜索”；新增仅管理员可见“新增题目”按钮。
- 验收：管理员可见按钮，普通用户不可见；搜索行为不变。
- 文件：
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`
  - `frontend-vue-ai-chat/src/assets/main.css`

## Task 2 [M] 前端：新增题目弹窗（去除比赛入口 + 精简）
- 目标：实现 `AdminWorkspaceModal` 极简弹窗，仅承载题目管理能力，不包含创建比赛入口。
- 验收：点击“新增题目”后弹窗打开，弹窗内无 `Create Contest` 按钮，标题区域简洁。
- 文件：
  - `frontend-vue-ai-chat/src/components/AdminWorkspaceModal.vue`
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`

## Task 3 [L] 前端：单题新增/编辑复用同一表单组件
- 目标：抽取复用组件承载单题表单，供“新增单题”和“编辑题目”共同使用。
- 验收：新增与编辑字段项一致；两者仅提交行为差异（create/update）。
- 文件：
  - `frontend-vue-ai-chat/src/components/ProblemFormFields.vue`（新增）
  - `frontend-vue-ai-chat/src/components/AdminProblemUpload.vue`
  - `frontend-vue-ai-chat/src/components/ProblemEditModal.vue`

## Task 4 [M] 后端：题目更新 API
- 目标：确认 `PUT /admin/problems/{problem_id}` 已可用并与前端复用表单对齐。
- 验收：管理员可更新题目并返回成功；非管理员被拒绝。
- 文件：
  - `ai-agent-lite/app/routers/problem_upload.py`（如需）
  - `ai-agent-lite/app/services/problem_service.py`（如需）

## Task 5 [S] 前端：题库题目编辑入口联动
- 目标：保留题库卡片“编辑”入口，接入复用表单的编辑模式。
- 验收：保存后刷新列表，改动生效。
- 文件：
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`
  - `frontend-vue-ai-chat/src/components/ProblemEditModal.vue`

## Task 6 [S] 前端：题目卡片整块可点击 + 滚动条样式统一
- 目标：题库题目卡片整块可点击；统一主要滚动容器视觉滚动条样式。
- 验收：
  - 点击题目卡片任意非按钮区域均可进入题目。
  - 管理员编辑按钮点击仅触发编辑，不触发选题。
  - `problem-list / problem-detail-middle / submit-result-area / session-list / chat-main` 滚动条样式一致。
- 文件：
  - `frontend-vue-ai-chat/src/pages/ProblemsetPage.vue`
  - `frontend-vue-ai-chat/src/assets/main.css`

## Task 7 [S] 账户管理流程细化（状态反馈与权限边界）
- 目标：确保账户 CRUD 在 UI 反馈、按钮状态、权限边界上行为一致。
- 验收：
  - create/edit/delete 均有明确 success/error 提示。
  - 提交中按钮禁用，完成后状态恢复。
  - 普通管理员无法创建/提升 super admin（前后端双重约束）。
- 文件：
  - `frontend-vue-ai-chat/src/pages/AdminPage.vue`
  - `ai-agent-lite/app/routers/admin_accounts.py`（仅在需要修补后端约束时）

## Task 8 [S] 账户管理表单亮色主题修复
- 目标：修复账户管理表单在亮色主题下暗底输入框。
- 验收：`email/student_number/admin_type` 输入控件使用主题变量，不再硬编码暗色背景。
- 文件：
  - `frontend-vue-ai-chat/src/assets/main.css`

## Task 9 [S] Docker 验证与回归
- 目标：构建、重启、路由/权限/功能验收。
- 验收：所有成功标准满足，覆盖账户权限矩阵。
- 命令：
  - `docker compose build vue-ai-chat ai-agent-lite`
  - `docker compose up -d --force-recreate vue-ai-chat ai-agent-lite`

## Task 10 [S] Git 流程收尾
- 目标：提交、推送、PR。
- 验收：提供 PR 链接与验证结果。

## Task 11 [M] 账户管理新增弹窗与快捷操作（2026-05-20）
- 目标：将新增账号改为按钮 + 弹窗，并补齐账号列表状态、启用/禁用、修改密码快捷操作。
- 验收：
  - 新增账号表单不再常驻页面，点击“新增账号”打开弹窗。
  - 账号列表显示启用/禁用状态；无数据时显示清晰空态。
  - 每行提供编辑、修改密码、禁用/启用、删除快捷按钮。
  - `PATCH /admin/accounts/{username}/status` 和 `PATCH /admin/accounts/{username}/password` 不返回 404。
  - 当前登录账号不能被禁用/删除；最后一个可用管理员不能被禁用/删除。
- 文件：
  - `frontend-vue-ai-chat/src/pages/AdminPage.vue`
  - `frontend-vue-ai-chat/src/services/apiClient.js`
  - `frontend-vue-ai-chat/src/assets/main.css`
  - `ai-agent-lite/app/routers/admin_accounts.py`
  - `ai-agent-lite/app/routers/auth.py`
  - `ai-agent-lite/app/utils/auth_helpers.py`
  - `ai-agent-lite/app/database.py`
  - `ai-agent-lite/app/models/local_user.py`
