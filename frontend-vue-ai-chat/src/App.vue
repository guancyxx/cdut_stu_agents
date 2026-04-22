<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useChatFeature } from './composables/useChatFeature'
import { AUTH_MODES, OJ_DIFFICULTY_OPTIONS } from './utils/validators'
import { useOjAuthAndProblems } from './composables/useOjAuthAndProblems'

const activeTab = ref('home')

const {
  input,
  listRef,
  sending,
  sessions,
  currentSessionId,
  messages,
  createSession,
  loadSessions,
  selectSession,
  sendMessage,
  closeSocket
} = useChatFeature()

const {
  authMode,
  showAuthModal,
  authUsernameRef,
  ojUser,
  problems,
  problemLoading,
  problemError,
  keyword,
  difficulty,
  isLoginMode,
  openAuthModal,
  closeAuthModal,
  refreshCaptcha,
  login,
  register,
  fetchProblems
} = useOjAuthAndProblems()

const authActionText = computed(() => (ojUser.value.loggedIn ? ojUser.value.profileName : '登录 / 注册'))

const openAuth = async () => {
  await openAuthModal(nextTick)
}

const handleAuthSubmit = async () => {
  if (isLoginMode.value) {
    await login()
    return
  }
  await register()
}

const handleGlobalKeydown = (event) => {
  if (event.key === 'Escape' && showAuthModal.value) {
    closeAuthModal()
  }
}

watch(showAuthModal, (visible) => {
  document.body.style.overflow = visible ? 'hidden' : ''
})

onMounted(async () => {
  loadSessions()
  await refreshCaptcha()
  await fetchProblems()
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  closeSocket()
  window.removeEventListener('keydown', handleGlobalKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="app-shell">
    <header class="top-nav">
      <div class="tabs">
        <button :class="{ active: activeTab === 'home' }" @click="activeTab = 'home'">主页</button>
        <button :class="{ active: activeTab === 'problemset' }" @click="activeTab = 'problemset'">题库</button>
      </div>
      <div class="top-status-wrap">
        <button class="auth-open-btn" @click="openAuth">{{ authActionText }}</button>
        <div class="top-status">{{ sending ? 'AI 思考中...' : '在线' }}</div>
      </div>
    </header>

    <div class="content-grid">
      <section class="main-panel" v-if="activeTab === 'home'">
        <main class="chat-main" ref="listRef">
          <div v-for="(msg, idx) in messages" :key="idx" class="msg" :class="msg.role">
            <div class="meta">{{ msg.role === 'user' ? '你' : 'AI' }} · {{ msg.time }}</div>
            <div class="bubble">{{ msg.content }}</div>
          </div>
        </main>

        <footer class="chat-input-area">
          <textarea
            v-model="input"
            placeholder="请输入你的问题，Enter发送，Shift+Enter换行"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <button :disabled="sending || !input.trim()" @click="sendMessage">发送</button>
        </footer>
      </section>

      <section class="main-panel problem-panel" v-else>
        <div class="problem-toolbar">
          <input v-model="keyword" placeholder="关键词搜索题目" @keyup.enter="fetchProblems" />
          <select v-model="difficulty" @change="fetchProblems">
            <option :value="''">全部难度</option>
            <option v-for="level in OJ_DIFFICULTY_OPTIONS.filter((item) => item)" :key="level" :value="level">
              {{ level }}
            </option>
          </select>
          <button @click="fetchProblems">刷新</button>
        </div>

        <div class="problem-list" v-if="!problemLoading">
          <div class="problem-item" v-for="p in problems" :key="p._id">
            <div class="pid">{{ p._id }}</div>
            <div class="ptitle">{{ p.title }}</div>
            <div class="pdiff">{{ p.difficulty }}</div>
          </div>
          <div v-if="!problems.length" class="empty">暂无题目</div>
        </div>
        <div class="empty" v-else>加载中...</div>
        <div class="error" v-if="problemError">{{ problemError }}</div>
      </section>

      <aside class="right-sidebar">
        <div class="card sessions-card">
          <div class="sessions-head">
            <div class="card-title">Sessions</div>
            <button @click="createSession">新建</button>
          </div>
          <div class="session-list">
            <button
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ active: s.id === currentSessionId }"
              @click="selectSession(s.id)"
            >
              <div class="stitle">{{ s.title }}</div>
              <div class="smeta">{{ new Date(s.createdAt).toLocaleString() }}</div>
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>

  <div class="auth-modal-mask" v-if="showAuthModal" @click.self="closeAuthModal">
    <div class="auth-modal card">
      <div class="auth-modal-head">
        <div class="card-title">OJ 登录注册</div>
        <button class="close-btn" @click="closeAuthModal">✕</button>
      </div>

      <div class="switch-row" v-if="!ojUser.loggedIn">
        <button :class="{ active: authMode === AUTH_MODES.LOGIN }" @click="authMode = AUTH_MODES.LOGIN">登录</button>
        <button :class="{ active: authMode === AUTH_MODES.REGISTER }" @click="authMode = AUTH_MODES.REGISTER">注册</button>
      </div>

      <div v-if="ojUser.loggedIn" class="login-ok">已登录：{{ ojUser.profileName }}</div>

      <div v-else class="auth-form">
        <input ref="authUsernameRef" v-model="ojUser.username" placeholder="用户名" />
        <input v-model="ojUser.password" placeholder="密码" type="password" />
        <input v-if="authMode === AUTH_MODES.REGISTER" v-model="ojUser.email" placeholder="邮箱" type="email" />

        <div v-if="authMode === AUTH_MODES.REGISTER" class="captcha-row">
          <input v-model="ojUser.captcha" placeholder="验证码" />
          <img v-if="ojUser.captchaSrc" :src="ojUser.captchaSrc" alt="captcha" @click="refreshCaptcha" />
        </div>

        <button @click="handleAuthSubmit">{{ authMode === AUTH_MODES.LOGIN ? '登录 OJ' : '注册 OJ' }}</button>
        <div class="error" v-if="ojUser.error">{{ ojUser.error }}</div>
      </div>
    </div>
  </div>
</template>
