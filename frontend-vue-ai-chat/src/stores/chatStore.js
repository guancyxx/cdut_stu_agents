// Singleton chat store — module-level so all pages share the same reactive state.
import { computed, nextTick, ref } from 'vue'
import { useSessions } from '../composables/useSessions'
import { useChatSocket } from '../composables/useChatSocket'
import { validateChatInput } from '../utils/validators'

const BASE_SESSIONS_KEY = 'cdut-ai-chat-sessions-v2'

const buildSessionsStorageKey = (username) => {
  const normalized = (username || '').trim().toLowerCase()
  return normalized ? `${BASE_SESSIONS_KEY}::${normalized}` : `${BASE_SESSIONS_KEY}::_anon_`
}

const createHistoryStorageKey = (youtuSessionId) => `cdut-ai-chat-history-${youtuSessionId}`

const sanitizeStoredMessage = (message) => {
  if (!message || typeof message !== 'object') return null
  const role =
    message.role === 'user'
      ? 'user'
      : message.role === 'assistant'
        ? 'assistant'
        : message.role === 'trace'
          ? 'trace'
          : ''
  if (!role) return null
  if (role === 'trace') {
    return {
      role: 'trace',
      stage: typeof message.stage === 'string' ? message.stage.slice(0, 64) : '',
      title: typeof message.title === 'string' ? message.title.slice(0, 120) : '',
      detail: typeof message.detail === 'string' ? message.detail.slice(0, 500) : '',
      output: typeof message.output === 'string' ? message.output.slice(0, 2000) : '',
      time: typeof message.time === 'string' && message.time.trim() ? message.time : new Date().toLocaleTimeString()
    }
  }
  const content = typeof message.content === 'string' ? message.content : ''
  const time = typeof message.time === 'string' && message.time.trim() ? message.time : new Date().toLocaleTimeString()
  const extra = {}
  if (role === 'assistant') {
    if (message.agent) extra.agent = message.agent
    if (message.streamingDone !== undefined) extra.streamingDone = !!message.streamingDone
  }
  return { role, content, time, ...extra }
}

const loadHistoryFromLocalStorage = (youtuSessionId) => {
  if (!youtuSessionId) return []
  try {
    const raw = localStorage.getItem(createHistoryStorageKey(youtuSessionId))
    const parsed = raw ? JSON.parse(raw) : []
    if (!Array.isArray(parsed)) return []
    return parsed.map(sanitizeStoredMessage).filter(Boolean)
  } catch {
    return []
  }
}

const saveHistoryToLocalStorage = (youtuSessionId, messages = []) => {
  if (!youtuSessionId) return
  const sanitized = Array.isArray(messages)
    ? messages.map(sanitizeStoredMessage).filter(Boolean)
    : []
  localStorage.setItem(createHistoryStorageKey(youtuSessionId), JSON.stringify(sanitized))
}

const LANGUAGE_EXTENSIONS = {
  'C++': 'cpp',
  C: 'c',
  Java: 'java',
  Python3: 'py'
}

// ─── Module-level singleton state ───────────────────────────────────────────

const input = ref('')
const sending = ref(false)
const currentAgent = ref('')
const sessions = ref([])
const currentSessionId = ref('')

const {
  loadSessions: loadSessionsImpl,
  switchUserStorageKey,
  createSession: sessionsCreateSession,
  sessionsStorageKey
} = useSessions()

const {
  connectSocket: socketConnect,
  closeSocket: socketDisconnect,
  sendSocketMessage,
  onSocketMessage
} = useChatSocket()

const messages = ref([])
const attachmentsBySessionId = ref({})
const suggestionsBySessionId = ref({})

// ─── Computed ───────────────────────────────────────────────────────────────

const pendingAttachments = computed(() => {
  const sid = currentSessionId.value
  if (!sid) return []
  return attachmentsBySessionId.value[sid] || []
})

const hasPendingAttachments = computed(() => pendingAttachments.value.length > 0)

const nextStepSuggestions = computed(() => {
  const sid = currentSessionId.value
  if (!sid) return []
  return suggestionsBySessionId.value[sid] || []
})

// ─── Helpers ────────────────────────────────────────────────────────────────

function ensureAttachmentsForSession(sessionId) {
  if (!sessionId) return []
  if (!attachmentsBySessionId.value[sessionId]) {
    attachmentsBySessionId.value[sessionId] = []
  }
  return attachmentsBySessionId.value[sessionId]
}

function addPendingAttachment(attachment) {
  const list = ensureAttachmentsForSession(currentSessionId.value)
  list.push(attachment)
  attachmentsBySessionId.value = { ...attachmentsBySessionId.value }
}

