# Spec: 个人中心页面重排（企业平台风格）

Status: approved
Author: Hermes Agent
Date: 2026-05-20

## Objective

在保持现有资料编辑与密码修改能力不回退的前提下，对个人中心进行企业平台级重排：
- 顶部品牌卡（身份信息 + 关键操作）
- 左侧固定导航（资料 / 安全 / 个性化 / 竞赛）
- 右侧分区内容（首屏默认突出账号信息）

目标风格参考：GitHub/Linear/Ant Design Pro 的信息层级与后台质感，避免花哨营销风。

## User Requirements Mapping

1) “个人中心重新排版设计”
- 采用双栏骨架：左导航 + 右内容。

2) “参考大公司/平台处理方式”
- 使用统一卡片、清晰层级、可扫描模块分组、显式主操作。

3) 既有功能保持
- 资料编辑、签名编辑、旧密码校验修改密码保持可用。

## Scope

### In Scope
- 仅改 `ProfilePage.vue` 的结构与交互组织。
- 新增/调整 `main.css` 中 profile 相关样式。
- 轻量新增竞赛统计展示（基于现有 store 数据可得项，避免新增后端接口）。

### Out of Scope
- 不改后端 API。
- 不新增头像上传接口。
- 不改登录/注册流程。

## Architecture / Layout

### 1. 顶部品牌卡（Hero Card）
- 左侧：头像/首字母头像、用户名、角色标签、邮箱。
- 右侧：快捷按钮（返回主页、编辑资料、退出登录）。
- 次级信息：个性签名（摘要展示）。

### 2. 左侧固定导航（Section Nav）
- 导航项：
  - account（账号信息）
  - security（安全设置）
  - personalization（个性化）
  - contest（竞赛数据）
- 点击切换右侧分区，不路由跳转（页面内切换）。
- 当前项高亮。

### 3. 右侧分区内容（Section Panels）
- account：用户名/邮箱/学号/角色信息卡。
- security：旧密码校验改密表单。
- personalization：签名查看与编辑入口。
- contest：前端可得统计（如登录态、管理员标识、资料完整度等轻量指标）+ 最近动作提示。

## Interaction Rules

- 首次进入默认选中 account。
- 编辑资料时，保持与现有 save/cancel 逻辑一致。
- 改密码与资料编辑状态互不覆盖（消息区分）。
- 窄屏（<=900px）下导航变为横向可滚动 tabs，右侧单列。

## Data / API

- 继续复用现有 store 字段：`ojUser.username/email/studentNumber/signature/adminType/loggedIn`。
- 继续复用现有操作：`updateUserProfile`, `changeUserPassword`, `logout`。
- 不新增 API 调用。

## Files

- `frontend-vue-ai-chat/src/pages/ProfilePage.vue`
- `frontend-vue-ai-chat/src/assets/main.css`

## Acceptance Criteria

1. 页面结构为“顶部品牌卡 + 左导航 + 右内容区”。
2. 默认首屏突出账号信息区块。
3. 资料编辑功能可用（保存/取消/校验不回退）。
4. 修改密码功能可用且仍需旧密码校验。
5. 个性签名可展示并编辑。
6. 样式在桌面和窄屏下均保持可用（无布局塌陷）。
7. Docker 前端构建通过，服务重建后可访问。

## Risks & Mitigation

- 风险：大改模板导致样式冲突。
  - 缓解：新增 profile-v2 命名空间样式，减少影响面。
- 风险：交互状态互相覆盖。
  - 缓解：资料与密码状态分离，消息独立变量。

## Verification

- `docker compose run --rm --no-deps vue-ai-chat npm run build`
- `docker compose up -d --force-recreate vue-ai-chat`
- `curl http://127.0.0.1:5173` 返回 HTML
