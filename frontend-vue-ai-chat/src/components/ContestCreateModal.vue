<template>
  <div class="contest-modal-overlay" @click.self="$emit('close')">
    <div class="contest-modal" role="dialog" aria-label="Create contest">
      <div class="contest-modal-header">
        <h3>新增比赛</h3>
        <button class="modal-close-btn" @click="$emit('close')" aria-label="Close">×</button>
      </div>

      <div class="contest-modal-tabs">
        <button :class="{ active: activeTab === 'info' }" @click="activeTab = 'info'">比赛信息</button>
        <button :class="{ active: activeTab === 'problems' }" @click="activeTab = 'problems'">题目信息</button>
      </div>

      <div class="contest-modal-body">
        <div v-if="state.message" :class="['alert', state.type === 'error' ? 'alert-error' : 'alert-success']">
          {{ state.message }}
        </div>

        <section v-if="activeTab === 'info'" class="contest-tab-pane">
          <div class="form-grid">
            <label class="form-group">
              <span class="label-text">比赛标题 *</span>
              <input v-model="form.title" placeholder="例如：2026 春季训练赛 Round 1" maxlength="255" :disabled="submitting" />
            </label>

            <label class="form-group">
              <span class="label-text">比赛描述</span>
              <textarea v-model="form.description" placeholder="可选，简要说明比赛主题和规则" rows="3" maxlength="1000" :disabled="submitting" />
            </label>

            <div class="form-row-2">
              <label class="form-group">
                <span class="label-text">开始时间 *</span>
                <input v-model="form.startTime" type="datetime-local" :disabled="submitting" />
              </label>
              <label class="form-group">
                <span class="label-text">结束时间 *</span>
                <input v-model="form.endTime" type="datetime-local" :disabled="submitting" />
              </label>
            </div>

            <span v-if="timeError" class="field-hint field-hint-error">{{ timeError }}</span>

            <label class="form-group-check">
              <input v-model="form.visible" type="checkbox" :disabled="submitting" />
              <span class="label-text">对学生可见</span>
            </label>
          </div>
        </section>

        <section v-else class="contest-tab-pane problem-pane">
          <div class="problem-pane-layout">
            <aside class="selected-problem-pane">
              <div class="pane-title-row">
                <h4>已选题目 ({{ selectedProblems.length }})</h4>
              </div>
              <div class="selected-problem-list">
                <div v-for="(pid, idx) in selectedProblems" :key="pid" class="selected-problem-card">
                  <div class="selected-problem-index">{{ idx + 1 }}</div>
                  <div class="selected-problem-main">
                    <div class="problem-id">{{ pid }}</div>
                    <div class="problem-title">{{ selectedProblemMetaMap[pid]?.title || '未命名题目' }}</div>
                  </div>
                  <button class="remove-btn" @click="toggleProblem(pid)" :disabled="submitting">移除</button>
                </div>
                <div v-if="!selectedProblems.length" class="empty-tip">请从右侧题库中选择题目</div>
              </div>
            </aside>

            <section class="browser-problem-pane">
              <div class="problem-filter-row">
                <input
                  v-model="problemKeyword"
                  placeholder="按题号或标题筛选"
                  class="search-input"
                  :disabled="submitting"
                  @keydown.enter="searchProblems"
                />
                <select v-model="problemDifficulty" class="difficulty-select" :disabled="submitting">
                  <option value="">全部难度</option>
                  <option value="Low">Low</option>
                  <option value="Mid">Mid</option>
                  <option value="High">High</option>
                </select>
                <button class="btn-search" :disabled="submitting || problemSearching" @click="searchProblems">
                  {{ problemSearching ? '筛选中...' : '筛选' }}
                </button>
              </div>

              <div class="problem-card-grid">
                <button
                  v-for="p in problemSearchResults"
                  :key="p._id"
                  class="problem-grid-card"
                  :class="{ selected: isProblemSelected(p._id) }"
                  :disabled="submitting"
                  @click="toggleProblem(p._id)"
                >
                  <span class="selector-dot" :class="{ checked: isProblemSelected(p._id) }"></span>
                  <div class="grid-card-head">
                    <span class="problem-id">{{ p._id }}</span>
                    <span class="problem-diff" :class="String(p.difficulty || '').toLowerCase()">{{ p.difficulty || 'Low' }}</span>
                  </div>
                  <div class="problem-title">{{ p.title || 'Untitled Problem' }}</div>
                </button>
                <div v-if="!problemSearching && !problemSearchResults.length" class="empty-tip">未找到匹配题目</div>
              </div>
            </section>
          </div>
        </section>
      </div>

      <div class="contest-modal-footer">
        <button class="btn-cancel" @click="$emit('close')" :disabled="submitting">取消</button>
        <button class="btn-submit" :disabled="submitting || !canSubmit" @click="handleSubmit">
          {{ submitting ? '创建中...' : '创建比赛' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { createApiClient } from '../services/apiClient'
import { sanitizeTextInput } from '../utils/validators'

const props = defineProps({
  apiBaseUrl: { type: String, default: '/oj-api' },
  agentApiBaseUrl: { type: String, default: '/oj-test-cases' }
})

const emit = defineEmits(['close', 'created'])
const apiClient = createApiClient(props.apiBaseUrl, props.agentApiBaseUrl)

const activeTab = ref('info')
const submitting = ref(false)
const state = ref({ type: '', message: '' })

const form = ref({
  title: '',
  description: '',
  startTime: '',
  endTime: '',
  visible: true
})

const problemKeyword = ref('')
const problemDifficulty = ref('')
const problemSearching = ref(false)
const problemSearchResults = ref([])
const selectedProblems = ref([])
const selectedProblemMetaMap = ref({})

const timeError = computed(() => {
  if (!form.value.startTime || !form.value.endTime) return ''
  const st = form.value.startTime.includes('T') ? `${form.value.startTime}:00` : form.value.startTime
  const et = form.value.endTime.includes('T') ? `${form.value.endTime}:00` : form.value.endTime
  if (st >= et) return '结束时间必须晚于开始时间'
  return ''
})

const canSubmit = computed(() => {
  const hasTitle = form.value.title.trim().length > 0
  const hasStart = form.value.startTime.trim().length > 0
  const hasEnd = form.value.endTime.trim().length > 0
  const hasProblems = selectedProblems.value.length > 0
  return hasTitle && hasStart && hasEnd && hasProblems && !timeError.value && !submitting.value
})

const isProblemSelected = (pid) => selectedProblems.value.includes(String(pid))

const toggleProblem = (pid) => {
  const id = String(pid || '')
  if (!id) return
  const idx = selectedProblems.value.indexOf(id)
  if (idx >= 0) {
    selectedProblems.value.splice(idx, 1)
  } else {
    selectedProblems.value.push(id)
  }
}

const searchProblems = async () => {
  const keyword = sanitizeTextInput(problemKeyword.value, 64)
  const difficulty = sanitizeTextInput(problemDifficulty.value, 16)
  problemSearching.value = true
  try {
    const resp = await apiClient.fetchProblems({
      keyword,
      difficulty,
      limit: '60',
      offset: '0'
    })
    const rows = Array.isArray(resp.data?.data?.results) ? resp.data.data.results : []
    problemSearchResults.value = rows
    const cache = { ...selectedProblemMetaMap.value }
    rows.forEach((item) => {
      if (!item?._id) return
      cache[String(item._id)] = {
        title: sanitizeTextInput(String(item.title || ''), 255),
        difficulty: sanitizeTextInput(String(item.difficulty || ''), 16)
      }
    })
    selectedProblemMetaMap.value = cache
  } catch {
    problemSearchResults.value = []
  } finally {
    problemSearching.value = false
  }
}

const normalizeDateTime = (raw) => {
  const text = sanitizeTextInput(String(raw || ''), 64)
  if (!text) return ''
  return text.includes('T') ? `${text}:00Z` : text
}

const handleSubmit = async () => {
  state.value = { type: '', message: '' }
  if (!canSubmit.value) return

  submitting.value = true
  try {
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

    state.value = { type: 'success', message: `创建成功 (${data.data?.contest_id || 'OK'})` }
    emit('created', data.data)
    setTimeout(() => emit('close'), 1200)
  } catch (e) {
    state.value = { type: 'error', message: e?.message || '创建失败' }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  searchProblems()
})
</script>

<style scoped>
.contest-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.52);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}

