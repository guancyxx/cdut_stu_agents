# Tasks: 个人中心可编辑 + 排行榜签名展示 + 竞赛化分页榜单

Spec: `specs/015-profile-rank-enhancement/spec.md`

## Phase 1: API & 数据准备

- [ ] Task 1: 扩展 profile 查询与更新接口（含 signature）
  - Files:
    - `ai-agent-lite/app/routers/auth.py`

- [ ] Task 2: 扩展 contest rank 返回用户签名字段
  - Files:
    - `ai-agent-lite/app/routers/contests.py`

## Phase 2: 前端数据层

- [ ] Task 3: API Client 新增 updateProfile
  - Files:
    - `frontend-vue-ai-chat/src/services/apiClient.js`

- [ ] Task 4: OJ Store 新增 updateUserProfile 方法并暴露
  - Files:
    - `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`

## Phase 3: 页面与交互

- [ ] Task 5: ProfilePage 增加编辑态/保存/取消交互
  - Files:
    - `frontend-vue-ai-chat/src/pages/ProfilePage.vue`

- [ ] Task 6: ContestPage 榜单点击用户名显示签名 + 分页逻辑
  - Files:
    - `frontend-vue-ai-chat/src/pages/ContestPage.vue`

- [ ] Task 7: 排行榜竞赛化样式升级
  - Files:
    - `frontend-vue-ai-chat/src/assets/main.css`

## Phase 4: 验证与交付

- [ ] Task 8: Docker build + up + 接口/页面验收
- [ ] Task 9: 提交、推送、PR