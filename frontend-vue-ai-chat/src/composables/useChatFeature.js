import { computed, nextTick, ref } from 'vue'
import { useSessions } from './useSessions'
import { useChatSocket } from './useChatSocket'
import { validateChatInput } from '../utils/validators'

const STORAGE_KEY = 'cdut-ai-chat-sessions-v2'

const createHistoryStorageKey = (youtuSessionId) => `cdut-ai-chat-history-${youtuSessionId}`

const sanitizeStoredMessage = (message) => {
  if (!message || typeof message !== 'object') return null

  const role = message.role === 'user' ? 'user'
    : message.role === 'assistant' ? 'assistant'
    : message.role === 'trace' ? 'trace'
    : ''
  if (!role) return null

  // Trace messages have structured fields
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

  // Preserve agent info and streaming state for assistant messages
  const extra = {}
  if (role === 'assistant') {
    if (message.agent) extra.agent = message.agent
    if (message.streamingDone !== undefined) extra.streamingDone = !!message.streamingDone
  }

  return {
    role,
    content,
    time,
    ...extra
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

const LANGUAGE_EXTENSIONS = {
  'C++': 'cpp',
  'C': 'c',
  'Java': 'java',
  'Python3': 'py'
}

const buildCodeFilename = (language) => {
  const ext = LANGUAGE_EXTENSIONS[language] || 'txt'
  return `solution.${ext}`
}

const buildResultFilename = () => 'submit-result.txt'

export function useChatFeature() {
  const input = ref('')
  const listRef = ref(null)
  const sending = ref(false)

  // Per-session attachment storage — same pattern as submitDraftBySessionId
  const attachmentsBySessionId = ref({})
  const PRUNE_KEY = Symbol('prune')

  const ensureAttachmentsForSession = (sessionId) => {
    if (!sessionId) return []
    if (!attachmentsBySessionId.value[sessionId]) {
      attachmentsBySessionId.value[sessionId] = []
    }
    return attachmentsBySessionId.value[sessionId]
  }

  // Reactive view of attachments for the current session
  const pendingAttachments = computed({
    get: () => ensureAttachmentsForSession(currentSessionId.value),
    set: () => { /* read-only via helpers */ }
  })

  const addPendingAttachment = (attachment) => {
    if (!attachment || !attachment.filename || !attachment.content) return
    if (!currentSessionId.value) return

    const type = attachment.type || 'code'
    const list = ensureAttachmentsForSession(currentSessionId.value)
    const existing = list.find((item) => item.filename === attachment.filename)
    if (existing) {
      existing.content = attachment.content
      existing.type = type
      return
    }
    list.push({ ...attachment, type })
  }

  const removePendingAttachment = (index) => {
    if (!currentSessionId.value) return
    const list = attachmentsBySessionId.value[currentSessionId.value]
    if (list && index >= 0 && index < list.length) {
      list.splice(index, 1)
    }
  }

  const clearPendingAttachments = () => {
    if (!currentSessionId.value) return
    attachmentsBySessionId.value[currentSessionId.value] = []
  }

  const pruneOrphanAttachments = () => {
    const validSessionIds = new Set(sessions.value.map((s) => s.id))
    attachmentsBySessionId.value = Object.fromEntries(
      Object.entries(attachmentsBySessionId.value).filter(([sid]) => validSessionIds.has(sid))
    )
  }

  const hasPendingAttachments = computed(() => pendingAttachments.value.length > 0)

  // Per-session suggestion storage — follow same pattern as attachmentsBySessionId
  const suggestionsBySessionId = ref({})

  const ensureSuggestionsForSession = (sessionId) => {
    if (!sessionId) return []
    if (!suggestionsBySessionId.value[sessionId]) {
      suggestionsBySessionId.value[sessionId] = []
    }
    return suggestionsBySessionId.value[sessionId]
  }

  // Reactive view of suggestions for the current session
  const nextStepSuggestions = computed({
    get: () => ensureSuggestionsForSession(currentSessionId.value),
    set: () => { /* read-only via helpers */ }
  })

  const setSuggestionsForCurrentSession = (items) => {
    if (!currentSessionId.value) return
    suggestionsBySessionId.value[currentSessionId.value] = items
  }

  const clearSuggestions = () => {
    if (!currentSessionId.value) return
    suggestionsBySessionId.value[currentSessionId.value] = []
  }

  const pruneOrphanSuggestions = () => {
    const validSessionIds = new Set(sessions.value.map((s) => s.id))
    suggestionsBySessionId.value = Object.fromEntries(
      Object.entries(suggestionsBySessionId.value).filter(([sid]) => validSessionIds.has(sid))
    )
  }

  const sendSuggestion = async (suggestion) => {
    if (sending.value || !currentSession.value) return
    const text = suggestion.title || suggestion.target || ''
    if (!text) return

    // Clear suggestions immediately to prevent double-click
    clearSuggestions()

    appendMessageToSession(currentSessionId.value, {
      role: 'user',
      content: text,
      time: createTimeLabel()
    })
    syncSessionHistoryCache(currentSessionId.value)
    input.value = ''
    clearPendingAttachments()
    await scrollToBottom()
    await socketDriver.sendQuery(text)
  }

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
    clearAllSessions,
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
    getCurrentUserId: () => {
      const current = currentSession.value
      return current?.userId || ''
    },
    updateSessionMeta,
    appendMessageToSession,
    saveSessions,
    scrollToBottom,
    setSending: (value) => {
      sending.value = value
    },
    createTimeLabel,
    onAfterMessageAppended: (sessionId) => {
      syncSessionHistoryCache(sessionId)
    },
    onSuggestions: (items) => {
      setSuggestionsForCurrentSession(items)
    },
    onFinish: () => {
      // Remove all trace messages from current session — they've served their purpose
      const session = currentSession.value
      if (session && Array.isArray(session.messages)) {
        session.messages = session.messages.filter((m) => m.role !== 'trace')
      }
    }
  })

  // Expose the current agent indicator from the socket driver
  const currentAgent = computed(() => socketDriver.currentAgent.value)

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
    // Use unique youtuSessionId per session to prevent localStorage history pollution
    // when a previous session for the same problem was cleared
    const uniqueYotuSessionId = `problem_${problemId}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`
    const created = createMappedSession(title, {
      problemId,
      problemTitle: problem.title,
      youtuSessionId: uniqueYotuSessionId
    })

    restoreSessionHistory(created.id)
    return created
  }

  const sendProblemContextToAi = async (problem, options = {}) => {
    if (!problem?._id) return

    const fallbackSessionId = currentSessionId.value
    const targetSessionId = options.targetSessionId || fallbackSessionId
    const targetSession = getSessionById(targetSessionId)
    if (!targetSession) return

    const normalizedDescription = String(
      problem.description ||
      problem.content ||
      problem.desc ||
      problem.problem_description ||
      ''
    ).trim()

    const structuredPrompt = [
      'SYSTEM CONTEXT: OJ problem has been selected.',
      `Problem ID: ${problem._id}`,
      `Title: ${problem.title || 'Untitled'}`,
      `Difficulty: ${problem.difficulty || 'Unknown'}`,
      '',
      'Task requirement:',
      '- Do not provide explanation or solution before the user gives explicit request.',
      '- First, only acknowledge that problem context is loaded.',
      '',
      'Problem statement:',
      normalizedDescription || 'No statement provided.'
    ].join('\n')

    await socketDriver.sendQuery(structuredPrompt, { targetSessionId })
  }

  const encodeAttachmentsAsText = (attachments, textBody = '') => {
    const parts = []

    if (textBody.trim()) {
      parts.push(textBody.trim())
    }

    for (const attachment of attachments) {
      const label = attachment.type === 'result' ? 'Submission Result' : 'Code'
      parts.push(`[Attachment] ${attachment.filename}`)
      parts.push(`\`\`\`${attachment.filename.split('.').pop()}`)
      parts.push(attachment.content)
      parts.push('```')
      parts.push('')
    }

    return parts.join('\n')
  }

  const sendMessage = async () => {
    if (sending.value || !currentSession.value) return

    const hasText = input.value.trim().length > 0
    if (!hasText && !hasPendingAttachments.value) return

    const attachments = [...pendingAttachments.value]
    const textBody = input.value.trim()

    let finalContent = ''
    if (attachments.length > 0) {
      finalContent = encodeAttachmentsAsText(attachments, textBody)
    } else {
      const validation = validateChatInput(textBody)
      if (!validation.valid) return
      finalContent = validation.value
    }

    appendMessageToSession(currentSessionId.value, {
      role: 'user',
      content: finalContent,
      time: createTimeLabel()
    })
    syncSessionHistoryCache(currentSessionId.value)

    input.value = ''
    clearPendingAttachments()
    clearSuggestions()
    await scrollToBottom()
    await socketDriver.sendQuery(finalContent)
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

  const clearAllConversationData = () => {
    // Remove all history localStorage keys (including orphaned ones from previous sessions)
    const keysToRemove = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('cdut-ai-chat-history-')) {
        keysToRemove.push(key)
      }
    }
    keysToRemove.forEach((key) => localStorage.removeItem(key))

    clearAllSessions()
  }

  return {
    input,
    listRef,
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
    selectSession: selectSessionAndRestore,
    selectOrCreateProblemSession,
    ensureSessionMetadata,
    sendMessage,
    sendProblemContextToAi,
    clearAllConversationData,
    closeSocket
  }
}
