<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CodeEditor from './components/CodeEditor.vue'
import MessageBubble from './components/MessageBubble.vue'
import { useChatFeature } from './composables/useChatFeature'
import { AUTH_MODES, OJ_DIFFICULTY_OPTIONS, initMessageRenderer, sanitizeHtmlContent, sanitizeTextInput } from './utils/validators'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useOjAuthAndProblems } from './composables/useOjAuthAndProblems'

const activeTab = ref('home')
const rightPanelTab = ref('problem')
const selectedProblemId = ref('')

const createSubmitDraft = () => ({
  language: 'C++',
  code: '',
  state: { type: '', message: '' }
})

const submitDraftBySessionId = ref({})

const ensureSubmitDraftForSession = (sessionId) => {
  if (!sessionId) {
    return createSubmitDraft()
  }

  if (!submitDraftBySessionId.value[sessionId]) {
    submitDraftBySessionId.value[sessionId] = createSubmitDraft()
  }

  return submitDraftBySessionId.value[sessionId]
}

const getActiveSubmitDraft = () => ensureSubmitDraftForSession(currentSessionId.value)

const STARTER_CODE = {
  'C++': '#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}\n',
  'C': '#include <stdio.h>\n\nint main() {\n    \n    return 0;\n}\n',
  'Java': 'import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}\n',
  'Python3': '# Read input\n# n = int(input())\n# Process\n# Print output\n'
}

const getStarterCode = (problem, language) => {
  const tpl = problem?.template || {}
  return tpl[language] || STARTER_CODE[language] || ''
}

const activeSubmitLanguage = computed({
  get: () => getActiveSubmitDraft().language,
  set: (value) => {
    const oldLang = getActiveSubmitDraft().language
    const currentCode = getActiveSubmitDraft().code
    const oldStarter = getStarterCode(null, oldLang)
    getActiveSubmitDraft().language = String(value || 'C++')
    // If current code is the old language's default starter, replace it
    if (!currentCode || currentCode === oldStarter) {
      getActiveSubmitDraft().code = getStarterCode(null, String(value || 'C++'))
    }
  }
})

const activeSubmitCode = computed({
  get: () => getActiveSubmitDraft().code,
  set: (value) => {
    getActiveSubmitDraft().code = String(value || '')
  }
})

const activeSubmitState = computed({
  get: () => getActiveSubmitDraft().state,
  set: (value) => {
    getActiveSubmitDraft().state = value && typeof value === 'object' ? value : { type: '', message: '' }
  }
})

const pruneSubmitDrafts = () => {
  const validSessionIds = new Set(sessions.value.map((session) => session.id))
  submitDraftBySessionId.value = Object.fromEntries(
    Object.entries(submitDraftBySessionId.value).filter(([sessionId]) => validSessionIds.has(sessionId))
  )
}

const {
  input,
  listRef,
  sending,
  sessions,
  currentSessionId,
  messages,
  pendingAttachments,
  hasPendingAttachments,
  addPendingAttachment,
  removePendingAttachment,
  clearPendingAttachments,
  pruneOrphanAttachments,
  pruneOrphanSuggestions,
  nextStepSuggestions,
  sendSuggestion,
  clearSuggestions,
  loadSessions,
  selectSession,
  selectOrCreateProblemSession,
  ensureSessionMetadata,
  sendMessage,
  sendProblemContextToAi,
  clearAllConversationData,
  closeSocket
} = useChatFeature()

// Separate trace messages from normal chat messages
// Trace is displayed in a fixed overlay above the input, not in the scrollable chat flow
const chatMessages = computed(() => messages.value.filter((m) => m.role !== 'trace'))
const traceMessages = computed(() => messages.value.filter((m) => m.role === 'trace'))

