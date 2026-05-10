# Task Plan: 管理员题目上传功能

> 依赖 Spec: `specs/002-admin-problem-upload/spec.md`

## 任务分解

### Task 1: [S] 后端 — 批量上传路由骨架 + 文件解析
- **接收标准**: ai-agent-lite 新增 `POST /admin/problems/upload/batch` 和 `GET /admin/problems/upload/status/:id`，返回正确的 FastAPI 路由结构
- **验证**: `curl -X POST .../upload/batch` 返回 422（缺少文件参数）而非 404
- **文件**: `ai-agent-lite/app/routers/problem_upload.py`, `ai-agent-lite/app/main.py`
- **依赖**: 无

### Task 2: [M] 后端 — FPS XML 和 Hydro ZIP 解析器
- **接收标准**: `problem_import.py` 能解析 FPS XML 文件和 Hydro ZIP 目录，输出标准化的题目列表
- **验证**: 用小型测试数据运行解析逻辑，确认输出字段完整（title, description, input, output, samples, tags, difficulty, test_cases）
- **文件**: `ai-agent-lite/app/services/problem_import.py`
- **依赖**: 无（可与 Task 1 并行）

### Task 3: [M] 后端 — 三阶段 QDUOJ Admin API 导入器
- **接受标准**: 实现 create → upload test cases → update 三阶段导入流程，使用 ai-agent-lite 的 OJ_API_URL/OJ_ADMIN_PASS 配置
- **验证**: 用 1 道测试题目走完三阶段，确认题目在 OJ 中可搜索到
- **文件**: `ai-agent-lite/app/services/problem_import.py`（扩展）
- **依赖**: Task 2

### Task 4: [S] 后端 — 批量上传任务调度 + 进度追踪
- **接受标准**: POST 上传文件后返回 task_id，轮询 status 接口返回实时进度（imported/skipped/failed）
- **验证**: 上传 5 题的 FPS XML，轮询 status 接口确认进度更新
- **文件**: `ai-agent-lite/app/routers/problem_upload.py`（扩展）
- **依赖**: Task 1, Task 3

### Task 5: [S] 前端 — apiClient.js 添加 Admin API 方法
- **接受标准**: 新增 `createProblem()`, `uploadTestCase()`, `updateProblem()`, `fetchProfile()`（如需扩展）方法
- **验证**: 单元级 — 调用方法确认请求路径和参数格式正确
- **文件**: `frontend-vue-ai-chat/src/services/apiClient.js`
- **依赖**: 无

### Task 6: [S] 前端 — useOjAuthAndProblems.js 扩展 admin 判断
- **接受标准**: 导出 `isAdmin` computed 属性，基于 `admin_type >= 1` 为 true
- **验证**: 管理员登录后 `isAdmin` 为 true，普通用户为 false
- **文件**: `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
- **依赖**: Task 5

### Task 7: [L] 前端 — AdminProblemUpload.vue 单题上传表单
- **接受标准**: 表单包含所有必要字段（title, difficulty, source, description, input_description, output_description, samples, hint, tags, test_case ZIP），提交后走三阶段创建流程
- **验证**: 填写表单提交，在 OJ 题库中搜索到新创建的题目且字段完整
- **文件**: `frontend-vue-ai-chat/src/components/AdminProblemUpload.vue`
- **依赖**: Task 5, Task 6

### Task 8: [L] 前端 — AdminProblemUpload.vue 批量导入面板
- **接受标准**: 用户可选择文件格式（FPS/Hydro），上传 ZIP/XML，查看进度条和导入结果
- **验证**: 上传小型 FPS XML 文件，确认导入成功并显示进度
- **文件**: `frontend-vue-ai-chat/src/components/AdminProblemUpload.vue`（扩展）
- **依赖**: Task 4, Task 7

### Task 9: [S] 前端 — App.vue 集成管理 Tab
- **接受标准**: 管理员登录后可见 "管理" Tab，点击切换到 AdminProblemUpload 组件；非管理员不可见
- **验证**: 管理员登录 → 看到 Tab → 点击进入管理页面；普通用户 → 无 Tab
- **文件**: `frontend-vue-ai-chat/src/App.vue`
- **依赖**: Task 6, Task 7

### Task 10: [S] 集成测试 — 端到端验证
- **接受标准**: 完整流程走通（管理员登录 → 创建单题 → 搜索确认 → 批量导入 → 进度查询 → 导入结果确认）
- **验证**: 在运行中的 Docker 环境中操作完整流程
- **文件**: 无新文件，使用已有环境
- **依赖**: Task 9, Task 8

## 检查点

- **Checkpoint 1** (Task 4 完成): 后端批量导入可独立测试
- **Checkpoint 2** (Task 7 完成): 单题上传端到端可用
- **Checkpoint 3** (Task 10 完成): 全功能端到端验证通过

## 任务依赖图

```
Task 1 ─────┐
Task 2──Task 3──Task 4──┐
                                │
Task 5──Task 6──────────┤
                         │
                    Task 7──Task 8──Task 9──Task 10
```

关键路径: Task 2 → 3 → 4 → 8 → 10（批量导入链）