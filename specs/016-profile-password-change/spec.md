# Spec: 个人中心密码修改（校验旧密码）

Status: approved | Author: Hermes Agent | Date: 2026-05-20

## Objective

在个人中心提供“修改密码”能力，必须先验证旧密码，验证通过后才允许更新为新密码。

## Scope

- 后端新增密码修改接口。
- 前端个人中心新增密码修改表单。
- 保持现有登录/资料编辑流程不受影响。

## API Design

### PUT /api/profile/password

Request JSON:
- old_password: string (required)
- new_password: string (required, min length 6)

Response JSON (compat style):
- success: { "error": null, "data": "ok" }
- failure: { "error": "...", "data": "..." }

Validation rules:
1. 未登录 -> `Please login first`
2. old_password/new_password 为空 -> `Invalid password`
3. new_password 长度 < 6 -> `Invalid password`
4. old_password 校验失败 -> `Invalid old password`
5. 新旧密码一致 -> `New password must be different`

Security rules:
- 仅基于当前登录 cookie 用户修改自己的密码。
- 使用 `verify_password` 校验旧密码。
- 使用 `hash_password` 重新哈希存储新密码。
- 不返回密码哈希，不记录明文密码。

## Frontend UX

Profile 页面新增“修改密码”块：
- 字段：旧密码、新密码、确认新密码
- 提交前校验：
  - 三项必填
  - 新密码至少 6 位
  - 新密码与确认一致
- 提交成功：显示“密码修改成功”并清空密码输入
- 提交失败：显示后端错误文案

## Non-Goals

- 不做找回密码流程
- 不做多因子认证
- 不引入独立密码复杂度策略（除最小长度）

## Impact

- Backend: `ai-agent-lite/app/routers/auth.py`
- Frontend: `frontend-vue-ai-chat/src/services/apiClient.js`, `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`, `frontend-vue-ai-chat/src/pages/ProfilePage.vue`, `frontend-vue-ai-chat/src/assets/main.css`

## Verification

1. Docker 内 Python 编译通过。
2. Docker 内前端 build 通过。
3. API 冒烟：
   - 错旧密码返回失败
   - 正确旧密码返回成功
4. 本地健康检查：`/healthz` 与前端首页可访问。
