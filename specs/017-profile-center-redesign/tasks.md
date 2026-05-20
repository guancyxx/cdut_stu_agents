# Tasks: 个人中心页面重排（企业平台风格）

Spec: `specs/017-profile-center-redesign/spec.md`

## Phase 1 - 结构改造

- [ ] T1: 重构 ProfilePage 为 Hero + Nav + Section 三层结构
  - Acceptance: 页面主骨架完成，默认 account 分区
  - Verify: 本地运行后页面无模板错误

## Phase 2 - 功能保持

- [ ] T2: 迁移现有资料编辑逻辑到 account/personalization 分区
  - Acceptance: 保存/取消/提示行为与原功能等价
  - Verify: build + 手工触发表单操作

- [ ] T3: 迁移现有改密逻辑到 security 分区
  - Acceptance: 旧密码校验链路不回退
  - Verify: build + 接口调用路径不变

## Phase 3 - 样式升级

- [ ] T4: 新增 profile-v2 样式（品牌卡/左导航/内容卡/响应式）
  - Acceptance: 桌面双栏，窄屏单栏 tabs
  - Verify: 构建通过，关键 class 生效

## Phase 4 - 验证与发布

- [ ] T5: Docker 构建与容器重建验证
  - Verify: `docker compose run --rm --no-deps vue-ai-chat npm run build`
  - Verify: `docker compose up -d --force-recreate vue-ai-chat`

- [ ] T6: 提交 PR 并合并，远端部署核验
  - Acceptance: PR merged + 远端 health 与页面可访问
