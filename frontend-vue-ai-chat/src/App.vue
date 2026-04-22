<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CodeEditor from './components/CodeEditor.vue'
import { useChatFeature } from './composables/useChatFeature'
import { AUTH_MODES, OJ_DIFFICULTY_OPTIONS, sanitizeHtmlContent, sanitizeTextInput } from './utils/validators'
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
  loadSessions,
  selectSession,
  selectOrCreateProblemSession,
  ensureSessionMetadata,
  sendMessage,
  clearAllConversationData,
  closeSocket
} = useChatFeature()

const {
  authMode,
  authUsernameRef,
  authReady,
  ojUser,
  problems,
  problemLoading,
  problemError,
  keyword,
  difficulty,
  isLoginMode,
  hydrateAuthSession,
  fetchUserProfile,
  refreshCaptcha,
  login,
  register,
  logout,
  fetchProblems
} = useOjAuthAndProblems()

const authActionText = computed(() => (ojUser.value.loggedIn ? ojUser.value.profileName : '去登录'))
const isProfileTab = computed(() => activeTab.value === 'profile')
const requiresAuth = computed(() => authReady.value && !ojUser.value.loggedIn)
const sessionCount = computed(() => sessions.value.length)
const hasSessions = computed(() => sessionCount.value > 0)
const selectedProblem = computed(() => problems.value.find((item) => String(item._id) === selectedProblemId.value) || null)
const hasSelectedProblem = computed(() => Boolean(selectedProblem.value))
const selectedProblemDescription = computed(() => {
  if (!selectedProblem.value) return ''

  const candidate =
    selectedProblem.value.description ||
    selectedProblem.value.content ||
    selectedProblem.value.desc ||
    selectedProblem.value.problem_description ||
    ''

  const normalized = String(candidate).trim()
  return normalized || '暂无题目描述'
})

const selectedProblemDescriptionHtml = computed(() => sanitizeHtmlContent(selectedProblemDescription.value))

const handleGoToAuth = () => {
  if (ojUser.value.loggedIn) {
    activeTab.value = 'profile'
    fetchUserProfile().catch((error) => {
      console.warn('Failed to refresh profile data.', error)
    })
    return
  }

  activeTab.value = 'auth'
  rightPanelTab.value = 'problem'
  submitState.value = { type: '', message: '' }
}

const handleAuthSubmit = async () => {
  if (isLoginMode.value) {
    await login()
  } else {
    await register()
  }

  if (ojUser.value.loggedIn) {
    await fetchProblems()
    activeTab.value = 'home'
  }
}

const handleAuthKeydown = (event) => {
  if (event.key === 'Enter') {
    event.preventDefault()
    handleAuthSubmit()
  }
}