const {
  authMode,
  authUsernameRef,
  authReady,
  ojUser,
  problems,
  problemLoading,
  problemError,
  submitLoading,
  submitResultBySessionId,
  getSubmitResultForSession,
  setSubmitResultForSession,
  pruneSubmitResults,
  keyword,
  difficulty,
  currentPage,
  totalCount,
  totalPages,
  PAGE_SIZE,
  goToPage,
  searchProblems,
  isLoginMode,
  hydrateAuthSession,
  fetchUserProfile,
  refreshCaptcha,
  login,
  register,
  logout,
  fetchProblems,
  submitSolution
} = useOjAuthAndProblems()

const authActionText = computed(() => (ojUser.value.loggedIn ? ojUser.value.profileName : '去登录'))
const isProfileTab = computed(() => activeTab.value === 'profile')
const requiresAuth = computed(() => authReady.value && !ojUser.value.loggedIn)
const sessionCount = computed(() => sessions.value.length)
const hasSessions = computed(() => sessionCount.value > 0)

// Per-session submit result — switches automatically when session changes
const submitResult = computed(() => getSubmitResultForSession(currentSessionId.value))

// Auto-search when keyword looks like a problem ID pattern (e.g. LQ1273, fps-28e2, 1273)
let keywordSearchTimer = null
watch(keyword, (newVal) => {
  if (keywordSearchTimer) clearTimeout(keywordSearchTimer)
  if (!newVal || !newVal.trim()) return

  const trimmed = newVal.trim()
  // Auto-trigger on problem ID-like patterns: letter+digit, digit-only, or known prefixes
  const looksLikeProblemId = /^(?:[A-Za-z]{1,4}[-_]?\d{1,5}|\d{2,6})$/.test(trimmed)

  if (looksLikeProblemId) {
    // Search immediately for ID-like input (no debounce needed, user likely entering full ID)
    keywordSearchTimer = setTimeout(() => {
      if (keyword.value === newVal) {
        searchProblems()
      }
    }, 400)
  }
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const delta = 2
  const pages = []

  const start = Math.max(1, current - delta)
  const end = Math.min(total, current + delta)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})
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
  activeSubmitState.value = { type: '', message: '' }
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
    syncCurrentSessionUserId(ojUser.value.profileName || ojUser.value.username)
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
  activeSubmitCode.value = ''
  activeSubmitState.value = { type: '', message: '' }
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

const selectProblemForRightPanel = async (problem) => {
  if (!problem?._id) return

  const targetSession = selectOrCreateProblemSession(problem)
  if (!targetSession) return

  const resolvedUserId = sanitizeTextInput(ojUser.value.profileName || ojUser.value.username, 32)

  selectedProblemId.value = String(problem._id)
  rightPanelTab.value = 'problem'
  activeTab.value = 'home'

  // Populate starter code from problem template or default skeleton
  const draft = getActiveSubmitDraft()
  const lang = draft.language || 'C++'
  const templateCode = getStarterCode(problem, lang)
  if (!activeSubmitCode.value) {
    activeSubmitCode.value = templateCode
  }

  ensureSessionMetadata(targetSession.id, {
    problemId: String(problem._id),
    problemTitle: problem.title,
    youtuSessionId: `problem_${problem._id}`,
    userId: resolvedUserId
  })

  if (targetSession.messages.length === 0) {
    await sendProblemContextToAi(problem, { targetSessionId: targetSession.id })
  }
}

const handleClearAllSessions = () => {
  clearAllConversationData()
  selectedProblemId.value = ''
  rightPanelTab.value = 'problem'
  activeTab.value = 'problemset'
  activeSubmitCode.value = ''
  activeSubmitState.value = { type: '', message: '' }
  // Clear all per-session submit results since all sessions are gone
  submitResultBySessionId.value = {}
  pruneOrphanAttachments()
  pruneOrphanSuggestions()
}

const syncCurrentSessionUserId = (userId) => {
  const sessionId = currentSessionId.value
  if (!sessionId || !userId) return

  ensureSessionMetadata(sessionId, {
    userId
  })
}

