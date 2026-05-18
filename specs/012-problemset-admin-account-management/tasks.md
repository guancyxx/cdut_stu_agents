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

## Task 7 [S] Docker 验证与回归
- 目标：构建、重启、路由/权限/功能验收。
- 验收：所有成功标准满足。
- 命令：
  - `docker compose build vue-ai-chat`
  - `docker compose up -d --force-recreate vue-ai-chat`

## Task 8 [S] Git 流程收尾
- 目标：提交、推送、PR。
- 验收：提供 PR 链接与验证结果。