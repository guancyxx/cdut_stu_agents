<script setup>
import { computed, ref } from 'vue'
import { renderMessageContent } from '../utils/validators'

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  isLast: {
    type: Boolean,
    default: false
  }
})

const agentInfo = computed(() => {
  if (!props.message.agent) return null

  return {
    name: props.message.agent.name || 'AI助手',
    icon: props.message.agent.icon || '🤖',
    color: props.message.agent.color || '#666666'
  }
})

const shouldShowAgent = computed(() => {
  return agentInfo.value && props.isLast
})

// Render message content as safe HTML (Markdown / HTML / plain text)
const renderedMessage = computed(() => {
  if (props.message.role === 'trace') return { html: '', contentType: 'text' }

  const result = renderMessageContent(props.message.content)
  return result
})

// Trace: collapsible state
const traceExpanded = ref(false)

const isTrace = computed(() => props.message.role === 'trace')

const traceHasOutput = computed(() => {
  return isTrace.value && props.message.output && props.message.output.trim().length > 0
})

// Map stage to status icon
const traceStatusIcon = computed(() => {
  if (!isTrace.value) return ''
  const stage = props.message.stage || ''
  // Result stages get a checkmark
  if (stage.endsWith('_result')) return '✓'
  // Processing stages get a spinner indicator
  return '⟳'
})

const traceStatusClass = computed(() => {
  if (!isTrace.value) return ''
  const stage = props.message.stage || ''
  return stage.endsWith('_result') ? 'done' : 'running'
})
</script>

