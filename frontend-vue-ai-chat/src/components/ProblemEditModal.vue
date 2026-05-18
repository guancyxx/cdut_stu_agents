<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container problem-edit-modal" role="dialog" aria-label="Edit problem">
      <div class="modal-header minimal-header">
        <button class="modal-close-btn" @click="$emit('close')" aria-label="Close">&times;</button>
      </div>

      <div class="modal-body">
        <div v-if="state.message" :class="['alert', state.type === 'error' ? 'alert-error' : 'alert-success']">
          {{ state.message }}
        </div>

        <ProblemFormFields
          :form="form"
          :disabled="saving"
          :available-tags="[]"
          :show-example="false"
        />
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')" :disabled="saving">取消</button>
        <button class="btn-submit" @click="handleSave" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { createApiClient } from '../services/apiClient'
import { sanitizeTextInput } from '../utils/validators'
import ProblemFormFields from './ProblemFormFields.vue'

const props = defineProps({
  problem: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'saved'])

const apiClient = createApiClient(
  import.meta.env.VITE_OJ_API_BASE_URL || '/oj-api',
  import.meta.env.VITE_AGENT_API_BASE_URL || '/oj-test-cases'
)

const saving = ref(false)
const state = ref({ type: '', message: '' })

const normalizeTags = (value) => {
  if (Array.isArray(value)) return value.map((item) => String(item || '').trim()).filter(Boolean)
  if (typeof value === 'string') return value.split(',').map((item) => item.trim()).filter(Boolean)
  return []
}

const normalizePairs = (value) => {
  if (!Array.isArray(value) || !value.length) return [{ input: '', output: '' }]
  return value.map((item) => ({ input: String(item?.input || ''), output: String(item?.output || '') }))
}

const form = reactive({
  problem_id: String(props.problem?._id || props.problem?.id || ''),
  title: sanitizeTextInput(props.problem?.title || '', 128),
  description: String(props.problem?.description || ''),
  input_description: String(props.problem?.input_description || ''),
  output_description: String(props.problem?.output_description || ''),
  hint: String(props.problem?.hint || ''),
  source: sanitizeTextInput(props.problem?.source || '', 128),
  difficulty: sanitizeTextInput(props.problem?.difficulty || 'Low', 16) || 'Low',
  time_limit: Number(props.problem?.time_limit || 1000),
  memory_limit: Number(props.problem?.memory_limit || 256),
  visible: Boolean(props.problem?.visible),
  tags: normalizeTags(props.problem?.tags).join(','),
  samples: normalizePairs(props.problem?.samples),
  test_cases: normalizePairs(props.problem?.test_cases),
  template: {
    C: String(props.problem?.template?.C || ''),
    'C++': String(props.problem?.template?.['C++'] || ''),
    Java: String(props.problem?.template?.Java || ''),
    Python3: String(props.problem?.template?.Python3 || '')
  },
  spj: Boolean(props.problem?.spj),
  spj_language: String(props.problem?.spj_language || ''),
  spj_code: String(props.problem?.spj_code || '')
})

const handleSave = async () => {
  state.value = { type: '', message: '' }

  const pid = sanitizeTextInput(form.problem_id, 64)
  if (!pid) {
    state.value = { type: 'error', message: '题目ID无效' }
    return
  }

  const title = sanitizeTextInput(form.title, 128)
  if (!title) {
    state.value = { type: 'error', message: '标题不能为空' }
    return
  }

  saving.value = true
  try {
    const payload = {
      title,
      description: form.description || '',
      input_description: form.input_description || '',
      output_description: form.output_description || '',
      hint: form.hint || '',
      source: sanitizeTextInput(form.source, 128),
      difficulty: ['Low', 'Mid', 'High'].includes(form.difficulty) ? form.difficulty : 'Low',
      time_limit: Math.max(100, Number(form.time_limit || 1000)),
      memory_limit: Math.max(16, Number(form.memory_limit || 256)),
      visible: Boolean(form.visible),
      tags: normalizeTags(form.tags)
    }

    const resp = await apiClient.adminUpdateProblem(pid, payload)
    const data = resp.data
    if (!resp.ok || data?.error || data?.detail) {
      const msg = data?.detail || data?.error || data?.data || '更新失败'
      state.value = { type: 'error', message: String(msg) }
      return
    }

    state.value = { type: 'success', message: '题目更新成功' }
    emit('saved')
    setTimeout(() => emit('close'), 500)
  } catch (error) {
    state.value = { type: 'error', message: error.message || '网络错误' }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.problem-edit-modal {
  width: min(960px, 95vw);
  max-height: 92vh;
}

.minimal-header {
  min-height: 32px;
  justify-content: flex-end;
  padding-bottom: 0;
  border-bottom: none;
}
</style>