function removePendingAttachment(index) {
  const list = ensureAttachmentsForSession(currentSessionId.value)
  list.splice(index, 1)
  attachmentsBySessionId.value = { ...attachmentsBySessionId.value }
}

function clearPendingAttachments() {
  const list = ensureAttachmentsForSession(currentSessionId.value)
  list.length = 0
  attachmentsBySessionId.value = { ...attachmentsBySessionId.value }
}

function pruneOrphanAttachments() {
  const validIds = new Set(sessions.value.map((s) => s.id))
  const cleaned = {}
  for (const [sid, atts] of Object.entries(attachmentsBySessionId.value)) {
    if (validIds.has(sid)) cleaned[sid] = atts
  }
  attachmentsBySessionId.value = cleaned
}

function pruneOrphanSuggestions() {
  const validIds = new Set(sessions.value.map((s) => s.id))
  const cleaned = {}
  for (const [sid, sugs] of Object.entries(suggestionsBySessionId.value)) {
    if (validIds.has(sid)) cleaned[sid] = sugs
  }
  suggestionsBySessionId.value = cleaned
}

function clearSuggestions() {
  suggestionsBySessionId.value[currentSessionId.value] = []
}

// ─── Session management ─────────────────────────────────────────────────────

function loadSessions() {
  loadSessionsImpl()
  sessions.value = JSON.parse(localStorage.getItem(sessionsStorageKey.value) || '[]')
  if (sessions.value.length > 0 && !currentSessionId.value) {
    currentSessionId.value = sessions.value[0].id
  }
}

function createMappedSession(title = 'New Chat', metadata = {}) {
  const session = sessionsCreateSession(title, metadata)
  // Sync local ref
  sessions.value = JSON.parse(localStorage.getItem(sessionsStorageKey.value) || '[]')
  currentSessionId.value = session.id
  messages.value = []
  return session
}

function switchToUser(username) {
  switchUserStorageKey(buildSessionsStorageKey(username))
  attachmentsBySessionId.value = {}
  suggestionsBySessionId.value = {}
  input.value = ''
  sending.value = false
  loadSessions()
}

function selectSessionAndRestore(sessionId) {
  currentSessionId.value = sessionId
  const target = sessions.value.find((s) => s.id === sessionId)
  if (target?.youtuSessionId) {
    messages.value = loadHistoryFromLocalStorage(target.youtuSessionId)
  } else {
    messages.value = []
  }
}

function selectOrCreateProblemSession(problem) {
  const problemId = String(problem._id)
  // Find existing session for this problem
  const existing = sessions.value.find(
    (s) => s.problemId === problemId
  )
  if (existing) {
    selectSessionAndRestore(existing.id)
    return existing
  }
  const session = createMappedSession(
    problem.title || problemId,
    { problemId, problemTitle: problem.title }
  )
  return session
}

function ensureSessionMetadata(sessionId, metadata) {
  const idx = sessions.value.findIndex((s) => s.id === sessionId)
  if (idx === -1) return
  sessions.value[idx] = { ...sessions.value[idx], ...metadata }
  localStorage.setItem(sessionsStorageKey.value, JSON.stringify(sessions.value))
}

function clearAllConversationData() {
  for (const s of sessions.value) {
    if (s.youtuSessionId) localStorage.removeItem(createHistoryStorageKey(s.youtuSessionId))
  }
  sessions.value = []
  currentSessionId.value = ''
  messages.value = []
  localStorage.setItem(sessionsStorageKey.value, '[]')
}

// ─── Messaging ──────────────────────────────────────────────────────────────

