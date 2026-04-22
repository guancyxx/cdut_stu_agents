import { ref } from 'vue'

export function useChatSocket({
  getSessionId,
  getSessionById,
  getCurrentUserId,
  updateSessionMeta,
  appendMessageToSession,
  saveSessions,
  scrollToBottom,
  setSending,
  createTimeLabel,
  onAfterMessageAppended
}) {
  const sending = ref(false)

  let socket = null
  let socketBindingKey = ''
  let streamSessionId = ''
  let currentAssistantIndex = -1

  const getWsUrl = (sessionMeta = {}) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = new URL(`${protocol}//${window.location.host}/ws`)

    if (sessionMeta.youtuSessionId) {
      wsUrl.searchParams.set('session_id', String(sessionMeta.youtuSessionId))
    }

    const userId = sessionMeta.userId || getCurrentUserId?.()
    if (userId) {
      wsUrl.searchParams.set('user_id', String(userId))
    }

    return wsUrl.toString()
  }

  const resetStreamState = () => {
    sending.value = false
    setSending(false)
    currentAssistantIndex = -1
  }

  const ensureSocket = (sessionMeta = {}) => {
    const bindingSessionId = String(sessionMeta.youtuSessionId || '')
    const bindingUserId = String(sessionMeta.userId || getCurrentUserId?.() || '')
    const nextBindingKey = `${bindingSessionId}::${bindingUserId}`

    if (socket && socket.readyState === WebSocket.OPEN && socketBindingKey && socketBindingKey !== nextBindingKey) {
      socket.close()
      socket = null
      socketBindingKey = ''
    }

    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return socket
    }

    socketBindingKey = nextBindingKey
    socket = new WebSocket(getWsUrl(sessionMeta))

    socket.onmessage = async (eventPayload) => {
      let eventData
      try {
        eventData = JSON.parse(eventPayload.data)
      } catch (error) {
        console.warn('Invalid WebSocket payload.', error)
        return
      }

      const targetSessionId = streamSessionId || getSessionId()
      const targetSession = getSessionById(targetSessionId)
      if (!targetSession) return

      if (eventData.type === 'init') {
        const serverSessionId = eventData.data?.session_id
        if (serverSessionId && targetSession?.id) {
          updateSessionMeta?.(targetSession.id, {
            youtuSessionId: String(serverSessionId)
          })
          saveSessions()
        }
        return
      }

      if (eventData.type === 'raw' && eventData.data?.type === 'text') {
        if (currentAssistantIndex === -1) {
          targetSession.messages.push({
            role: 'assistant',
            content: '',
            time: createTimeLabel()
          })
          currentAssistantIndex = targetSession.messages.length - 1
        }

        if (eventData.data.delta) {
          targetSession.messages[currentAssistantIndex].content += eventData.data.delta
        }

        if (eventData.data.inprogress === false) {
          currentAssistantIndex = -1
        }

        saveSessions()
        onAfterMessageAppended?.(targetSessionId)
        await scrollToBottom()
        return
      }

      if (eventData.type === 'error') {
        targetSession.messages.push({
          role: 'assistant',
          content: `Request failed: ${eventData.data?.message || 'Unknown error'}`,
          time: createTimeLabel()
        })
        resetStreamState()
        saveSessions()
        onAfterMessageAppended?.(targetSessionId)
        await scrollToBottom()
        return
      }

      if (eventData.type === 'finish') {
        resetStreamState()
        saveSessions()
        await scrollToBottom()
      }
    }

    socket.onclose = () => {
      socketBindingKey = ''
      resetStreamState()
    }

    return socket
  }

  const waitForOpen = (activeSocket) => {
    if (activeSocket.readyState === WebSocket.OPEN) return Promise.resolve()

    return new Promise((resolve, reject) => {
      const onOpen = () => {
        activeSocket.removeEventListener('error', onError)
        resolve()
      }
      const onError = () => {
        activeSocket.removeEventListener('open', onOpen)
        reject(new Error('WebSocket connection failed'))
      }
      activeSocket.addEventListener('open', onOpen, { once: true })
      activeSocket.addEventListener('error', onError, { once: true })
    })
  }

  const sendQuery = async (query, options = {}) => {
    const fallbackSessionId = getSessionId()
    const targetSessionId = options.targetSessionId || fallbackSessionId
    const targetSession = getSessionById(targetSessionId)

    if (!targetSession) {
      throw new Error('Target chat session does not exist')
    }

    streamSessionId = targetSessionId
    sending.value = true
    setSending(true)

    try {
      const activeSocket = ensureSocket({
        youtuSessionId: targetSession.youtuSessionId,
        userId: targetSession.userId || getCurrentUserId?.()
      })
      await waitForOpen(activeSocket)
      activeSocket.send(
        JSON.stringify({
          type: 'query',
          content: {
            query
          }
        })
      )
    } catch (error) {
      appendMessageToSession(targetSessionId, {
        role: 'assistant',
        content: `Connection failed: ${error.message || String(error)}`,
        time: createTimeLabel()
      })
      onAfterMessageAppended?.(targetSessionId)
      resetStreamState()
      await scrollToBottom()
    }
  }

  const closeSocket = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close()
    }
    socketBindingKey = ''
  }

  return {
    sending,
    sendQuery,
    closeSocket,
    resetStreamState
  }
}
