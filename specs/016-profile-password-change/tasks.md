# Tasks: 个人中心密码修改（校验旧密码）

Spec: `specs/016-profile-password-change/spec.md`

## Phase 1 - Backend

- [ ] 在 `auth.py` 新增 `PUT /api/profile/password`
- [ ] 使用 `verify_password` 校验旧密码
- [ ] 使用 `hash_password` 更新新密码
- [ ] 补充输入校验与错误返回

## Phase 2 - Frontend

- [ ] `apiClient.js` 增加 `updateProfilePassword`
- [ ] `useOjAuthAndProblems.js` 增加 `changeUserPassword`
- [ ] `ProfilePage.vue` 增加密码修改表单与交互
- [ ] `main.css` 增加密码表单样式

## Phase 3 - Verify & Ship

- [ ] Docker run: Python 编译验证
- [ ] Docker run: 前端构建验证
- [ ] 本地健康检查
- [ ] 提交、推送、PR、合并
- [ ] 远端部署与健康核验
