# Spec: 个人中心可编辑 + 排行榜签名展示 + 竞赛化分页榜单

Status: approved | Author: Hermes Agent | Date: 2026-05-20

## Objective

实现以下三项：

1. 个人中心支持显示并修改个人信息，重点支持“个性签名”可编辑。
2. 比赛排行榜中点击用户名可查看该用户个性签名。
3. 比赛排行榜重做排版样式，突出竞赛氛围，并支持分页展示。

## Scope

### In scope

- 后端：
  - `ai-agent-lite/app/routers/auth.py`
  - `ai-agent-lite/app/routers/contests.py`
- 前端：
  - `frontend-vue-ai-chat/src/services/apiClient.js`
  - `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
  - `frontend-vue-ai-chat/src/pages/ProfilePage.vue`
  - `frontend-vue-ai-chat/src/pages/ContestPage.vue`
  - `frontend-vue-ai-chat/src/assets/main.css`

### Out of scope

- 不修改登录认证协议（保持 cookie + session）。
- 不新增独立服务。

## API Contract Changes

### 1) Profile 更新接口

新增：`PUT /api/profile`

请求体：
- `email` (optional, string)
- `student_number` (optional, string)
- `signature` (optional, string, max 280)

行为：
- 需登录。
- 仅更新当前登录用户。
- 返回更新后的 profile 数据。

兼容：
- `GET /api/profile` 增加返回 `signature` 字段（若无则空串）。

### 2) Contest Rank 签名字段

`GET /api/contest/rank?contest_id=...` 返回每行附加：
- `signature` (string)

兼容：
- 保持既有字段 `rank/user_id/solved_count/penalty_time_ms/joined_at` 不变。

## Frontend Behavior

### A. 个人中心（ProfilePage）

1. 页面显示：用户名、邮箱、学号、个性签名。
2. 提供“编辑资料”入口，进入编辑态后可修改：
   - 邮箱
   - 学号
   - 个性签名
3. 保存后：
   - 调用 `PUT /api/profile`
   - 成功提示并刷新 store 中用户信息
4. 取消编辑回滚本地草稿。

### B. 排行榜用户名可点签名

1. 用户名渲染为可点击按钮（非纯文本）。
2. 点击后弹出签名浮层（轻量 modal/popover），显示：
   - 用户名
   - 个性签名（为空时显示“该用户暂未设置签名”）

### C. 排行榜竞赛化重排 + 分页

1. 排行榜头部增加竞赛风格视觉区（标题、状态提示、统计）。
2. 榜单行强化层级：
   - 排名徽章（Top3 特殊视觉）
   - 用户名主信息
   - 通过题数 / 罚时副信息
3. 分页规则：
   - 默认每页 10 条
   - 上一页 / 下一页 / 页码信息
   - 切换比赛或刷新榜单时页码回到第 1 页

## Validation Plan (Docker)

1. 构建：
- `docker compose build ai-agent-lite vue-ai-chat`

2. 启动：
- `docker compose up -d --force-recreate ai-agent-lite vue-ai-chat`

3. 验证：
- 已登录用户可在个人中心保存签名并刷新后保持。
- `/api/profile` 返回 `signature`。
- 排行榜点击用户名可看到签名。
- 排行榜分页可用，切页数据正确。
- 样式在亮/暗主题均可读。

## Acceptance Criteria

1. 个人中心支持编辑并保存个性签名。
2. 比赛排行榜点击用户名可查看该用户个性签名。
3. 比赛排行榜完成竞赛化视觉升级并支持分页。
4. 变更通过 Docker 构建与运行验证。