<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container" role="dialog" aria-label="Create contest">
      <div class="modal-header">
        <h3>Create Contest</h3>
        <button class="modal-close-btn" @click="$emit('close')" aria-label="Close">&times;</button>
      </div>

      <div class="modal-body">
        <div v-if="state.message" :class="['alert', state.type === 'error' ? 'alert-error' : 'alert-success']">
          {{ state.message }}
        </div>

        <div class="form-grid">
          <label class="form-group">
            <span class="label-text">Title *</span>
            <input
              v-model="form.title"
              placeholder="e.g. 2026 Spring Training Round 1"
              maxlength="255"
              :disabled="submitting"
            />
          </label>

          <label class="form-group">
            <span class="label-text">Description</span>
            <textarea
              v-model="form.description"
              placeholder="Optional description"
              rows="2"
              maxlength="1000"
              :disabled="submitting"
            />
          </label>

          <label class="form-group">
            <span class="label-text">Start Time *</span>
            <input
              v-model="form.startTime"
              type="datetime-local"
              :disabled="submitting"
            />
          </label>

          <label class="form-group">
            <span class="label-text">End Time *</span>
            <input
              v-model="form.endTime"
              type="datetime-local"
              :disabled="submitting"
            />
            <span v-if="timeError" class="field-hint field-hint-error">{{ timeError }}</span>
          </label>

          <label class="form-group-check">
            <input v-model="form.visible" type="checkbox" :disabled="submitting" />
            <span class="label-text">Visible to students</span>
          </label>
        </div>

        <div class="section-divider">
          <span>Select Problems</span>
        </div>

        <div class="problem-picker">
          <div class="search-row">
            <input
              v-model="problemKeyword"
              placeholder="Search by ID or title..."
              class="search-input"
              :disabled="submitting"
              @keydown.enter="searchProblems"
            />
            <button class="btn-search" :disabled="submitting || problemSearching" @click="searchProblems">
              {{ problemSearching ? 'Searching...' : 'Search' }}
            </button>
          </div>

          <div v-if="problemSearchResults.length" class="search-results">
            <div
              v-for="p in problemSearchResults"
              :key="p._id"
              class="search-item"
              :class="{ selected: isProblemSelected(p._id) }"
            >
              <input
                :id="`problem-${p._id}`"
                type="checkbox"
                :checked="isProblemSelected(p._id)"
                :disabled="submitting"
                @change="toggleProblem(p._id)"
              />
              <label :for="`problem-${p._id}`" class="search-item-label">
                <span class="problem-id">{{ p._id }}</span>
                <span class="problem-title">{{ p.title }}</span>
                <span class="problem-diff" :class="p.difficulty?.toLowerCase()">{{ p.difficulty || 'Low' }}</span>
              </label>
            </div>
          </div>

          <div v-if="selectedProblems.length" class="selected-section">
            <h4>Selected ({{ selectedProblems.length }})</h4>
            <div class="selected-tags">
              <span v-for="pid in selectedProblems" :key="pid" class="selected-tag">
                {{ pid }}
                <button class="tag-remove" @click="toggleProblem(pid)" :disabled="submitting" aria-label="Remove">&times;</button>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')" :disabled="submitting">Cancel</button>
        <button class="btn-submit" :disabled="submitting || !canSubmit" @click="handleSubmit">
          {{ submitting ? 'Creating...' : 'Create Contest' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { createApiClient } from '../services/apiClient'
import { sanitizeTextInput } from '../utils/validators'

const props = defineProps({
  apiBaseUrl: { type: String, default: '/oj-api' },
  agentApiBaseUrl: { type: String, default: '/oj-test-cases' }
})

const emit = defineEmits(['close', 'created'])

const apiClient = createApiClient(props.apiBaseUrl, props.agentApiBaseUrl)

const form = ref({
  title: '',
  description: '',
  startTime: '',
  endTime: '',
  visible: true
})

const submitting = ref(false)
const state = ref({ type: '', message: '' })

const timeError = computed(() => {
  if (!form.value.startTime || !form.value.endTime) return ''
  const st = form.value.startTime.includes('T') ? `${form.value.startTime}:00` : form.value.startTime
  const et = form.value.endTime.includes('T') ? `${form.value.endTime}:00` : form.value.endTime
  if (st && et && st >= et) return 'End time must be after start time'
  return ''
})

const canSubmit = computed(() => {
  const hasTitle = form.value.title.trim().length > 0
  const hasStart = form.value.startTime.trim().length > 0
  const hasEnd = form.value.endTime.trim().length > 0
  const hasProblems = selectedProblems.value.length > 0
  const timeOk = !timeError.value
  return hasTitle && hasStart && hasEnd && hasProblems && timeOk && !submitting.value
})

// Problem search
const problemKeyword = ref('')
const problemSearching = ref(false)
const problemSearchResults = ref([])
const selectedProblems = ref([])

const isProblemSelected = (pid) => selectedProblems.value.includes(String(pid))

const toggleProblem = (pid) => {
  const id = String(pid)
  const idx = selectedProblems.value.indexOf(id)
  if (idx >= 0) {
    selectedProblems.value.splice(idx, 1)
  } else {
    selectedProblems.value.push(id)
  }
}

const searchProblems = async () => {
  const kw = sanitizeTextInput(problemKeyword.value, 64)
  if (!kw) return

  problemSearching.value = true
  try {
    const resp = await apiClient.fetchProblems({ keyword: kw, limit: '50', offset: '0' })
    const rows = Array.isArray(resp.data?.data?.results) ? resp.data.data.results : []
    problemSearchResults.value = rows
  } catch {
    problemSearchResults.value = []
  } finally {
    problemSearching.value = false
  }
}

const handleSubmit = async () => {
  state.value = { type: '', message: '' }
  if (!canSubmit.value) return

  submitting.value = true
  try {
    const normalizeDateTime = (raw) => {
      const text = sanitizeTextInput(String(raw || ''), 64)
      if (!text) return ''
      return text.includes('T') ? `${text}:00Z` : text
    }

    const payload = {
      title: sanitizeTextInput(form.value.title, 255),
      description: sanitizeTextInput(form.value.description, 1000),
      start_time: normalizeDateTime(form.value.startTime),
      end_time: normalizeDateTime(form.value.endTime),
      visible: form.value.visible,
      problem_ids: [...selectedProblems.value]
    }

    const resp = await apiClient.createContest(payload)
    const data = resp.data

    if (data?.error) {
      state.value = { type: 'error', message: typeof data.data === 'string' ? data.data : data.error }
      return
    }

    state.value = { type: 'success', message: `Contest created (${data.data?.contest_id || 'OK'})` }
    emit('created', data.data)

    setTimeout(() => emit('close'), 1500)
  } catch (e) {
    state.value = { type: 'error', message: e.message || 'Failed to create contest' }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: #1e1e2e;
  border-radius: 12px;
  width: min(620px, 95vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  color: #cdd6f4;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #313244;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 1.4rem;
  color: #6c7086;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}

.modal-close-btn:hover { color: #cdd6f4; }

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #313244;
}

.alert {
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 0.85rem;
}
.alert-error { background: rgba(243, 139, 168, 0.15); color: #f38ba8; }
.alert-success { background: rgba(166, 227, 161, 0.15); color: #a6e3a1; }

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group-check {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.label-text {
  font-size: 0.85rem;
  font-weight: 500;
  color: #a6adc8;
}

.form-group input,
.form-group textarea {
  padding: 7px 10px;
  border-radius: 6px;
  border: 1px solid #45475a;
  background: #181825;
  color: #cdd6f4;
  font-size: 0.9rem;
  font-family: inherit;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #89b4fa;
}

.field-hint { font-size: 0.78rem; }
.field-hint-error { color: #f38ba8; }

.section-divider {
  margin: 16px 0 10px;
  border-top: 1px solid #313244;
  text-align: center;
}

.section-divider span {
  position: relative;
  top: -10px;
  background: #1e1e2e;
  padding: 0 10px;
  font-size: 0.82rem;
  color: #6c7086;
}

.problem-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-row {
  display: flex;
  gap: 8px;
}

.search-input {
  flex: 1;
  padding: 7px 10px;
  border-radius: 6px;
  border: 1px solid #45475a;
  background: #181825;
  color: #cdd6f4;
  font-size: 0.9rem;
}

.search-input:focus {
  outline: none;
  border-color: #89b4fa;
}

.btn-search {
  padding: 7px 14px;
  border-radius: 6px;
  border: 1px solid #45475a;
  background: #313244;
  color: #cdd6f4;
  cursor: pointer;
  font-size: 0.85rem;
  white-space: nowrap;
}

.btn-search:hover { background: #45475a; }
.btn-search:disabled { opacity: 0.5; cursor: not-allowed; }

.search-results {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #313244;
  border-radius: 6px;
  background: #181825;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid #11111b;
}

.search-item:last-child { border-bottom: none; }
.search-item.selected { background: rgba(137, 180, 250, 0.08); }

.search-item-label {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  cursor: pointer;
  font-size: 0.85rem;
}

.problem-id {
  color: #89b4fa;
  font-family: monospace;
  font-size: 0.8rem;
  min-width: 70px;
}

.problem-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.problem-diff {
  font-size: 0.72rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: #313244;
}

.problem-diff.low { color: #a6e3a1; }
.problem-diff.mid { color: #f9e2af; }
.problem-diff.high { color: #f38ba8; }

.selected-section {
  border: 1px solid #313244;
  border-radius: 6px;
  padding: 10px;
  background: #181825;
}

.selected-section h4 {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: #a6adc8;
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.selected-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #313244;
  font-size: 0.8rem;
  font-family: monospace;
}

.tag-remove {
  background: none;
  border: none;
  color: #f38ba8;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
}

.btn-cancel,
.btn-submit {
  padding: 8px 18px;
  border-radius: 6px;
  border: 1px solid #45475a;
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-cancel {
  background: #1e1e2e;
  color: #a6adc8;
}

.btn-submit {
  background: #313244;
  color: #cdd6f4;
  border-color: #89b4fa;
}

.btn-submit:hover:not(:disabled) { background: #45475a; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
