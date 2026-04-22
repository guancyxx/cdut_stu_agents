import { nextTick, ref } from 'vue'
import { useSessions } from './useSessions'
import { useChatSocket } from './useChatSocket'
import { validateChatInput } from '../utils/validators'

const STORAGE_KEY = 'cdut-ai-chat-sessions-v2'

const createHistoryStorageKey = (youtuSessionId) => `cdut-ai-chat-history-${youtuSessionId}`

const sanitizeStoredMessage = (message) => {
  if (!message || typeof message !== 'object') return null

  const role = message.role === 'user' ? 'user' : message.role === 'assistant' ? 'assistant' : ''
  if (!role) return null

  const content = typeof message.content === 'string' ? message.content : ''
  const time = typeof message.time === 'string' && message.time.trim() ? message.time : new Date().toLocaleTimeString()

  return {
    role,
    content,
    time
  }
}

const loadHistoryFromLocalStorage = (youtuSessionId) => {
  if (!youtuSessionId) return []

  try {
    const raw = localStorage.getItem(createHistoryStorageKey(youtuSessionId))
    const parsed = raw ? JSON.parse(raw) : []
    if (!Array.isArray(parsed)) return []

    return parsed
      .map((message) => sanitizeStoredMessage(message))
      .filter(Boolean)
  } catch (error) {
    console.warn('Failed to load chat history from localStorage.', error)
    return []
  }
}

const saveHistoryToLocalStorage = (youtuSessionId, messages = []) => {
  if (!youtuSessionId) return

  const sanitized = Array.isArray(messages)
    ? messages.map((message) => sanitizeStoredMessage(message)).filter(Boolean)
    : []

  localStorage.setItem(createHistoryStorageKey(youtuSessionId), JSON.stringify(sanitized))
}

export function useChatFeature() {
  const input = ref('')
  const listRef = ref(null)
  const sending = ref(false)

  const {
    sessions,
    currentSessionId,
    currentSession,
    messages,
    saveSessions,
    createSession,
    loadSessions,
    selectSession,
    findSessionByProblemId,
    getSessionById,
    appendMessageToSession,
    upsertSessionHistory,
    updateSessionMeta,
    createTimeLabel
  } = useSessions(STORAGE_KEY)

  const scrollToBottom = async () => {
    await nextTick()
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  }

  const syncSessionHistoryCache = (sessionId) => {
    const targetSession = getSessionById(sessionId)
    if (!targetSession?.youtuSessionId) return

    saveHistoryToLocalStorage(targetSession.youtuSessionId, targetSession.messages)
  }

  const restoreSessionHistory = (sessionId) => {
    const targetSession = getSessionById(sessionId)
    if (!targetSession?.youtuSessionId) return

    const history = loadHistoryFromLocalStorage(targetSession.youtuSessionId)
    if (history.length > 0) {
      upsertSessionHistory(sessionId, history)
    }
  }

  const socketDriver = useChatSocket({
    getSessionId: () => currentSessionId.value,
    getSessionById,
    appendMessageToSession,
    saveSessions,
    scrollToBottom,
    setSending: (value) => {
      sending.value = value
    },
    createTimeLabel,
    onAfterMessageAppended: (sessionId) => {
      syncSessionHistoryCache(sessionId)
    }
  })

  const createMappedSession = (title, metadata = {}) => {
    const youtuSessionId = metadata.youtuSessionId || `yt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    return createSession(title, {
      ...metadata,
      youtuSessionId
    })
  }

  const selectSessionAndRestore = (sessionId) => {
    selectSession(sessionId)
    restoreSessionHistory(sessionId)
  }

  const selectOrCreateProblemSession = (problem) => {
    if (!problem?._id) return null

    const problemId = String(problem._id)
    const existed = findSessionByProblemId(problemId)

    if (existed) {
      selectSessionAndRestore(existed.id)
      return existed
    }

    const title = `${problem._id} ${problem.title}`.slice(0, 24)
    const created = createMappedSession(title, {
      problemId,
      problemTitle: problem.title,
      youtuSessionId: `problem_${problemId}`
    })

    restoreSessionHistory(created.id)
    return created
  }

  const sendMessage = async () => {
    if (sending.value || !currentSession.value) return

    const validation = validateChatInput(input.value)
    if (!validation.valid) return

    appendMessageToSession(currentSessionId.value, {
      role: 'user',
      content: validation.value,
      time: createTimeLabel()
    })
    syncSessionHistoryCache(currentSessionId.value)

    input.value = ''
    await scrollToBottom()
    await socketDriver.sendQuery(validation.value)
  }

  const ensureSessionMetadata = (sessionId, partialMeta = {}) => {
    const targetSession = getSessionById(sessionId)
    if (!targetSession) return null

    const youtuSessionId = targetSession.youtuSessionId || partialMeta.youtuSessionId || targetSession.id
    return updateSessionMeta(sessionId, {
      ...partialMeta,
      youtuSessionId
    })
  }

  const closeSocket = () => {
    socketDriver.closeSocket()
  }

  return {
    input,
    listRef,
    sending,
    sessions,
    currentSessionId,
    messages,
    createSession: createMappedSession,
    loadSessions,
    selectSession: selectSessionAndRestore,
    selectOrCreateProblemSession,
    ensureSessionMetadata,
    sendMessage,
    closeSocket
  }
}
