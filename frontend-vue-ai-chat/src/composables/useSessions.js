import { computed, ref } from 'vue'

const DEFAULT_WELCOME_MESSAGE = '你好，我是 CDUT AI 助手。现在已接入 youtu-agent 实时回复。'

const createTimeLabel = () => new Date().toLocaleTimeString()

const createSessionEntity = () => ({
  id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  title: '新会话',
  createdAt: Date.now(),
  messages: [
    {
      role: 'assistant',
      content: DEFAULT_WELCOME_MESSAGE,
      time: createTimeLabel()
    }
  ]
})

export function useSessions(storageKey) {
  const sessions = ref([])
  const currentSessionId = ref('')

  const currentSession = computed(() => sessions.value.find((item) => item.id === currentSessionId.value) || null)
  const messages = computed(() => currentSession.value?.messages || [])

  const saveSessions = () => {
    localStorage.setItem(storageKey, JSON.stringify(sessions.value))
  }

  const createSession = () => {
    const session = createSessionEntity()
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    saveSessions()
  }

  const loadSessions = () => {
    try {
      const raw = localStorage.getItem(storageKey)
      const parsed = raw ? JSON.parse(raw) : []
      if (Array.isArray(parsed) && parsed.length > 0) {
        sessions.value = parsed
        currentSessionId.value = parsed[0].id
        return
      }
    } catch (error) {
      sessions.value = []
      localStorage.removeItem(storageKey)
      console.warn('Failed to parse saved sessions, storage was reset.', error)
    }

    const initialSession = createSessionEntity()
    sessions.value = [initialSession]
    currentSessionId.value = initialSession.id
    saveSessions()
  }

  const selectSession = (sessionId) => {
    currentSessionId.value = sessionId
  }

  const getSessionById = (sessionId) => sessions.value.find((item) => item.id === sessionId)

  const appendMessageToSession = (sessionId, message) => {
    const targetSession = getSessionById(sessionId)
    if (!targetSession) return

    targetSession.messages.push(message)
    if (targetSession.title === '新会话' && message.role === 'user') {
      targetSession.title = message.content.slice(0, 20)
    }

    saveSessions()
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    messages,
    saveSessions,
    createSession,
    loadSessions,
    selectSession,
    getSessionById,
    appendMessageToSession,
    createTimeLabel
  }
}