<template>
  <!-- Trace message: collapsible step card -->
  <div v-if="isTrace" class="trace-card" :class="traceStatusClass" @click="traceHasOutput && (traceExpanded = !traceExpanded)">
    <div class="trace-header">
      <span class="trace-icon">{{ traceStatusIcon }}</span>
      <span class="trace-title">{{ message.title }}</span>
      <span v-if="message.detail" class="trace-detail">{{ message.detail }}</span>
      <span v-if="traceHasOutput" class="trace-toggle">{{ traceExpanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="traceHasOutput && traceExpanded" class="trace-output">
      <pre>{{ message.output }}</pre>
    </div>
    <div class="message-time">{{ message.time }}</div>
  </div>

  <!-- Normal message bubble -->
  <div v-else class="message-bubble" :class="{
    assistant: message.role === 'assistant',
    user: message.role === 'user',
    'has-agent': shouldShowAgent
  }">
    <!-- Agent header for assistant messages -->
    <div v-if="message.role === 'assistant' && shouldShowAgent" class="agent-header">
      <span class="agent-icon">{{ agentInfo.icon }}</span>
      <span class="agent-name" :style="{ color: agentInfo.color }">{{ agentInfo.name }}</span>
      <span class="agent-badge" :style="{ backgroundColor: agentInfo.color }">当前处理中</span>
    </div>

    <!-- Message content: rendered Markdown/HTML -->
    <div
      class="message-content"
      :class="`content-${renderedMessage.contentType}`"
      v-html="renderedMessage.html"
    />

    <!-- Message time -->
    <div class="message-time">
      {{ message.time }}
    </div>
  </div>
</template>

<style scoped>
/* ---- Trace Card ---- */
.trace-card {
  max-width: 75%;
  padding: 8px 14px;
  border-radius: 10px;
  margin-bottom: 6px;
  align-self: flex-start;
  margin-right: auto;
  cursor: default;
  font-size: 13px;
  border: 1px solid var(--border-subtle, #e8e8e8);
  background: var(--bg-soft, #f9f9fb);
  color: var(--text-secondary, #666);
  transition: border-color 0.2s, background 0.2s;
}

.trace-card.running {
  border-left: 3px solid var(--brand, #4a9eff);
}

.trace-card.done {
  border-left: 3px solid #4caf50;
  opacity: 0.85;
}

.trace-card:hover {
  border-color: var(--border-standard, #d0d0d0);
}

.trace-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.trace-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.running .trace-icon {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.trace-title {
  font-weight: 600;
  color: var(--text-primary, #333);
}

.trace-detail {
  color: var(--text-tertiary, #999);
  font-size: 12px;
}

.trace-toggle {
  margin-left: auto;
  font-size: 10px;
  color: var(--text-tertiary, #999);
  cursor: pointer;
  padding: 2px 4px;
}

.trace-output {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--border-subtle, #eee);
}

.trace-output pre {
  margin: 0;
  padding: 6px 10px;
  background: var(--code-bg, #1e1e2e);
  color: var(--code-fg, #cdd6f4);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  overflow-x: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ---- Normal Message Bubble ---- */
.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 16px;
  margin-bottom: 12px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.message-bubble.assistant {
  background: var(--bg-soft);
  color: var(--text-secondary);
  align-self: flex-start;
  margin-right: auto;
  border: 1px solid var(--border-standard);
}

.message-bubble.assistant.has-agent {
  border-top-left-radius: 4px;
}

.message-bubble.user {
  background: var(--brand);
  color: #fff;
  align-self: flex-end;
  margin-left: auto;
  border: 1px solid transparent;
}

.message-bubble.user:hover {
  background: var(--brand-hover);
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.agent-icon {
  font-size: 16px;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.agent-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  color: white;
  font-weight: 500;
}

.message-content {
  line-height: 1.6;
  word-break: break-word;
  font-size: 14px;
  letter-spacing: -0.165px;
}

/* Plain text: preserve line breaks */
.message-content.content-text {
  white-space: pre-wrap;
}

/* Markdown/HTML content: let the markup control line breaks */
.message-content.content-markdown,
.message-content.content-html {
  white-space: normal;
}

/* --- Markdown typography styles (scoped deep for v-html children) --- */

.message-content.content-markdown :deep(h1),
.message-content.content-html :deep(h1) {
  font-size: 1.4em;
  font-weight: 700;
  margin: 0.6em 0 0.3em;
  line-height: 1.3;
}

.message-content.content-markdown :deep(h2),
.message-content.content-html :deep(h2) {
  font-size: 1.25em;
  font-weight: 700;
  margin: 0.5em 0 0.25em;
  line-height: 1.3;
}

.message-content.content-markdown :deep(h3),
.message-content.content-html :deep(h3) {
  font-size: 1.1em;
  font-weight: 600;
  margin: 0.4em 0 0.2em;
  line-height: 1.3;
}

.message-content.content-markdown :deep(h4),
.message-content.content-markdown :deep(h5),
.message-content.content-markdown :deep(h6),
.message-content.content-html :deep(h4),
.message-content.content-html :deep(h5),
.message-content.content-html :deep(h6) {
  font-size: 1em;
  font-weight: 600;
  margin: 0.3em 0 0.15em;
}

.message-content.content-markdown :deep(p),
.message-content.content-html :deep(p) {
  margin: 0.4em 0;
}

.message-content.content-markdown :deep(ul),
.message-content.content-markdown :deep(ol),
.message-content.content-html :deep(ul),
.message-content.content-html :deep(ol) {
  padding-left: 1.5em;
  margin: 0.4em 0;
}

.message-content.content-markdown :deep(li),
.message-content.content-html :deep(li) {
  margin: 0.15em 0;
}

.message-content.content-markdown :deep(pre),
.message-content.content-html :deep(pre) {
  background: var(--code-bg, #1e1e2e);
  color: var(--code-fg, #cdd6f4);
  border-radius: 8px;
  padding: 12px 16px;
  margin: 0.5em 0;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}

.message-content.content-markdown :deep(code),
.message-content.content-html :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
}

.message-content.content-markdown :deep(:not(pre) > code),
.message-content.content-html :deep(:not(pre) > code) {
  background: var(--code-inline-bg, rgba(135, 135, 135, 0.15));
  color: var(--code-inline-fg, inherit);
  padding: 2px 5px;
  border-radius: 4px;
}

.message-content.content-markdown :deep(blockquote),
.message-content.content-html :deep(blockquote) {
  border-left: 3px solid var(--brand, #4a9eff);
  margin: 0.5em 0;
  padding: 0.3em 1em;
  color: var(--text-tertiary, #888);
}

.message-content.content-markdown :deep(table),
.message-content.content-html :deep(table) {
  border-collapse: collapse;
  margin: 0.5em 0;
  width: 100%;
}

.message-content.content-markdown :deep(th),
.message-content.content-markdown :deep(td),
.message-content.content-html :deep(th),
.message-content.content-html :deep(td) {
  border: 1px solid var(--border-standard, #ddd);
  padding: 6px 10px;
  font-size: 13px;
}

.message-content.content-markdown :deep(th),
.message-content.content-html :deep(th) {
  background: var(--bg-soft, #f5f5f5);
  font-weight: 600;
}

.message-content.content-markdown :deep(a),
.message-content.content-html :deep(a) {
  color: var(--brand, #4a9eff);
  text-decoration: none;
}

.message-content.content-markdown :deep(a:hover),
.message-content.content-html :deep(a:hover) {
  text-decoration: underline;
}

.message-content.content-markdown :deep(img),
.message-content.content-html :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

.message-content.content-markdown :deep(hr),
.message-content.content-html :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-subtle, #eee);
  margin: 0.8em 0;
}

.message-content.content-markdown :deep(strong),
.message-content.content-html :deep(strong) {
  font-weight: 700;
}

.message-content.content-markdown :deep(em),
.message-content.content-html :deep(em) {
  font-style: italic;
}

.message-content.content-markdown :deep(del),
.message-content.content-html :deep(del) {
  text-decoration: line-through;
  opacity: 0.7;
}

/* Task list checkbox styling */
.message-content.content-markdown :deep(input[type="checkbox"]),
.message-content.content-html :deep(input[type="checkbox"]) {
  margin-right: 6px;
  pointer-events: none;
}

.message-time {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
  text-align: right;
}

/* User bubble: adjust code/inline colors for contrast on brand bg */
.message-bubble.user .message-content.content-markdown :deep(pre),
.message-bubble.user .message-content.content-html :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  color: #f0f0f0;
}

.message-bubble.user .message-content.content-markdown :deep(:not(pre) > code),
.message-bubble.user .message-content.content-html :deep(:not(pre) > code) {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.message-bubble.user .message-content.content-markdown :deep(a),
.message-bubble.user .message-content.content-html :deep(a) {
  color: #d0e8ff;
}

.message-bubble.user .message-content.content-markdown :deep(blockquote),
.message-bubble.user .message-content.content-html :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.5);
  color: rgba(255, 255, 255, 0.8);
}

.message-bubble.user .message-content.content-markdown :deep(th),
.message-bubble.user .message-content.content-html :deep(th) {
  background: rgba(0, 0, 0, 0.1);
}

.message-bubble.user .message-content.content-markdown :deep(th),
.message-bubble.user .message-content.content-markdown :deep(td),
.message-bubble.user .message-content.content-html :deep(th),
.message-bubble.user .message-content.content-html :deep(td) {
  border-color: rgba(255, 255, 255, 0.2);
}
</style>