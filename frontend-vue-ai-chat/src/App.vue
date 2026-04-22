<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useChatFeature } from './composables/useChatFeature'
import { AUTH_MODES, OJ_DIFFICULTY_OPTIONS, sanitizeTextInput } from './utils/validators'
import { useOjAuthAndProblems } from './composables/useOjAuthAndProblems'

const activeTab = ref('home')
const rightPanelTab = ref('problem')
const selectedProblemId = ref('')

const submitLanguage = ref('C++')
const submitCode = ref('')
const submitState = ref({ type: '', message: '' })

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
  selectOrCreateProblemSession,
  ensureSessionMetadata,
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
const sessionCount = computed(() => sessions.value.length)
const hasSessions = computed(() => sessionCount.value > 0)
const problemCount = computed(() => problems.value.length)
const selectedProblem = computed(() => problems.value.find((item) => String(item._id) === selectedProblemId.value) || null)
const hasSelectedProblem = computed(() => Boolean(selectedProblem.value))

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

const switchRightPanelTab = (tab) => {
  rightPanelTab.value = tab
}

const handleSelectSession = (sessionId) => {
  selectSession(sessionId)
  const targetSession = sessions.value.find((session) => session.id === sessionId)
  selectedProblemId.value = targetSession?.problemId ? String(targetSession.problemId) : ''
  activeTab.value = 'home'
}

    const selectProblemForRightPanel = (problem) => {
      if (!problem?._id) return

      const targetSession = selectOrCreateProblemSession(problem)
      if (!targetSession) return

      selectedProblemId.value = String(problem._id)
      rightPanelTab.value = 'problem'
      activeTab.value = 'home'

      ensureSessionMetadata(targetSession.id, {
        problemId: String(problem._id),
        problemTitle: problem.title,
        youtuSessionId: `problem_${problem._id}`
      })
    }

const clearSelectedProblem = () => {
  selectedProblemId.value = ''
}

const handleSubmitCode = () => {
  submitState.value = { type: '', message: '' }

  if (!selectedProblem.value) {
    submitState.value = { type: 'error', message: 'Please select a problem first.' }
    return
  }

  const normalizedCode = sanitizeTextInput(submitCode.value, 20000)
  submitCode.value = normalizedCode

  if (normalizedCode.length < 10) {
    submitState.value = { type: 'error', message: 'Code must be at least 10 characters.' }
    return
  }

  submitState.value = {
    type: 'info',
    message: 'Submission API is not integrated yet. UI and validation are ready.'
  }
}

const handleGlobalKeydown = (event) => {
  if (event.key === 'Escape' && showAuthModal.value) {
    closeAuthModal()
  }
}

watch(showAuthModal, (visible) => {
  document.body.style.overflow = visible ? 'hidden' : ''
})

watch(problems, (items) => {
  const targetExists = items.some((item) => String(item._id) === selectedProblemId.value)
  if (!targetExists) {
    selectedProblemId.value = ''
  }
})

onMounted(async () => {
  loadSessions()
  await refreshCaptcha()
  await fetchProblems()
  window.addEventListener('keydown', handleGlobalKeydown)
  
  // 如果没有会话，自动显示题库
  if (!hasSessions.value) {
    activeTab.value = 'problemset'
  }
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

    <div class="content-grid" :class="{ 'problemset-mode': activeTab === 'problemset' || !hasSessions }">
      <aside class="left-sidebar">
        <div class="card sessions-card">
          <div class="session-count">{{ sessionCount }} 会话</div>
          <div class="session-list">
            <button
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ active: s.id === currentSessionId }"
              @click="handleSelectSession(s.id)"
            >
              <div class="session-main">
                <div class="stitle">{{ s.title }}</div>
                <div class="session-dot" :class="{ active: s.id === currentSessionId }" />
              </div>
              <div class="smeta">{{ new Date(s.createdAt).toLocaleString() }}</div>
            </button>
          </div>
        </div>
      </aside>

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
          <button class="problem-item" v-for="p in problems" :key="p._id" @click="selectProblemForRightPanel(p)">
            <div class="problem-item-main">
              <div class="pid">{{ p._id }}</div>
              <div class="pdiff">{{ p.difficulty || 'Unknown' }}</div>
            </div>
            <div class="ptitle">{{ p.title }}</div>
          </button>
          <div v-if="!problems.length" class="empty">暂无题目</div>
        </div>
        <div class="empty" v-else>加载中...</div>
        <div class="error" v-if="problemError">{{ problemError }}</div>
      </section>

      <aside class="right-sidebar" v-if="activeTab === 'home'">
        <div class="card side-tab-card">
          <div class="switch-row side-tabs">
            <button :class="{ active: rightPanelTab === 'problem' }" @click="switchRightPanelTab('problem')">题目信息</button>
            <button :class="{ active: rightPanelTab === 'submit' }" @click="switchRightPanelTab('submit')">OJ提交</button>
          </div>
        </div>

        <div class="card side-content-card" v-if="rightPanelTab === 'problem'">
          <div class="problem-detail" v-if="hasSelectedProblem">
            <div class="detail-head">
              <div>
                <div class="card-title">{{ selectedProblem.title }}</div>
                <div class="card-subtitle">Problem ID: {{ selectedProblem._id }}</div>
              </div>
              <button class="secondary-btn" @click="clearSelectedProblem">返回题库</button>
            </div>

            <div class="detail-grid">
              <div class="detail-row"><span>难度</span><strong>{{ selectedProblem.difficulty || 'Unknown' }}</strong></div>
              <div class="detail-row"><span>时间限制</span><strong>{{ selectedProblem.time_limit || '-' }}</strong></div>
              <div class="detail-row"><span>内存限制</span><strong>{{ selectedProblem.memory_limit || '-' }}</strong></div>
              <div class="detail-row"><span>提交数</span><strong>{{ selectedProblem.submission_number || 0 }}</strong></div>
              <div class="detail-row"><span>通过数</span><strong>{{ selectedProblem.accepted_number || 0 }}</strong></div>
              <div class="detail-row"><span>通过率</span><strong>{{ selectedProblem.submission_number ? `${Math.round((selectedProblem.accepted_number / selectedProblem.submission_number) * 100)}%` : '0%' }}</strong></div>
            </div>
          </div>
          <div class="empty" v-else>请先在题库中选择一道题目</div>
        </div>

        <div class="card side-content-card" v-else>
          <template v-if="hasSelectedProblem">
            <div class="submit-head">
              <div class="card-title">提交到: {{ selectedProblem.title }}</div>
              <div class="submit-meta">Problem ID: {{ selectedProblem._id }}</div>
            </div>
            <div class="submit-form">
              <select v-model="submitLanguage">
                <option value="C++">C++</option>
                <option value="C">C</option>
                <option value="Java">Java</option>
                <option value="Python3">Python3</option>
              </select>
              <textarea v-model="submitCode" placeholder="Enter your source code here" />
              <button @click="handleSubmitCode">提交代码</button>
            </div>
            <div class="empty" :class="submitState.type" v-if="submitState.message">{{ submitState.message }}</div>
          </template>
          <div class="empty" v-else>请先选择题目后再提交代码</div>
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