const mapSubmissionLabelToUiMessage = (result) => {
  if (!result) {
    return {
      type: 'error',
      message: 'No submission result returned.'
    }
  }

  if (result.label === 'ERROR') {
    return {
      type: 'error',
      message: result.message || 'Submission failed.'
    }
  }

  if (result.label === 'TIMEOUT') {
    return {
      type: 'warning',
      message: 'Judge polling timed out. Please refresh later.'
    }
  }

  const detailMessage = `Result: ${result.label} | Score: ${result.score} | Time: ${result.timeCost}ms | Memory: ${result.memoryCost}KB | Submission: ${result.submissionId || '-'}`
  if (result.label === 'ACCEPTED') {
    return {
      type: 'success',
      message: detailMessage
    }
  }

  return {
    type: 'info',
    message: detailMessage
  }
}

const handleSubmitCode = async () => {
  activeSubmitState.value = { type: '', message: '' }

  if (!selectedProblem.value) {
    activeSubmitState.value = { type: 'error', message: 'Please select a problem first.' }
    return
  }

  const normalizedCode = sanitizeTextInput(activeSubmitCode.value, 20000)
  activeSubmitCode.value = normalizedCode

  if (normalizedCode.length < 10) {
    activeSubmitState.value = { type: 'error', message: 'Code must be at least 10 characters.' }
    return
  }

  const result = await submitSolution({
    problemId: selectedProblem.value.id,
    problemQueryId: selectedProblem.value._id,
    language: activeSubmitLanguage.value,
    code: normalizedCode,
    sessionId: currentSessionId.value
  })

  activeSubmitState.value = mapSubmissionLabelToUiMessage(result)
}

const buildResultAttachmentContent = (result) => {
  if (!result) return ''
  const lines = []
  lines.push(`[${result.label}] ${result.display || result.label}`)
  if (result.submissionId) lines.push(`Submission: ${result.submissionId}`)
  if (result.score) lines.push(`Score: ${result.score}`)
  lines.push(`Time: ${result.timeCost}ms | Memory: ${formatMemory(result.memoryCost)}`)
  if (result.errInfo) lines.push(`\nError: ${result.errInfo}`)
  if (result.testCases && result.testCases.length > 0) {
    lines.push(`\nTest Cases:`)
    result.testCases.forEach((tc) => {
      lines.push(`  #${tc.index} ${tc.icon} ${tc.display} | ${tc.cpuTime}ms | ${formatMemory(tc.memory)}${tc.score > 0 ? ` | ${tc.score}pts` : ''}`)
    })
  }
  return lines.join('\n')
}

const getResultClass = (result) => {
  if (!result || !result.label) return 'result-unknown'
  if (result.label === 'ACCEPTED') return 'result-accepted'
  if (result.label === 'COMPILE_ERROR') return 'result-compile-error'
  if (['WRONG_ANSWER', 'RUNTIME_ERROR', 'CPU_TIME_LIMIT_EXCEEDED', 'REAL_TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED', 'SYSTEM_ERROR', 'PARTIALLY_ACCEPTED'].includes(result.label)) return 'result-wrong'
  if (result.label === 'ERROR') return 'result-error'
  return 'result-unknown'
}

const getTestCaseClass = (tc) => {
  if (tc.status === 0 || tc.label === 'ACCEPTED') return 'tc-passed'
  return 'tc-failed'
}