.contest-modal {
  width: min(1100px, 96vw);
  max-height: 92vh;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  border: 1px solid var(--border-standard);
  border-radius: 14px;
  background: linear-gradient(180deg, var(--bg-panel) 0%, var(--bg-surface) 100%);
  color: var(--text-primary);
  box-shadow: var(--elevated-shadow);
}

.contest-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.contest-modal-header h3 { margin: 0; font-size: 18px; }

.modal-close-btn {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-soft);
  color: var(--text-secondary);
  cursor: pointer;
}

.contest-modal-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.contest-modal-tabs button {
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-soft);
  color: var(--text-secondary);
  cursor: pointer;
}

.contest-modal-tabs button.active {
  border-color: transparent;
  background: var(--brand);
  color: #fff;
}

.contest-modal-body {
  min-height: 0;
  overflow: auto;
  padding: 14px 16px;
}

.form-grid { display: grid; gap: 10px; }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.form-group { display: grid; gap: 4px; }
.label-text { font-size: 12px; color: var(--text-tertiary); }

.form-group input,
.form-group textarea,
.search-input,
.difficulty-select {
  border: 1px solid var(--border-standard);
  background: var(--input-bg);
  color: var(--text-primary);
  border-radius: 8px;
  padding: 8px 10px;
  font-family: inherit;
}

