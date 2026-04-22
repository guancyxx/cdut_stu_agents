<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const STORAGE_KEY = 'cdut-ai-chat-sessions-v1'

const activeTab = ref('home')
const sending = ref(false)
const input = ref('')
const listRef = ref(null)
const authUsernameRef = ref(null)

const sessions = ref([])
const currentSessionId = ref('')

const authMode = ref('login')
const showAuthModal = ref(false)
const ojUser = ref({
  username: '',
  password: '',
  email: '',
  captcha: '',
  captchaSrc: '',
  loggedIn: false,
  profileName: '',
  error: ''
})

const problems = ref([])
const problemLoading = ref(false)
const problemError = ref('')
const keyword = ref('')
const difficulty = ref('')

let ws = null
let streamSessionId = ''
let currentAssistantIndex = -1

const currentSession = computed(() => sessions.value.find((s) => s.id === currentSessionId.value) || null)
const messages = computed(() => currentSession.value?.messages || [])

const makeSession = () => ({
  id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  title: '新会话',
  createdAt: Date.now(),
  messages: [
    {
      role: 'assistant',
      content: '你好，我是 CDUT AI 助手。现在已接入 youtu-agent 实时回复。',
      time: new Date().toLocaleTimeString()
    }
  ]
})

const saveSessions = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.value))
}

const loadSessions = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length) {
        sessions.value = parsed
        currentSessionId.value = parsed[0].id
        return
      }
    }
  } catch {
    // ignore parse error
  }
  const s = makeSession()
  sessions.value = [s]
  currentSessionId.value = s.id
  saveSessions()
}

const createSession = () => {
  const s = makeSession()
  sessions.value.unshift(s)
  currentSessionId.value = s.id
  saveSessions()
}

const selectSession = (id) => {
  currentSessionId.value = id
}

const getSessionById = (id) => sessions.value.find((s) => s.id === id)

const appendMessageToSession = (sessionId, msg) => {
  const s = getSessionById(sessionId)
  if (!s) return
  s.messages.push(msg)
  if (s.title === '新会话' && msg.role === 'user') {
    s.title = msg.content.slice(0, 20)
  }
  saveSessions()
}

const scrollToBottom = async () => {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

const getWsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

const ensureWs = () => {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return ws
  }

  ws = new WebSocket(getWsUrl())

  ws.onmessage = async (evt) => {
    let event
    try {
      event = JSON.parse(evt.data)
    } catch {
      return
    }

    const targetSessionId = streamSessionId || currentSessionId.value
    const s = getSessionById(targetSessionId)
    if (!s) return

    if (event.type === 'raw' && event.data?.type === 'text') {
      if (currentAssistantIndex === -1) {
        s.messages.push({
          role: 'assistant',
          content: '',
          time: new Date().toLocaleTimeString()
        })
        currentAssistantIndex = s.messages.length - 1
      }

      if (event.data.delta) {
        s.messages[currentAssistantIndex].content += event.data.delta
      }

      if (event.data.inprogress === false) {
        currentAssistantIndex = -1
      }

      saveSessions()
      await scrollToBottom()
      return
    }

    if (event.type === 'error') {
      s.messages.push({
        role: 'assistant',
        content: `请求失败：${event.data?.message || '未知错误'}`,
        time: new Date().toLocaleTimeString()
      })
      sending.value = false
      currentAssistantIndex = -1
      saveSessions()
      await scrollToBottom()
      return
    }

    if (event.type === 'finish') {
      sending.value = false
      currentAssistantIndex = -1
      saveSessions()
      await scrollToBottom()
    }
  }

  ws.onclose = () => {
    sending.value = false
    currentAssistantIndex = -1
  }

  return ws
}

const waitForOpen = (socket) => {
  if (socket.readyState === WebSocket.OPEN) return Promise.resolve()

  return new Promise((resolve, reject) => {
    const onOpen = () => {
      socket.removeEventListener('error', onError)
      resolve()
    }
    const onError = () => {
      socket.removeEventListener('open', onOpen)
      reject(new Error('WebSocket connection failed'))
    }
    socket.addEventListener('open', onOpen, { once: true })
    socket.addEventListener('error', onError, { once: true })
  })
}

const sendMessage = async () => {
  const text = input.value.trim()
  if (!text || sending.value || !currentSession.value) return

  appendMessageToSession(currentSessionId.value, {
    role: 'user',
    content: text,
    time: new Date().toLocaleTimeString()
  })

  input.value = ''
  sending.value = true
  streamSessionId = currentSessionId.value
  await scrollToBottom()

  try {
    const socket = ensureWs()
    await waitForOpen(socket)

    socket.send(
      JSON.stringify({
        type: 'query',
        content: {
          query: text
        }
      })
    )
  } catch (err) {
    appendMessageToSession(streamSessionId, {
      role: 'assistant',
      content: `连接失败：${err.message || String(err)}`,
      time: new Date().toLocaleTimeString()
    })
    sending.value = false
    currentAssistantIndex = -1
    await scrollToBottom()
  }
}

