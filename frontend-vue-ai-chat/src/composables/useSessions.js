import { computed, ref } from 'vue'

const createTimeLabel = () => new Date().toLocaleTimeString()

const createSessionEntity = (title = '新会话', metadata = {}) => ({
  id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  title,
  createdAt: Date.now(),
  problemId: metadata.problemId || '',
  problemTitle: metadata.problemTitle || '',
  youtuSessionId: metadata.youtuSessionId || '',
  userId: metadata.userId || '',
  messages: []
})

export function useSessions(storageKey) {
  const sessions = ref([])
  const currentSessionId = ref('')

  const currentSession = computed(() => sessions.value.find((item) => item.id === currentSessionId.value) || null)
  const messages = computed(() => currentSession.value?.messages || [])

  const saveSessions = () => {
    localStorage.setItem(storageKey, JSON.stringify(sessions.value))
  }

  const createSession = (title = '新会话', metadata = {}) => {
    const session = createSessionEntity(title, metadata)
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    saveSessions()
    return session
  }

  const loadSessions = () => {
    try {
      const raw = localStorage.getItem(storageKey)
      const parsed = raw ? JSON.parse(raw) : []
      if (Array.isArray(parsed) && parsed.length > 0) {
        sessions.value = parsed.map((session) => ({
          ...session,
          youtuSessionId: String(session.youtuSessionId || session.id || ''),
          problemId: session.problemId || '',
          problemTitle: session.problemTitle || '',
          userId: session.userId || '',
          messages: Array.isArray(session.messages) ? session.messages : []
        }))
        currentSessionId.value = sessions.value[0].id
        return
      }
    } catch (error) {
      sessions.value = []
      currentSessionId.value = ''
      localStorage.removeItem(storageKey)
      console.warn('Failed to parse saved sessions, storage was reset.', error)
    }

    sessions.value = []
    currentSessionId.value = ''
    saveSessions()
  }

  const selectSession = (sessionId) => {
    currentSessionId.value = sessionId
  }

  const findSessionByProblemId = (problemId) =>
    sessions.value.find((session) => String(session.problemId || '') === String(problemId || ''))

  const findSessionByYoutuSessionId = (youtuSessionId) =>
    sessions.value.find((session) => String(session.youtuSessionId || '') === String(youtuSessionId || ''))

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

  const upsertSessionHistory = (sessionId, messagesPayload = []) => {
    const targetSession = getSessionById(sessionId)
    if (!targetSession) return

    targetSession.messages = Array.isArray(messagesPayload)
      ? messagesPayload.filter((message) => message && (message.role === 'user' || message.role === 'assistant'))
      : []

    saveSessions()
  }

  const updateSessionMeta = (sessionId, partialMeta = {}) => {
    const targetSession = getSessionById(sessionId)
    if (!targetSession) return null

    targetSession.problemId = partialMeta.problemId ?? targetSession.problemId
    targetSession.problemTitle = partialMeta.problemTitle ?? targetSession.problemTitle
    targetSession.youtuSessionId = partialMeta.youtuSessionId ?? targetSession.youtuSessionId
    targetSession.userId = partialMeta.userId ?? targetSession.userId

    saveSessions()
    return targetSession
  }

  const clearAllSessions = () => {
    sessions.value = []
    currentSessionId.value = ''
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
    findSessionByProblemId,
    findSessionByYoutuSessionId,
    getSessionById,
    appendMessageToSession,
    upsertSessionHistory,
    updateSessionMeta,
    clearAllSessions,
    createTimeLabel
  }
}