const handleLogout = async () => {
  const succeeded = await logout()
  if (!succeeded) return

  activeTab.value = 'auth'
  selectedProblemId.value = ''
  rightPanelTab.value = 'problem'
  submitCode.value = ''
  submitState.value = { type: '', message: '' }
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

const getSessionTag = (session) => {
  if (session?.problemId) {
    return String(session.problemId)
  }

  return String(session?.id || 'chat').slice(-4)
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

const handleClearAllSessions = () => {
  clearAllConversationData()
  selectedProblemId.value = ''
  rightPanelTab.value = 'problem'
  activeTab.value = 'problemset'
  submitCode.value = ''
  submitState.value = { type: '', message: '' }
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

const handleSubmitCodeToAi = () => {
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

  const prompt = [
    `Please review and improve this OJ solution for problem ${selectedProblem.value._id} ${selectedProblem.value.title}.`,
    '',
    'Problem description:',
    selectedProblemDescription.value,
    '',
    `Language: ${submitLanguage.value}`,
    'Code:',
    normalizedCode
  ].join('\n')

  input.value = prompt
  submitState.value = { type: 'info', message: 'Code has been sent to AI input box. Click 发送 to continue.' }
}

watch(
  [currentSessionId, sessions],
  ([sessionId, sessionList]) => {
    if (!sessionId) {
      selectedProblemId.value = ''
      return
    }

    const targetSession = sessionList.find((session) => session.id === sessionId)
    selectedProblemId.value = targetSession?.problemId ? String(targetSession.problemId) : ''
  },
  { immediate: true }
)

watch(problems, (items) => {
  const targetExists = items.some((item) => String(item._id) === selectedProblemId.value)
  if (!targetExists) {
    selectedProblemId.value = ''
  }
})

watch(
  () => ojUser.value.loggedIn,
  (loggedIn) => {
    if (!authReady.value) return

    if (!loggedIn) {
      activeTab.value = 'auth'
      return
    }

    if (activeTab.value === 'auth') {
      activeTab.value = 'home'
    }
  }
)

watch(authMode, async (mode) => {
  if (mode === AUTH_MODES.REGISTER) {
    await refreshCaptcha()
  }
})

onMounted(async () => {
  loadSessions()
  await hydrateAuthSession()

  if (!ojUser.value.loggedIn) {
    await refreshCaptcha()
    activeTab.value = 'auth'
    return
  }

  await fetchProblems()
  activeTab.value = 'home'
})

onBeforeUnmount(() => {
  closeSocket()
})
</script>

<template>
  <div class="app-shell">
    <header class="top-nav">
      <div class="tabs" v-if="!requiresAuth">
        <button :class="{ active: activeTab === 'home' }" @click="activeTab = 'home'">主页</button>
        <button :class="{ active: activeTab === 'problemset' }" @click="activeTab = 'problemset'">题库</button>
        <button :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">个人中心</button>
      </div>
      <div class="tabs" v-else>
        <button class="active">登录 / 注册</button>
      </div>

      <div class="top-status-wrap">
        <button
          class="auth-open-btn"
          :class="{ 'auth-user-btn': ojUser.loggedIn }"
          @click="handleGoToAuth"
        >
          {{ authActionText }}
        </button>
        <div class="top-status">{{ sending ? 'AI 思考中...' : '在线' }}</div>
      </div>
    </header>

    <section class="auth-screen" v-if="requiresAuth || activeTab === 'auth'">
      <div class="auth-page card">
        <div class="auth-page-header">
          <h2>OJ 登录注册</h2>
          <p>请先完成登录或注册后继续使用题库和聊天功能</p>
        </div>

        <div class="switch-row auth-switch-row">
          <button :class="{ active: authMode === AUTH_MODES.LOGIN }" @click="authMode = AUTH_MODES.LOGIN">登录</button>
          <button :class="{ active: authMode === AUTH_MODES.REGISTER }" @click="authMode = AUTH_MODES.REGISTER">注册</button>
        </div>

        <div class="auth-form auth-page-form" @keydown="handleAuthKeydown">
          <input ref="authUsernameRef" v-model="ojUser.username" placeholder="用户名" />
          <input v-model="ojUser.password" placeholder="密码" type="password" />
          <input v-if="authMode === AUTH_MODES.REGISTER" v-model="ojUser.email" placeholder="邮箱" type="email" />

          <div v-if="authMode === AUTH_MODES.REGISTER" class="captcha-row">
            <input v-model="ojUser.captcha" placeholder="验证码" />
            <img v-if="ojUser.captchaSrc" :src="ojUser.captchaSrc" alt="captcha" @click="refreshCaptcha" />
          </div>

          <button class="auth-submit-btn" @click="handleAuthSubmit">
            {{ authMode === AUTH_MODES.LOGIN ? '登录 OJ' : '注册 OJ' }}
          </button>
          <div class="error" v-if="ojUser.error">{{ ojUser.error }}</div>
        </div>
      </div>
    </section>

    <section class="profile-screen" v-else-if="isProfileTab">
      <div class="profile-page card">
        <div class="profile-header">
          <div class="profile-avatar" v-if="ojUser.avatar">
            <img :src="ojUser.avatar" alt="avatar" />
          </div>
          <div class="profile-avatar profile-avatar-fallback" v-else>{{ (ojUser.profileName || 'U').slice(0, 1).toUpperCase() }}</div>

          <div class="profile-title-group">
            <h2>{{ ojUser.profileName || ojUser.username || '未命名用户' }}</h2>
            <p>{{ ojUser.email || 'No email available' }}</p>
          </div>
        </div>

        <div class="profile-grid">
          <div class="profile-item">
            <span>用户名</span>
            <strong>{{ ojUser.username || '-' }}</strong>
          </div>
          <div class="profile-item">
            <span>学号</span>
            <strong>{{ ojUser.studentNumber || '-' }}</strong>
          </div>
          <div class="profile-item profile-item-full">
            <span>个性签名</span>
            <strong>{{ ojUser.signature || '-' }}</strong>
          </div>
        </div>

        <div class="profile-actions">
          <button class="secondary-btn" @click="activeTab = 'home'">返回主页</button>
          <button class="danger-btn" @click="handleLogout">退出登录</button>
        </div>

        <div class="error" v-if="ojUser.error">{{ ojUser.error }}</div>
      </div>
    </section>

    <div class="content-grid" :class="{ 'problemset-mode': activeTab === 'problemset' || !hasSessions }" v-else>
      <aside class="left-sidebar">
        <div class="card sessions-card">
          <div class="session-header-row">
            <div class="session-count">{{ sessionCount }} 会话</div>
            <button
              class="session-clear-btn"
              type="button"
              title="清空所有对话"
              @click="handleClearAllSessions"
            >
              clear
            </button>
          </div>
          <div class="session-list">
            <button
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ active: s.id === currentSessionId }"
              @click="handleSelectSession(s.id)"
            >
              <div class="session-main">
                <div class="session-tag">{{ getSessionTag(s) }}</div>
                <div class="stitle">{{ s.title }}</div>
                <div class="smeta">{{ new Date(s.createdAt).toLocaleString() }}</div>
              </div>
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
          <div class="problem-grid" v-if="problems.length">
            <button class="problem-item" v-for="p in problems" :key="p._id" @click="selectProblemForRightPanel(p)">
              <div class="problem-item-main">
                <div class="pid">{{ p._id }}</div>
                <div class="pdiff">{{ p.difficulty || 'Unknown' }}</div>
              </div>
              <div class="ptitle">{{ p.title }}</div>
            </button>
          </div>
          <div v-else class="empty">暂无题目</div>
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
            <div class="problem-detail-top">
              <div class="card-title">{{ selectedProblem.title }}</div>
              <div class="card-subtitle">Problem ID: {{ selectedProblem._id }}</div>
            </div>

            <div class="problem-detail-middle">
              <div class="problem-description" v-html="selectedProblemDescriptionHtml" />
            </div>

            <div class="problem-detail-bottom">
              <div class="detail-grid compact-detail-grid">
                <div class="detail-row compact-detail-row"><span>难度</span><strong>{{ selectedProblem.difficulty || 'Unknown' }}</strong></div>
                <div class="detail-row compact-detail-row"><span>时间限制</span><strong>{{ selectedProblem.time_limit || '-' }}</strong></div>
                <div class="detail-row compact-detail-row"><span>内存限制</span><strong>{{ selectedProblem.memory_limit || '-' }}</strong></div>
                <div class="detail-row compact-detail-row"><span>提交数</span><strong>{{ selectedProblem.submission_number || 0 }}</strong></div>
                <div class="detail-row compact-detail-row"><span>通过数</span><strong>{{ selectedProblem.accepted_number || 0 }}</strong></div>
                <div class="detail-row compact-detail-row"><span>通过率</span><strong>{{ selectedProblem.submission_number ? `${Math.round((selectedProblem.accepted_number / selectedProblem.submission_number) * 100)}%` : '0%' }}</strong></div>
              </div>
            </div>
          </div>
          <div class="empty" v-else>请先在题库中选择一道题目</div>
        </div>

        <div class="card side-content-card" v-else>
          <template v-if="hasSelectedProblem">
            <div class="submit-layout">
              <div class="submit-editor-area">
                <div class="submit-form">
                  <select v-model="submitLanguage">
                    <option value="C++">C++</option>
                    <option value="C">C</option>
                    <option value="Java">Java</option>
                    <option value="Python3">Python3</option>
                  </select>
                  <CodeEditor
                    v-model="submitCode"
                    class="oj-code-editor"
                    :language="submitLanguage"
                    placeholder="Enter your source code here"
                  />
                  <div class="submit-action-row">
                    <button @click="handleSubmitCode">提交代码</button>
                    <button class="secondary-btn" @click="handleSubmitCodeToAi">发给AI</button>
                  </div>
                </div>
              </div>
              <div class="submit-result-area">
                <div class="empty" :class="submitState.type" v-if="submitState.message">{{ submitState.message }}</div>
                <div class="empty" v-else>提交结果和错误信息将在此显示</div>
              </div>
            </div>
          </template>
          <div class="empty" v-else>请先选择题目后再提交代码</div>
        </div>
      </aside>
    </div>
  </div>
</template>
