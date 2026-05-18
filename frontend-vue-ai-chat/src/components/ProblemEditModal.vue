<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container problem-edit-modal" role="dialog" aria-label="Edit problem">
      <div class="modal-header">
        <h3>编辑题目 {{ model.problem_id || '-' }}</h3>
        <button class="modal-close-btn" @click="$emit('close')" aria-label="Close">&times;</button>
      </div>

      <div class="modal-body">
        <div v-if="state.message" :class="['alert', state.type === 'error' ? 'alert-error' : 'alert-success']">
          {{ state.message }}
        </div>

        <div class="form-grid">
          <label class="form-group">
            <span class="label-text">标题</span>
            <input v-model="model.title" maxlength="128" :disabled="saving" />
          </label>

          <div class="form-row-inline">
            <label class="form-group">
              <span class="label-text">难度</span>
              <select v-model="model.difficulty" :disabled="saving">
                <option value="Low">Low</option>
                <option value="Mid">Mid</option>
                <option value="High">High</option>
              </select>
            </label>
            <label class="form-group">
              <span class="label-text">来源</span>
              <input v-model="model.source" :disabled="saving" />
            </label>
          </div>

          <div class="form-row-inline">
            <label class="form-group">
              <span class="label-text">时间限制(ms)</span>
              <input v-model.number="model.time_limit" type="number" min="100" :disabled="saving" />
            </label>
            <label class="form-group">
              <span class="label-text">内存限制(MB)</span>
              <input v-model.number="model.memory_limit" type="number" min="16" :disabled="saving" />
            </label>
          </div>

          <label class="form-group">
            <span class="label-text">题目描述</span>
            <textarea v-model="model.description" rows="4" :disabled="saving" />
          </label>

          <label class="form-group">
            <span class="label-text">输入描述</span>
            <textarea v-model="model.input_description" rows="3" :disabled="saving" />
          </label>

          <label class="form-group">
            <span class="label-text">输出描述</span>
            <textarea v-model="model.output_description" rows="3" :disabled="saving" />
          </label>

          <label class="form-group">
            <span class="label-text">提示</span>
            <textarea v-model="model.hint" rows="2" :disabled="saving" />
          </label>

          <label class="form-group">
            <span class="label-text">标签（逗号分隔）</span>
            <input v-model="model.tagsText" :disabled="saving" placeholder="数学,动态规划" />
          </label>

          <label class="form-group-check">
            <input v-model="model.visible" type="checkbox" :disabled="saving" />
            <span class="label-text">公开可见</span>
          </label>
        </div>
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

const props = defineProps({
  problem: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'saved'])

const apiClient = createApiClient(import.meta.env.VITE_OJ_API_BASE_URL || '/oj-api', import.meta.env.VITE_AGENT_API_BASE_URL || '/oj-test-cases')
const saving = ref(false)
const state = ref({ type: '', message: '' })

const normalizeTags = (value) => {
  if (Array.isArray(value)) return value.map((item) => String(item || '').trim()).filter(Boolean)
  if (typeof value === 'string') return value.split(',').map((item) => item.trim()).filter(Boolean)
  return []
}

const model = reactive({
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
  tagsText: normalizeTags(props.problem?.tags).join(',')
})

const handleSave = async () => {
  state.value = { type: '', message: '' }
  const pid = sanitizeTextInput(model.problem_id, 64)
  if (!pid) {
    state.value = { type: 'error', message: '题目ID无效' }
    return
  }
  if (!sanitizeTextInput(model.title, 128)) {
    state.value = { type: 'error', message: '标题不能为空' }
    return
  }

  saving.value = true
  try {
    const payload = {
      title: sanitizeTextInput(model.title, 128),
      description: model.description || '',
      input_description: model.input_description || '',
      output_description: model.output_description || '',
      hint: model.hint || '',
      source: sanitizeTextInput(model.source, 128),
      difficulty: ['Low', 'Mid', 'High'].includes(model.difficulty) ? model.difficulty : 'Low',
      time_limit: Math.max(100, Number(model.time_limit || 1000)),
      memory_limit: Math.max(16, Number(model.memory_limit || 256)),
      visible: Boolean(model.visible),
      tags: normalizeTags(model.tagsText)
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
  width: min(860px, 95vw);
  max-height: 92vh;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-row-inline {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group input,
.form-group textarea,
.form-group select {
  padding: 7px 10px;
  border-radius: 6px;
  border: 1px solid #45475a;
  background: #181825;
  color: #cdd6f4;
  font-size: 0.9rem;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #89b4fa;
}

.form-group-check {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label-text {
  font-size: 0.82rem;
  color: #a6adc8;
}
</style>
