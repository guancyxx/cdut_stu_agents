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
            <aside class="problem-col selected-problem-pane">
              <header class="pane-head">
                <span class="pane-head-label">已选题目</span>
                <span class="pane-head-count">{{ selectedProblems.length }}</span>
              </header>
              <div class="pane-body selected-problem-list">
                <div v-for="(pid, idx) in selectedProblems" :key="pid" class="selected-problem-card">
                  <div class="problem-letter">{{ problemLabel(idx) }}</div>
                  <div class="selected-problem-main">
                    <div class="problem-id">{{ pid }}</div>
                    <div
                      class="problem-title"
                      :title="plainText(selectedProblemMetaMap[pid]?.title) || '未命名题目'"
                    >{{ plainText(selectedProblemMetaMap[pid]?.title) || '未命名题目' }}</div>
                  </div>
                  <button class="remove-btn" @click="toggleProblem(pid)" :disabled="submitting" aria-label="移除题目">移除</button>
                </div>
                <div v-if="!selectedProblems.length" class="empty-state">
                  <div class="empty-state-mark">A</div>
                  <p class="empty-state-text">从右侧题库挑选题目<br />入选题目将按 A、B、C 顺序排定</p>
                </div>
              </div>
            </aside>

            <section class="problem-col browser-problem-pane">
              <header class="pane-head">
                <span class="pane-head-label">题库</span>
                <span class="pane-head-count">{{ problemSearchResults.length }}</span>
              </header>
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

              <div class="pane-body problem-card-grid">
                <button
                  v-for="p in problemSearchResults"
                  :key="p._id"
                  class="problem-grid-card"
                  :class="{ selected: isProblemSelected(p._id) }"
                  :disabled="submitting"
                  @click="toggleProblem(p._id)"
                  @mouseenter="showProblemPopup(p, $event)"
                  @mouseleave="hideProblemPopup"
                  @focus="showProblemPopup(p, $event)"
                  @blur="hideProblemPopup"
                >
                  <div class="grid-card-head">
                    <span class="problem-id">{{ p._id }}</span>
                    <span class="problem-diff" :class="String(p.difficulty || '').toLowerCase()">{{ p.difficulty || 'Low' }}</span>
                  </div>
                  <div class="problem-title">{{ plainText(p.title) || 'Untitled Problem' }}</div>
                  <span class="card-select-flag" :class="{ checked: isProblemSelected(p._id) }">
                    {{ isProblemSelected(p._id) ? '已选 ✓' : '点击选择' }}
                  </span>
                </button>
                <div v-if="!problemSearching && !problemSearchResults.length" class="empty-state">
                  <div class="empty-state-mark">?</div>
                  <p class="empty-state-text">未找到匹配题目<br />换个题号或难度再试</p>
                </div>
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

    <Teleport to="body">
      <div
        v-if="hoverPid"
        class="problem-popover"
        :style="{ top: hoverPos.top + 'px', left: hoverPos.left + 'px' }"
      >
        <template v-if="hoverIsLoading && !hoverDetail">
          <div class="popover-loading">加载题目详情…</div>
        </template>
        <template v-else-if="hoverDetail">
          <div class="popover-head">
            <span class="problem-id">{{ hoverPid }}</span>
            <span class="problem-diff" :class="String(hoverDetail.difficulty || '').toLowerCase()">
              {{ hoverDetail.difficulty || 'Low' }}
            </span>
          </div>
          <h5 class="popover-title">{{ hoverDetail.title }}</h5>
          <p class="popover-desc">{{ hoverDetail.description }}</p>
          <div v-if="hoverDetail.timeLimit || hoverDetail.memoryLimit" class="popover-meta">
            <span v-if="hoverDetail.timeLimit">⏱ {{ hoverDetail.timeLimit }} ms</span>
            <span v-if="hoverDetail.memoryLimit">▢ {{ hoverDetail.memoryLimit }} MB</span>
          </div>
        </template>
      </div>
    </Teleport>
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

// Contest-style ordering label: A, B, C … then numeric fallback past Z.
const problemLabel = (idx) => (idx < 26 ? String.fromCharCode(65 + idx) : String(idx + 1))

