import { ref } from 'vue'

export function useChatSocket({
  getSessionId,
  getSessionById,
  appendMessageToSession,
  saveSessions,
  scrollToBottom,
  setSending,
  createTimeLabel
}) {
  const sending = ref(false)

  let socket = null
  let streamSessionId = ''
  let currentAssistantIndex = -1

  const getWsUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws`
  }

  const resetStreamState = () => {
    sending.value = false
    setSending(false)
    currentAssistantIndex = -1
  }

  const ensureSocket = () => {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return socket
    }

    socket = new WebSocket(getWsUrl())

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

  const sendQuery = async (query) => {
    const sessionId = getSessionId()
    streamSessionId = sessionId
    sending.value = true
    setSending(true)

    try {
      const activeSocket = ensureSocket()
      await waitForOpen(activeSocket)
      activeSocket.send(
        JSON.stringify({
          type: 'query',
          content: { query }
        })
      )
    } catch (error) {
      appendMessageToSession(sessionId, {
        role: 'assistant',
        content: `Connection failed: ${error.message || String(error)}`,
        time: createTimeLabel()
      })
      resetStreamState()
      await scrollToBottom()
    }
  }

  const closeSocket = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close()
    }
  }

  return {
    sending,
    sendQuery,
    closeSocket,
    resetStreamState
  }
}