async function sendMessage() {
  const text = input.value.trim()
  const hasAttachment = hasPendingAttachments.value
  if (!text && !hasAttachment) return
  if (sending.value) return

  const validated = validateChatInput(text)
  if (validated.error && !hasAttachment) return

  // Build message content with attachments
  let content = validated.text
  if (pendingAttachments.value.length > 0) {
    const attachmentTexts = pendingAttachments.value.map((att) => {
      if (att.type === 'code') return `\`\`\`${LANGUAGE_EXTENSIONS[att.language] || ''}\n${att.content}\n\`\`\``
      return att.content || ''
    })
    if (content) {
      content = `${content}\n\n${attachmentTexts.join('\n\n')}`
    } else {
      content = attachmentTexts.join('\n\n')
    }
  }

  let session = sessions.value.find((s) => s.id === currentSessionId.value)
  if (!session) {
    session = createMappedSession()
  }

  // Add user message to display
  const userMsg = { role: 'user', content, time: new Date().toLocaleTimeString() }
  messages.value = [...messages.value, userMsg]
  saveHistoryToLocalStorage(session.youtuSessionId || '', messages.value)

  clearPendingAttachments()
  input.value = ''
  sending.value = true

  try {
    // Connect WebSocket if not open
    if (!socketConnect()) {
      // Fallback: simulate response
      messages.value = [
        ...messages.value,
        { role: 'assistant', content: 'Connection unavailable. Please try again.', time: new Date().toLocaleTimeString(), streamingDone: true }
      ]
    } else {
      sendSocketMessage({
        session_id: session.youtuSessionId,
        message: content,
        metadata: {
          problemId: session.problemId,
          problemTitle: session.problemTitle
        }
      })

      // Listen for response
      offSocketMessage = onSocketMessage((data) => {
        if (data.session_id !== session.youtuSessionId) return
        if (data.type === 'trace') {
          messages.value = [
            ...messages.value,
            { role: 'trace', stage: data.stage, title: data.title, detail: data.detail, time: new Date().toLocaleTimeString() }
          ]
          return
        }
        if (data.type === 'suggestions') {
          suggestionsBySessionId.value = {
            ...suggestionsBySessionId.value,
            [currentSessionId.value]: Array.isArray(data.suggestions) ? data.suggestions : []
          }
          return
        }

        // Assistant message
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg?.role === 'assistant' && !lastMsg.streamingDone) {
          // Stream: append to existing
          lastMsg.content += data.content || ''
          if (data.done) {
            lastMsg.streamingDone = true
            lastMsg.agent = data.agent
            sending.value = false
            saveHistoryToLocalStorage(session.youtuSessionId || '', messages.value)
          }
          messages.value = [...messages.value]
        } else {
          // New message
          const newMsg = {
            role: 'assistant',
            content: data.content || '',
            time: new Date().toLocaleTimeString(),
            streamingDone: !!data.done,
            agent: data.agent
          }
          messages.value = [...messages.value, newMsg]
          if (data.done) {
            sending.value = false
            saveHistoryToLocalStorage(session.youtuSessionId || '', messages.value)
          }
        }
      })
    }
  } catch (error) {
    messages.value = [
      ...messages.value,
      { role: 'assistant', content: `Error: ${error.message}`, time: new Date().toLocaleTimeString(), streamingDone: true }
    ]
    sending.value = false
  }

  return session
}

let offSocketMessage = null

async function sendProblemContextToAi(problem, { targetSessionId } = {}) {
  const sessionId = targetSessionId || currentSessionId.value
  const session = sessions.value.find((s) => s.id === sessionId)
  if (!session || !problem) return

  const contextMsg = `Here is the problem context:\nTitle: ${problem.title}\nID: ${problem._id}\nDescription: ${problem.description || 'N/A'}`
  const userMsg = { role: 'user', content: contextMsg, time: new Date().toLocaleTimeString() }
  messages.value = [...messages.value, userMsg]
  saveHistoryToLocalStorage(session.youtuSessionId || '', messages.value)

  sending.value = true
  try {
    if (!socketConnect()) {
      messages.value = [
        ...messages.value,
        { role: 'assistant', content: 'Connection unavailable. Please try again.', time: new Date().toLocaleTimeString(), streamingDone: true }
      ]
      sending.value = false
      return
    }
    sendSocketMessage({
      session_id: session.youtuSessionId,
      message: contextMsg,
      metadata: { problemId: String(problem._id), problemTitle: problem.title }
    })
  } catch (error) {
    messages.value = [
      ...messages.value,
      { role: 'assistant', content: `Error: ${error.message}`, time: new Date().toLocaleTimeString(), streamingDone: true }
    ]
    sending.value = false
  }
}

function sendSuggestion(suggestion) {
  if (!suggestion?.text) return
  input.value = suggestion.text
  sendMessage()
}

function closeSocket() {
  if (offSocketMessage) {
    offSocketMessage()
    offSocketMessage = null
  }
  socketDisconnect()
}

// ─── Export ─────────────────────────────────────────────────────────────────

export function useChatStore() {
  return {
    input,
    sending,
    currentAgent,
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
    createSession: createMappedSession,
    loadSessions,
    switchToUser,
    selectSession: selectSessionAndRestore,
    selectOrCreateProblemSession,
    ensureSessionMetadata,
    sendMessage,
    sendProblemContextToAi,
    clearAllConversationData,
    closeSocket
  }
}