// Strip markup/entities so list titles and the popup show clean text (the题库
// stores HTML-ish descriptions, hence stray &nbsp; / tags).
const plainText = (raw) => {
  const t = String(raw || '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
  return t.replace(/\s+/g, ' ').trim()
}

// --- hover preview popup (lazy-loads full problem detail, cached per id) ---
const hoverPid = ref('')
const hoverPos = ref({ top: 0, left: 0 })
const problemDetailMap = ref({})
const detailLoading = ref({})

const hoverDetail = computed(() => problemDetailMap.value[hoverPid.value] || null)
const hoverIsLoading = computed(() => !!detailLoading.value[hoverPid.value])

const POPUP_WIDTH = 320

const showProblemPopup = (p, evt) => {
  const id = String(p._id)
  hoverPid.value = id

  const rect = evt.currentTarget.getBoundingClientRect()
  const fitsRight = rect.right + 12 + POPUP_WIDTH <= window.innerWidth
  hoverPos.value = {
    top: Math.max(12, Math.min(rect.top, window.innerHeight - 240)),
    left: fitsRight ? rect.right + 12 : Math.max(12, rect.left - POPUP_WIDTH - 12)
  }

  if (problemDetailMap.value[id] || detailLoading.value[id]) return
  detailLoading.value = { ...detailLoading.value, [id]: true }
  apiClient
    .fetchProblemDetail(id)
    .then((resp) => {
      const d = resp?.data?.data || {}
      problemDetailMap.value = {
        ...problemDetailMap.value,
        [id]: {
          title: plainText(d.title || p.title || 'Untitled Problem'),
          difficulty: d.difficulty || p.difficulty || 'Low',
          description: plainText(d.description) || '该题目暂无描述',
          timeLimit: d.time_limit,
          memoryLimit: d.memory_limit
        }
      }
    })
    .catch(() => {
      problemDetailMap.value = {
        ...problemDetailMap.value,
        [id]: {
          title: plainText(p.title || 'Untitled Problem'),
          difficulty: p.difficulty || 'Low',
          description: '加载详情失败'
        }
      }
    })
    .finally(() => {
      const next = { ...detailLoading.value }
      delete next[id]
      detailLoading.value = next
    })
}

const hideProblemPopup = () => {
  hoverPid.value = ''
}

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
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 14px;
  height: clamp(380px, 56vh, 520px);
}

/* Both panes share the same column skeleton: fixed head + scrolling body. */
.problem-col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--bg-soft);
  overflow: hidden;
}

.pane-head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.pane-head-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.pane-head-count {
  min-width: 20px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--brand-subtle-bg);
  color: var(--brand-subtle-text);
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.pane-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  padding: 10px;
}

/* ---- selected column ---- */
.selected-problem-list { display: grid; gap: 7px; align-content: start; }

.selected-problem-card {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  border-radius: 9px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-panel);
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.selected-problem-card:hover { border-color: var(--border-standard); }

.problem-letter {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--brand);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.selected-problem-main { min-width: 0; }
.selected-problem-main .problem-id { font-family: monospace; font-size: 11px; color: var(--brand); }
.selected-problem-main .problem-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
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

.remove-btn {
  padding: 4px 9px;
  font-size: 12px;
  transition: color var(--motion-fast), border-color var(--motion-fast);
}
.remove-btn:hover:not(:disabled) { color: var(--danger); border-color: var(--danger); }

/* ---- browser column ---- */
.problem-filter-row {
  flex: 0 0 auto;
  padding: 10px;
  border-bottom: 1px solid var(--border-subtle);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px 76px;
  gap: 8px;
}

.btn-search { font-size: 12px; font-weight: 600; }
.btn-search:hover:not(:disabled) { border-color: var(--brand); color: var(--brand-subtle-text); }

.problem-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(176px, 1fr));
  grid-auto-rows: min-content;
  gap: 14px;
  padding: 12px;
}

.problem-grid-card {
  position: relative;
  text-align: left;
  min-height: 116px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-panel);
  padding: 14px 14px 12px;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 12px;
  align-content: start;
  cursor: pointer;
  transition: border-color var(--motion-fast) var(--ease-standard),
    background var(--motion-fast) var(--ease-standard);
}

.problem-grid-card:hover:not(:disabled) { border-color: var(--border-standard); }

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

.problem-id { font-size: 11px; color: var(--brand); font-family: monospace; }
.problem-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.problem-diff {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--text-tertiary);
  background: var(--bg-soft);
}

.problem-diff.low { color: var(--success-subtle-text); background: var(--success-subtle-bg); }
.problem-diff.mid { color: var(--warning-subtle-text); background: var(--warning-subtle-bg); }
.problem-diff.high { color: var(--danger-subtle-text); background: var(--danger-subtle-bg); }

.card-select-flag {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  transition: color var(--motion-fast);
}
.card-select-flag.checked { color: var(--brand-subtle-text); }

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 28px 16px;
  text-align: center;
}

.empty-state-mark {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--border-standard);
  color: var(--text-tertiary);
  font-size: 20px;
  font-weight: 700;
}

.empty-state-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary);
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

/* ---- hover preview popover (teleported to body) ---- */
.problem-popover {
  position: fixed;
  z-index: 1400;
  width: 320px;
  padding: 14px 16px;
  border: 1px solid var(--border-standard);
  border-radius: 12px;
  background: var(--bg-surface);
  box-shadow: var(--elevated-shadow);
  color: var(--text-primary);
  pointer-events: none;
  animation: popover-in var(--motion-fast) var(--ease-emphasized);
}

@keyframes popover-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.popover-loading { font-size: 12px; color: var(--text-tertiary); }

.popover-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.popover-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--text-primary);
}

.popover-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.popover-meta {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--text-tertiary);
}

@media (max-width: 980px) {
  .problem-pane-layout { grid-template-columns: 1fr; height: auto; }
  .problem-col { max-height: 46vh; }
  .problem-filter-row { grid-template-columns: 1fr; }
  .form-row-2 { grid-template-columns: 1fr; }
}
</style>