const formatMemory = (kb) => {
  if (!kb || kb <= 0) return '0KB'
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)}MB`
  return `${kb}KB`
}

const handleSubmitCodeToAi = () => {
  if (!selectedProblem.value) {
    activeSubmitState.value = { type: 'error', message: 'Please select a problem first.' }
    return
  }

  const normalizedCode = sanitizeTextInput(activeSubmitCode.value, 20000)
  activeSubmitCode.value = normalizedCode

  if (normalizedCode.length < 10) {
    activeSubmitState.value = { type: 'error', message: 'Code must be at least 10 characters.' }
    return
  }

  // Capture previous submit result BEFORE resetting
  const previousResult = submitResult.value

  // Stage code as attachment
  const language = activeSubmitLanguage.value
  const codeFilename = `${language.toLowerCase().replace('3', '')}_${selectedProblem.value._id}.${language === 'C++' ? 'cpp' : language === 'C' ? 'c' : language === 'Java' ? 'java' : 'py'}`
  addPendingAttachment({
    filename: codeFilename,
    content: normalizedCode,
    type: 'code'
  })

  // If there is a submission result, stage it with rich detail
  if (previousResult) {
    const resultContent = buildResultAttachmentContent(previousResult)
    if (resultContent) {
      addPendingAttachment({
        filename: 'submit-result.txt',
        content: resultContent,
        type: 'result'
      })
    }
  }

  activeSubmitState.value = { type: 'info', message: 'Attachment staged. Click 发送 in chat when ready.' }
}

watch(
  [currentSessionId, sessions],
  ([sessionId, sessionList]) => {
    pruneSubmitDrafts()
    pruneOrphanAttachments()
    pruneOrphanSuggestions()
    pruneSubmitResults(sessionList.map((s) => s.id))

    if (!sessionId) {
      selectedProblemId.value = ''
      rightPanelTab.value = 'problem'
      activeSubmitState.value = { type: '', message: '' }
      return
    }

    ensureSubmitDraftForSession(sessionId)

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

    syncCurrentSessionUserId(ojUser.value.profileName || ojUser.value.username)

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
  // Initialize Markdown/HTML message renderer
  initMessageRenderer(marked, DOMPurify)

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

      <!-- Auth Screen -->
      <div class="auth-page card" v-if="requiresAuth">
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
          <MessageBubble 
            v-for="(msg, idx) in chatMessages" 
            :key="msg._uid || idx" 
            :message="msg" 
            :is-last="idx === chatMessages.length - 1"
          />
        </main>

        <footer class="chat-input-area">
          <TransitionGroup name="trace-slide" tag="div" class="trace-bar" v-if="traceMessages.length">
            <div
              v-for="tmsg in traceMessages"
              :key="tmsg._uid || tmsg.time"
              class="trace-bar-item"
              :class="tmsg.stage?.endsWith('_result') ? 'done' : 'running'"
            >
              <span class="trace-bar-icon">{{ tmsg.stage?.endsWith('_result') ? '✓' : '⟳' }}</span>
              <span class="trace-bar-title">{{ tmsg.title }}</span>
              <span v-if="tmsg.detail" class="trace-bar-detail">{{ tmsg.detail }}</span>
            </div>
          </TransitionGroup>
          <div class="suggestion-chips" v-if="nextStepSuggestions.length && !sending">
            <button
              v-for="(sug, idx) in nextStepSuggestions"
              :key="idx"
              class="suggestion-chip"
              :class="sug.type"
              :title="sug.reason || ''"
              @click="sendSuggestion(sug)"
            >
              <span class="sug-icon">{{ { practice: '🎯', learn: '📖', review: '🔍', debug: '🐛', compete: '🏆' }[sug.type] || '💡' }}</span>
              <span class="sug-title">{{ sug.title }}</span>
            </button>
          </div>
          <div class="pending-attachments" v-if="pendingAttachments.length">
            <div
              v-for="(att, idx) in pendingAttachments"
              :key="idx"
              class="attachment-chip"
              :class="att.type"
            >
              <span class="chip-filename">{{ att.filename }}</span>
              <button class="chip-remove" type="button" @click="removePendingAttachment(idx)">&times;</button>
            </div>
          </div>
          <div class="chat-input-row">
            <textarea
              v-model="input"
              placeholder="请输入你的问题，Enter发送，Shift+Enter换行"
              :disabled="sending"
              @keydown.enter.exact.prevent="sendMessage"
            />
            <button :disabled="sending || (!input.trim() && !hasPendingAttachments)" @click="sendMessage">发送</button>
          </div>
        </footer>
      </section>

      <section class="main-panel problem-panel" v-else>
        <div class="problem-toolbar">
          <input v-model="keyword" placeholder="搜索题目编号或关键词 (如 LQ1273)" @keyup.enter="searchProblems" />
          <select v-model="difficulty" @change="searchProblems">
            <option :value="''">全部难度</option>
            <option v-for="level in OJ_DIFFICULTY_OPTIONS.filter((item) => item)" :key="level" :value="level">
              {{ level }}
            </option>
          </select>
          <button @click="searchProblems">刷新</button>
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

        <div class="pagination" v-if="!problemLoading && totalPages > 1">
          <button
            class="page-btn"
            :disabled="currentPage === 1"
            @click="goToPage(1)"
          >&laquo;</button>
          <button
            class="page-btn"
            :disabled="currentPage === 1"
            @click="goToPage(currentPage - 1)"
          >&lsaquo;</button>

          <button
            v-if="visiblePages[0] > 1"
            class="page-btn page-ellipsis"
            disabled
          >...</button>

          <button
            v-for="page in visiblePages"
            :key="page"
            class="page-btn"
            :class="{ active: page === currentPage }"
            @click="goToPage(page)"
          >{{ page }}</button>

          <button
            v-if="visiblePages[visiblePages.length - 1] < totalPages"
            class="page-btn page-ellipsis"
            disabled
          >...</button>

          <button
            class="page-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(currentPage + 1)"
          >&rsaquo;</button>
          <button
            class="page-btn"
            :disabled="currentPage === totalPages"
            @click="goToPage(totalPages)"
          >&raquo;</button>

          <span class="page-info">{{ currentPage }} / {{ totalPages }} ({{ totalCount }})</span>
        </div>
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
                  <select v-model="activeSubmitLanguage">
                    <option value="C++">C++</option>
                    <option value="C">C</option>
                    <option value="Java">Java</option>
                    <option value="Python3">Python3</option>
                  </select>
                  <CodeEditor
                    v-model="activeSubmitCode"
                    class="oj-code-editor"
                    :language="activeSubmitLanguage"
                    placeholder="Enter your source code here"
                  />
                  <div class="submit-action-row">
                    <button :disabled="submitLoading" @click="handleSubmitCode">{{ submitLoading ? '提交中...' : '提交代码' }}</button>
                    <button class="secondary-btn" :disabled="submitLoading" @click="handleSubmitCodeToAi">发给AI</button>
                  </div>
                </div>
              </div>
              <div class="submit-result-area">
                <!-- Loading state -->
                <div class="submit-result-empty" v-if="submitLoading">
                  <div class="result-spinner"></div>
                  <span>Judging...</span>
                </div>

                <!-- Detailed result panel -->
                <div class="submit-result-panel" v-else-if="submitResult" :class="getResultClass(submitResult)">
                  <!-- Status header -->
                  <div class="result-header">
                    <span class="result-icon">{{ submitResult.icon || '❓' }}</span>
                    <span class="result-label">{{ submitResult.display || submitResult.label }}</span>
                    <span class="result-submission-id" v-if="submitResult.submissionId">#{{ submitResult.submissionId }}</span>
                  </div>

                  <!-- Stats row -->
                  <div class="result-stats-row">
                    <div class="result-stat" v-if="submitResult.score > 0">
                      <span class="stat-label">Score</span>
                      <span class="stat-value">{{ submitResult.score }}</span>
                    </div>
                    <div class="result-stat">
                      <span class="stat-label">Time</span>
                      <span class="stat-value">{{ submitResult.timeCost }}ms</span>
                    </div>
                    <div class="result-stat">
                      <span class="stat-label">Memory</span>
                      <span class="stat-value">{{ formatMemory(submitResult.memoryCost) }}</span>
                    </div>
                  </div>

                  <!-- Error details (compile error, runtime error, system error) -->
                  <div class="result-error-block" v-if="submitResult.errInfo">
                    <div class="error-block-header">
                      <span class="error-block-icon">⚠</span>
                      <span>{{ submitResult.label === 'COMPILE_ERROR' ? 'Compile Error' : 'Error Details' }}</span>
                    </div>
                    <pre class="error-block-content">{{ submitResult.errInfo }}</pre>
                  </div>

                  <!-- Test case results -->
                  <div class="result-test-cases" v-if="submitResult.testCases && submitResult.testCases.length > 0">
                    <!-- Summary bar -->
                    <div class="test-cases-header">
                      <span class="tc-summary-label">Test Cases</span>
                      <span class="tc-pass-count">
                        {{ submitResult.testCases.filter(tc => tc.status === 0 || tc.label === 'ACCEPTED').length }}/{{ submitResult.testCases.length }} passed
                      </span>
                    </div>
                    <!-- Visual progress bar -->
                    <div class="tc-progress-bar">
                      <div
                        v-for="tc in submitResult.testCases"
                        :key="'bar-' + tc.index"
                        class="tc-progress-segment"
                        :class="getTestCaseClass(tc)"
                        :title="`#${tc.index} ${tc.display}`"
                      ></div>
                    </div>
                    <!-- Individual test case cards -->
                    <div class="test-cases-list">
                      <div
                        v-for="tc in submitResult.testCases"
                        :key="'card-' + tc.index"
                        class="test-case-card"
                        :class="getTestCaseClass(tc)"
                      >
                        <div class="tc-card-header">
                          <span class="tc-index">#{{ tc.index }}</span>
                          <span class="tc-icon">{{ tc.icon }}</span>
                          <span class="tc-status-label">{{ tc.display }}</span>
                        </div>
                        <div class="tc-card-metrics">
                          <span class="tc-metric" v-if="tc.cpuTime">
                            <span class="tc-metric-label">Time</span>
                            <span class="tc-metric-value">{{ tc.cpuTime }}ms</span>
                          </span>
                          <span class="tc-metric" v-if="tc.realTime && tc.realTime !== tc.cpuTime">
                            <span class="tc-metric-label">Real</span>
                            <span class="tc-metric-value">{{ tc.realTime }}ms</span>
                          </span>
                          <span class="tc-metric" v-if="tc.memory">
                            <span class="tc-metric-label">Mem</span>
                            <span class="tc-metric-value">{{ formatMemory(tc.memory) }}</span>
                          </span>
                          <span class="tc-metric" v-if="tc.score > 0">
                            <span class="tc-metric-label">Score</span>
                            <span class="tc-metric-value">{{ tc.score }}pts</span>
                          </span>
                          <span class="tc-metric" v-if="tc.signal != null">
                            <span class="tc-metric-label">Signal</span>
                            <span class="tc-metric-value">{{ tc.signal }}</span>
                          </span>
                        </div>
                        <!-- Test case I/O content -->
                        <div class="tc-card-io" v-if="tc.input || tc.expectedOutput || tc.actualOutput">
                          <div class="tc-io-section" v-if="tc.input">
                            <div class="tc-io-label">Input</div>
                            <pre class="tc-io-content tc-input">{{ tc.input }}</pre>
                          </div>
                          <div class="tc-io-section" v-if="tc.expectedOutput">
                            <div class="tc-io-label">Expected</div>
                            <pre class="tc-io-content tc-expected">{{ tc.expectedOutput }}</pre>
                          </div>
                          <div class="tc-io-section" v-if="tc.actualOutput">
                            <div class="tc-io-label">Output</div>
                            <pre class="tc-io-content tc-actual">{{ tc.actualOutput }}</pre>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Flat error message fallback -->
                  <div class="result-fallback-message" v-if="activeSubmitState.message && !submitResult.errInfo && !(submitResult.testCases && submitResult.testCases.length > 0)">
                    {{ activeSubmitState.message }}
                  </div>
                </div>

                <!-- Placeholder -->
                <div class="submit-result-empty" v-else>
                  <span class="empty-icon">📋</span>
                  <span>Submit code to see results</span>
                </div>
              </div>
            </div>
          </template>
          <div class="empty" v-else>请先选择题目后再提交代码</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style>
  </style>
