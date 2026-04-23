<script setup>
import { computed } from 'vue'

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
</script>

<template>
  <div class="message-bubble" :class="{ 
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
    
    <!-- Message content -->
    <div class="message-content">
      {{ message.content }}
    </div>
    
    <!-- Message time -->
    <div class="message-time">
      {{ message.time }}
    </div>
  </div>
</template>

<style scoped>
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
  white-space: pre-wrap;
  line-height: 1.5;
  word-break: break-word;
  font-size: 14px;
  letter-spacing: -0.165px;
}

.message-time {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
  text-align: right;
}
</style>