.form-group-check { display: inline-flex; align-items: center; gap: 8px; margin-top: 4px; }
.field-hint-error { color: var(--danger); font-size: 12px; }

.problem-pane-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 12px;
  min-height: 500px;
}

.selected-problem-pane,
.browser-problem-pane {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-soft);
  min-height: 0;
}

.pane-title-row { padding: 10px 12px; border-bottom: 1px solid var(--border-subtle); }
.pane-title-row h4 { margin: 0; font-size: 13px; color: var(--text-secondary); }

.selected-problem-list {
  padding: 10px;
  display: grid;
  gap: 8px;
  max-height: 430px;
  overflow: auto;
}

.selected-problem-card {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-panel);
}

.selected-problem-index {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-standard);
  color: var(--text-tertiary);
  font-size: 12px;
}

.selected-problem-main .problem-id { font-family: monospace; font-size: 12px; color: var(--brand); }
.selected-problem-main .problem-title {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.remove-btn,
.btn-search,
.btn-cancel,
.btn-submit {
  border: 1px solid var(--border-standard);
  border-radius: 8px;
  background: var(--bg-panel);
  color: var(--text-secondary);
  cursor: pointer;
}

.remove-btn { padding: 4px 8px; font-size: 12px; }

.problem-filter-row {
  padding: 10px;
  border-bottom: 1px solid var(--border-subtle);
  display: grid;
  grid-template-columns: 1fr 130px 84px;
  gap: 8px;
}

.btn-search { font-size: 12px; }

.problem-card-grid {
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 8px;
  max-height: 430px;
  overflow: auto;
}

.problem-grid-card {
  text-align: left;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-panel);
  padding: 8px;
  display: grid;
  gap: 8px;
  cursor: pointer;
}

.problem-grid-card.selected {
  border-color: var(--brand);
  background: var(--brand-subtle-bg);
}

.grid-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.selector-dot {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid var(--border-standard);
  background: transparent;
}

.selector-dot.checked {
  border-color: var(--brand);
  background: radial-gradient(circle, var(--brand) 45%, transparent 48%);
}

.problem-id { font-size: 11px; color: var(--brand); font-family: monospace; }
.problem-title {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  min-height: 34px;
  overflow: hidden;
}

.problem-diff {
  font-size: 11px;
  padding: 2px 6px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  color: var(--text-tertiary);
}

.problem-diff.low { color: var(--success); }
.problem-diff.mid { color: var(--warning); }
.problem-diff.high { color: var(--danger); }

.empty-tip {
  color: var(--text-tertiary);
  font-size: 12px;
  border: 1px dashed var(--border-standard);
  border-radius: 8px;
  padding: 10px;
}

.alert {
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 10px;
  font-size: 12px;
}

.alert-error {
  color: var(--danger);
  background: var(--danger-subtle-bg);
  border: 1px solid var(--border-subtle);
}

.alert-success {
  color: var(--success);
  background: var(--success-subtle-bg);
  border: 1px solid var(--border-subtle);
}

.contest-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-subtle);
}

.btn-cancel,
.btn-submit {
  padding: 8px 14px;
}

.btn-submit {
  border-color: rgba(130, 143, 255, 0.45);
  color: var(--text-primary);
}

@media (max-width: 980px) {
  .problem-pane-layout { grid-template-columns: 1fr; }
  .problem-filter-row { grid-template-columns: 1fr; }
  .form-row-2 { grid-template-columns: 1fr; }
}
</style>
