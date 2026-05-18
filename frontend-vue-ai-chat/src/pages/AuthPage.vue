<script setup>
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'

const { AUTH_MODES, authMode, authUsernameRef, ojUser, isLoginMode, refreshCaptcha, login, register } = useOjStore()
const { switchToUser, loadSessions } = useChatStore()

const handleAuthSubmit = async () => {
  if (isLoginMode.value) {
    await login()
  } else {
    await register()
  }
  if (ojUser.value.loggedIn) {
    switchToUser(ojUser.value.profileName || ojUser.value.username)
  }
}

const handleAuthKeydown = (event) => {
  if (event.key === 'Enter') {
    event.preventDefault()
    handleAuthSubmit()
  }
}
</script>

<template>
  <div class="auth-screen">
    <div class="auth-page card">
      <div class="auth-page-header">
        <div class="auth-brand-icon">
          <img src="/logo.svg" alt="CDUT AI" style="width:56px;height:56px;" />
        </div>
        <h2>登录 OJ 账号</h2>
        <p>请先完成登录或注册后继续使用题库和聊天功能</p>
      </div>

      <div class="auth-switch-row">
        <button :class="{ active: authMode === AUTH_MODES.LOGIN }" @click="authMode = AUTH_MODES.LOGIN">登录</button>
        <button :class="{ active: authMode === AUTH_MODES.REGISTER }" @click="authMode = AUTH_MODES.REGISTER">注册</button>
      </div>

      <div class="auth-form auth-page-form" @keydown="handleAuthKeydown">
        <input ref="authUsernameRef" v-model="ojUser.username" placeholder="用户名" autocomplete="username" />
        <input v-model="ojUser.password" placeholder="密码" type="password" autocomplete="current-password" />

        <template v-if="authMode === AUTH_MODES.REGISTER">
          <input v-model="ojUser.email" placeholder="邮箱（选填）" type="email" autocomplete="email" />
          <input v-model="ojUser.studentNumber" placeholder="学号（选填）" autocomplete="off" />
          <div class="captcha-row">
            <input v-model="ojUser.captcha" placeholder="验证码" autocomplete="off" />
            <img v-if="ojUser.captchaSrc" :src="ojUser.captchaSrc" alt="captcha" @click="refreshCaptcha" title="点击刷新验证码" />
          </div>
        </template>

        <button class="auth-submit-btn" @click="handleAuthSubmit">
          {{ authMode === AUTH_MODES.LOGIN ? '登录 OJ' : '注册 OJ' }}
        </button>
        <div class="error" v-if="ojUser.error">{{ ojUser.error }}</div>
      </div>
    </div>
  </div>
</template>
