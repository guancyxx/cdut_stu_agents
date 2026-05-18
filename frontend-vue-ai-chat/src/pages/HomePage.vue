<script setup>
import { computed } from 'vue'
import MessageBubble from '../components/MessageBubble.vue'
import { useChatStore } from '../stores/chatStore'

const {
  input,
  sending,
  messages,
  currentSessionId,
  sessions,
  pendingAttachments,
  hasPendingAttachments,
  removePendingAttachment,
  nextStepSuggestions,
  sendSuggestion,
  sendMessage
} = useChatStore()

const chatMessages = computed(() => messages.value.filter((m) => m.role !== 'trace'))
const traceMessages = computed(() => messages.value.filter((m) => m.role === 'trace'))
</script>

<template>
  <section class="main-panel home-panel">
    <main class="chat-main">
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
</template>