const getCookie = (name) => {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return m ? decodeURIComponent(m[1]) : ''
}

const ensureOjCsrf = async () => {
  await fetch('/oj-api/api/profile', { credentials: 'include' })
  return getCookie('csrftoken')
}

const refreshCaptcha = async () => {
  try {
    const resp = await fetch('/oj-api/api/captcha?refresh=1', { credentials: 'include' })
    const data = await resp.json()
    ojUser.value.captchaSrc = data?.data || ''
  } catch {
    ojUser.value.captchaSrc = ''
  }
}

const ojLogin = async () => {
  ojUser.value.error = ''
  const csrf = await ensureOjCsrf()
  const resp = await fetch('/oj-api/api/login', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
      Referer: window.location.origin
    },
    body: JSON.stringify({
      username: ojUser.value.username,
      password: ojUser.value.password
    })
  })
  const result = await resp.json()
  if (result.error) {
    ojUser.value.error = typeof result.data === 'string' ? result.data : result.error
    return
  }
  ojUser.value.loggedIn = true
  ojUser.value.profileName = result.data?.username || ojUser.value.username
  ojUser.value.password = ''
  showAuthModal.value = false
}

const ojRegister = async () => {
  ojUser.value.error = ''
  const csrf = await ensureOjCsrf()
  const resp = await fetch('/oj-api/api/register', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf,
      Referer: window.location.origin
    },
    body: JSON.stringify({
      username: ojUser.value.username,
      password: ojUser.value.password,
      email: ojUser.value.email,
      captcha: ojUser.value.captcha
    })
  })
  const result = await resp.json()
  if (result.error) {
    ojUser.value.error = typeof result.data === 'string' ? result.data : result.error
    await refreshCaptcha()
    return
  }
  ojUser.value.loggedIn = true
  ojUser.value.profileName = ojUser.value.username
  ojUser.value.password = ''
  showAuthModal.value = false
}

const openAuthModal = async () => {
  showAuthModal.value = true
  await nextTick()
  authUsernameRef.value?.focus()
}

const closeAuthModal = () => {
  showAuthModal.value = false
}

const handleGlobalKeydown = (evt) => {
  if (evt.key === 'Escape' && showAuthModal.value) {
    closeAuthModal()
  }
}

const fetchProblems = async () => {
  problemError.value = ''
  problemLoading.value = true
  try {
    const params = new URLSearchParams({ limit: '100', page: '1' })
    if (keyword.value.trim()) params.append('keyword', keyword.value.trim())
    if (difficulty.value) params.append('difficulty', difficulty.value)

    const resp = await fetch(`/oj-api/api/problem/?${params.toString()}`, { credentials: 'include' })
    const data = await resp.json()
    if (data.error) {
      problemError.value = data.data || data.error
      problems.value = []
    } else {
      problems.value = data.data?.results || []
    }
  } catch (e) {
    problemError.value = String(e)
  } finally {
    problemLoading.value = false
  }
}

onMounted(async () => {
  loadSessions()
  await refreshCaptcha()
  await fetchProblems()
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close()
  }
  window.removeEventListener('keydown', handleGlobalKeydown)
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
        <button v-if="!ojUser.loggedIn" class="auth-open-btn" @click="openAuthModal">登录 / 注册</button>
        <button v-else class="auth-open-btn" @click="openAuthModal">{{ ojUser.profileName }}</button>
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
            <option value="">全部难度</option>
            <option value="Low">Low</option>
            <option value="Mid">Mid</option>
            <option value="High">High</option>
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
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
      </div>

      <div v-if="ojUser.loggedIn" class="login-ok">已登录：{{ ojUser.profileName }}</div>

      <div v-else class="auth-form">
        <input ref="authUsernameRef" v-model="ojUser.username" placeholder="用户名" />
        <input v-model="ojUser.password" placeholder="密码" type="password" />
        <input v-if="authMode === 'register'" v-model="ojUser.email" placeholder="邮箱" type="email" />

        <div v-if="authMode === 'register'" class="captcha-row">
          <input v-model="ojUser.captcha" placeholder="验证码" />
          <img v-if="ojUser.captchaSrc" :src="ojUser.captchaSrc" alt="captcha" @click="refreshCaptcha" />
        </div>

        <button v-if="authMode === 'login'" @click="ojLogin">登录 OJ</button>
        <button v-else @click="ojRegister">注册 OJ</button>
        <div class="error" v-if="ojUser.error">{{ ojUser.error }}</div>
      </div>
    </div>
  </div>
</template>
