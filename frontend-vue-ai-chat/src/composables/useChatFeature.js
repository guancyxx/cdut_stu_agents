import { nextTick, ref } from 'vue'
import { useSessions } from './useSessions'
import { useChatSocket } from './useChatSocket'
import { validateChatInput } from '../utils/validators'

const STORAGE_KEY = 'cdut-ai-chat-sessions-v1'

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
    getSessionById,
    appendMessageToSession,
    createTimeLabel
  } = useSessions(STORAGE_KEY)

  const scrollToBottom = async () => {
    await nextTick()
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
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
    createTimeLabel
  })

  const sendMessage = async () => {
    if (sending.value || !currentSession.value) return

    const validation = validateChatInput(input.value)
    if (!validation.valid) return

    appendMessageToSession(currentSessionId.value, {
      role: 'user',
      content: validation.value,
      time: createTimeLabel()
    })

    input.value = ''
    await scrollToBottom()
    await socketDriver.sendQuery(validation.value)
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
    createSession,
    loadSessions,
    selectSession,
    sendMessage,
    closeSocket
  }
}
