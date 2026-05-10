<script setup>
import { ref, computed, onMounted } from 'vue'
import { createApiClient } from '../services/apiClient'

const AGENT_API_BASE_URL = import.meta.env.VITE_AGENT_API_BASE_URL || '/oj-test-cases'
const apiClient = createApiClient(import.meta.env.VITE_OJ_API_BASE_URL || '/oj-api', AGENT_API_BASE_URL)

// Tab state: 'single' | 'batch'
const uploadTab = ref('single')

// ---- Single problem form ----
const form = ref({
  title: '',
  description: '',
  input_description: '',
  output_description: '',
  hint: '',
  source: '',
  difficulty: 'Low',
  time_limit: 1000,
  memory_limit: 256,
  visible: false,
  tags: '',
  samples: [{ input: '', output: '' }],
  test_cases: [{ input: '', output: '' }]
})

const submitting = ref(false)
const submitResult = ref(null)  // { success, problem_id, db_id, message } | { error }

const addSample = () => {
  form.value.samples.push({ input: '', output: '' })
}

const removeSample = (index) => {
  if (form.value.samples.length > 1) {
    form.value.samples.splice(index, 1)
  }
}

const addTestCase = () => {
  form.value.test_cases.push({ input: '', output: '' })
}

const removeTestCase = (index) => {
  if (form.value.test_cases.length > 1) {
    form.value.test_cases.splice(index, 1)
  }
}

const handleSingleSubmit = async () => {
  if (!form.value.title.trim()) {
    submitResult.value = { error: '标题不能为空' }
    return
  }

  submitting.value = true
  submitResult.value = null

  try {
    const payload = {
      title: form.value.title.trim(),
      description: form.value.description,
      input_description: form.value.input_description,
      output_description: form.value.output_description,
      hint: form.value.hint,
      source: form.value.source,
      difficulty: form.value.difficulty,
      time_limit: Number(form.value.time_limit) || 1000,
      memory_limit: Number(form.value.memory_limit) || 256,
      visible: form.value.visible,
      tags: form.value.tags.split(',').map(t => t.trim()).filter(Boolean),
      samples: form.value.samples.filter(s => s.input || s.output),
      test_cases: form.value.test_cases.filter(tc => tc.input || tc.output)
    }

    const response = await apiClient.adminCreateProblem(payload)
    const result = response.data

    if (result?.success) {
      submitResult.value = result
    } else {
      submitResult.value = { error: result?.detail || result?.error || '创建失败' }
    }
  } catch (err) {
    submitResult.value = { error: err.message || '网络错误' }
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  form.value = {
    title: '',
    description: '',
    input_description: '',
    output_description: '',
    hint: '',
    source: '',
    difficulty: 'Low',
    time_limit: 1000,
    memory_limit: 256,
    visible: false,
    tags: '',
    samples: [{ input: '', output: '' }],
    test_cases: [{ input: '', output: '' }]
  }
  submitResult.value = null
}

// ---- Batch import ----
const batchFile = ref(null)
const batchFormat = ref('auto')
const batchTags = ref('')
const batchDifficulty = ref('')
const batchVisible = ref(false)
const batchUploading = ref(false)
const batchTaskId = ref(null)
const batchProgress = ref(null)  // { status, total, imported, skipped, failed, failed_details }
let batchPollTimer = null

const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    batchFile.value = file
  }
}

const handleDrop = (e) => {
  e.preventDefault()
  const file = e.dataTransfer.files[0]
  if (file) {
    batchFile.value = file
  }
}

const handleDragOver = (e) => {
  e.preventDefault()
}

const startBatchImport = async () => {
  if (!batchFile.value) return

  batchUploading.value = true
  batchProgress.value = null

  try {
    const formData = new FormData()
    formData.append('file', batchFile.value)
    formData.append('format', batchFormat.value)
    if (batchTags.value) formData.append('tags', batchTags.value)
    if (batchDifficulty.value) formData.append('difficulty', batchDifficulty.value)
    formData.append('visible', batchVisible.value ? 'true' : 'false')

    const response = await apiClient.adminBatchUpload(formData)
    const result = response.data

    if (result?.task_id) {
      batchTaskId.value = result.task_id
      startPolling(result.task_id)
    } else {
      batchProgress.value = {
        status: 'failed',
        total: 0,
        imported: 0,
        skipped: 0,
        failed: 1,
        failed_details: [{ title: 'N/A', reason: result?.detail || result?.error || '上传失败' }]
      }
    }
  } catch (err) {
    batchProgress.value = {
      status: 'failed',
      total: 0,
      imported: 0,
      skipped: 0,
      failed: 1,
      failed_details: [{ title: 'N/A', reason: err.message || '网络错误' }]
    }
  } finally {
    batchUploading.value = false
  }
}

const startPolling = (taskId) => {
  if (batchPollTimer) clearInterval(batchPollTimer)

  batchPollTimer = setInterval(async () => {
    try {
      const response = await apiClient.adminImportStatus(taskId)
      const result = response.data

      if (result) {
        batchProgress.value = result
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(batchPollTimer)
          batchPollTimer = null
        }
      }
    } catch {
      // Keep polling on transient errors
    }
  }, 2000)
}

const resetBatch = () => {
  batchFile.value = null
  batchTaskId.value = null
  batchProgress.value = null
  if (batchPollTimer) {
    clearInterval(batchPollTimer)
    batchPollTimer = null
  }
}

// ---- Tags list ----
const availableTags = ref([])

onMounted(async () => {
  try {
    const response = await apiClient.adminFetchTags()
    if (response.data?.tags) {
      availableTags.value = response.data.tags.map(t => t.name)
    }
  } catch {
    // Tags loading is non-critical
  }
})

// ---- Computed ----
const isPolling = computed(() => batchPollTimer !== null)

const progressPercent = computed(() => {
  if (!batchProgress.value || !batchProgress.value.total) return 0
  const { imported, skipped, failed, total } = batchProgress.value
  return Math.round(((imported + skipped + failed) / total) * 100)
})
</script>

<template>
  <div class="admin-upload">
    <h2 class="admin-title">题目管理</h2>

    <!-- Sub-tab switcher -->
    <div class="upload-tabs">
      <button
        :class="{ active: uploadTab === 'single' }"
        @click="uploadTab = 'single'"
      >单题上传</button>
      <button
        :class="{ active: uploadTab === 'batch' }"
        @click="uploadTab = 'batch'"
      >批量导入</button>
    </div>

    <!-- ========== Single problem form ========== -->
    <div v-if="uploadTab === 'single'" class="single-form">
      <div class="form-row">
        <label>标题 <span class="required">*</span></label>
        <input v-model="form.title" type="text" placeholder="题目标题" maxlength="128" />
      </div>

      <div class="form-row inline">
        <div class="form-field">
          <label>难度</label>
          <select v-model="form.difficulty">
            <option value="Low">Low（简单）</option>
            <option value="Mid">Mid（中等）</option>
            <option value="High">High（困难）</option>
          </select>
        </div>
        <div class="form-field">
          <label>来源</label>
          <input v-model="form.source" type="text" placeholder="如：蓝桥杯" />
        </div>
      </div>

      <div class="form-row">
        <label>题目描述</label>
        <textarea v-model="form.description" rows="5" placeholder="题目描述（支持HTML）"></textarea>
      </div>

      <div class="form-row">
        <label>输入描述</label>
        <textarea v-model="form.input_description" rows="3" placeholder="输入格式说明"></textarea>
      </div>

      <div class="form-row">
        <label>输出描述</label>
        <textarea v-model="form.output_description" rows="3" placeholder="输出格式说明"></textarea>
      </div>

      <!-- Samples -->
      <div class="form-section">
        <label>样例</label>
        <div v-for="(sample, i) in form.samples" :key="'s'+i" class="sample-row">
          <div class="sample-field">
            <span class="sample-label">输入{{ i + 1 }}</span>
            <textarea v-model="sample.input" rows="2" placeholder="样例输入"></textarea>
          </div>
          <div class="sample-field">
            <span class="sample-label">输出{{ i + 1 }}</span>
            <textarea v-model="sample.output" rows="2" placeholder="样例输出"></textarea>
          </div>
          <button v-if="form.samples.length > 1" class="btn-remove" @click="removeSample(i)">✕</button>
        </div>
        <button class="btn-add" @click="addSample">+ 添加样例</button>
      </div>

      <div class="form-row">
        <label>提示</label>
        <textarea v-model="form.hint" rows="2" placeholder="解题提示（可选）"></textarea>
      </div>

      <!-- Tags -->
      <div class="form-row">
        <label>标签</label>
        <input v-model="form.tags" type="text" placeholder="逗号分隔，如：数学,动态规划" />
        <div v-if="availableTags.length" class="tag-hints">
          可用标签：{{ availableTags.join('、') }}
        </div>
      </div>

      <!-- Test cases -->
      <div class="form-section">
        <label>测试数据</label>
        <div v-for="(tc, i) in form.test_cases" :key="'tc'+i" class="sample-row">
          <div class="sample-field">
            <span class="sample-label">输入{{ i + 1 }}</span>
            <textarea v-model="tc.input" rows="2" placeholder="测试输入"></textarea>
          </div>
          <div class="sample-field">
            <span class="sample-label">输出{{ i + 1 }}</span>
            <textarea v-model="tc.output" rows="2" placeholder="测试输出"></textarea>
          </div>
          <button v-if="form.test_cases.length > 1" class="btn-remove" @click="removeTestCase(i)">✕</button>
        </div>
        <button class="btn-add" @click="addTestCase">+ 添加测试数据</button>
      </div>

      <!-- Limits -->
      <div class="form-row inline">
        <div class="form-field">
          <label>时间限制 (ms)</label>
          <input v-model.number="form.time_limit" type="number" min="100" max="60000" />
        </div>
        <div class="form-field">
          <label>内存限制 (MB)</label>
          <input v-model.number="form.memory_limit" type="number" min="16" max="1024" />
        </div>
      </div>

      <div class="form-row">
        <label class="checkbox-label">
          <input v-model="form.visible" type="checkbox" />
          公开可见
        </label>
      </div>

      <!-- Submit -->
      <div class="form-actions">
        <button class="btn-primary" :disabled="submitting" @click="handleSingleSubmit">
          {{ submitting ? '提交中...' : '提交创建' }}
        </button>
        <button class="btn-secondary" @click="resetForm">重置</button>
      </div>

      <!-- Result -->
      <div v-if="submitResult" class="result-box" :class="submitResult.success ? 'success' : 'error'">
        <template v-if="submitResult.success">
          创建成功！题目ID: {{ submitResult.problem_id }}，数据库ID: {{ submitResult.db_id }}
        </template>
        <template v-else>
          {{ submitResult.error }}
        </template>
      </div>
    </div>

    <!-- ========== Batch import ========== -->
    <div v-if="uploadTab === 'batch'" class="batch-form">
      <div class="form-row inline">
        <div class="form-field">
          <label>格式</label>
          <select v-model="batchFormat">
            <option value="auto">自动检测</option>
            <option value="fps">FPS XML</option>
            <option value="hydro">Hydro ZIP</option>
          </select>
        </div>
        <div class="form-field">
          <label>默认难度</label>
          <select v-model="batchDifficulty">
            <option value="">不覆盖</option>
            <option value="Low">Low（简单）</option>
            <option value="Mid">Mid（中等）</option>
            <option value="High">High（困难）</option>
          </select>
        </div>
      </div>

      <div class="form-row">
        <label>追加标签</label>
        <input v-model="batchTags" type="text" placeholder="逗号分隔，如：蓝桥杯,入门" />
      </div>

      <div class="form-row">
        <label class="checkbox-label">
          <input v-model="batchVisible" type="checkbox" />
          导入后设为公开
        </label>
      </div>

      <!-- File drop zone -->
      <div
        class="drop-zone"
        :class="{ dragging: false }"
        @drop="handleDrop"
        @dragover="handleDragOver"
        @click="$refs.fileInput.click()"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".xml,.zip"
          style="display: none"
          @change="handleFileChange"
        />
        <template v-if="batchFile">
          <div class="file-info">{{ batchFile.name }} ({{ (batchFile.size / 1024).toFixed(1) }} KB)</div>
        </template>
        <template v-else>
          <div class="drop-hint">点击或拖拽上传文件（.xml 或 .zip）</div>
        </template>
      </div>

      <div class="form-actions">
        <button
          class="btn-primary"
          :disabled="!batchFile || batchUploading || isPolling"
          @click="startBatchImport"
        >
          {{ batchUploading ? '上传中...' : isPolling ? '导入中...' : '开始导入' }}
        </button>
        <button class="btn-secondary" @click="resetBatch">重置</button>
      </div>

      <!-- Progress -->
      <div v-if="batchProgress" class="progress-box">
        <div class="progress-bar-wrap">
          <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <div class="progress-text">
          <span v-if="batchProgress.status === 'running'">
            处理中：{{ batchProgress.imported + batchProgress.skipped + batchProgress.failed }} / {{ batchProgress.total }}
          </span>
          <span v-else-if="batchProgress.status === 'completed'">
            导入完成
          </span>
          <span v-else-if="batchProgress.status === 'failed'">
            导入失败
          </span>
          <span v-else-if="batchProgress.status === 'pending'">
            等待处理...
          </span>
        </div>
        <div class="progress-stats">
          <span class="stat-imported">已导入: {{ batchProgress.imported }}</span>
          <span class="stat-skipped">跳过: {{ batchProgress.skipped }}</span>
          <span class="stat-failed">失败: {{ batchProgress.failed }}</span>
          <span>总计: {{ batchProgress.total }}</span>
        </div>
        <div v-if="batchProgress.failed_details?.length" class="failed-details">
          <div class="failed-title">失败详情：</div>
          <div v-for="(item, i) in batchProgress.failed_details" :key="i" class="failed-item">
            {{ item.title }}: {{ item.reason }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-upload {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.admin-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary, #e0e0e0);
}

.upload-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--border-color, #333);
}

.upload-tabs button {
  padding: 8px 20px;
  background: none;
  border: none;
  color: var(--text-secondary, #999);
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}

.upload-tabs button.active {
  color: var(--accent, #4fc3f7);
  border-bottom-color: var(--accent, #4fc3f7);
}

.form-row {
  margin-bottom: 14px;
}

.form-row label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary, #999);
  margin-bottom: 4px;
}

.form-row.inline {
  display: flex;
  gap: 16px;
}

.form-row.inline .form-field {
  flex: 1;
}

.form-row input[type="text"],
.form-row input[type="number"],
.form-row textarea,
.form-row select {
  width: 100%;
  padding: 8px 10px;
  background: var(--input-bg, #1a1a2e);
  border: 1px solid var(--border-color, #333);
  border-radius: 6px;
  color: var(--text-primary, #e0e0e0);
  font-size: 13px;
  box-sizing: border-box;
}

.form-row textarea {
  resize: vertical;
  font-family: 'Consolas', 'Monaco', monospace;
}

.required {
  color: #ef5350;
}

.form-section {
  margin-bottom: 14px;
  padding: 10px;
  background: var(--card-bg, #1e1e30);
  border-radius: 8px;
  border: 1px solid var(--border-color, #333);
}

.form-section > label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary, #999);
  margin-bottom: 8px;
}

.sample-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 8px;
}

.sample-field {
  flex: 1;
}

.sample-label {
  display: block;
  font-size: 11px;
  color: var(--text-muted, #666);
  margin-bottom: 2px;
}

.sample-field textarea {
  width: 100%;
  padding: 6px 8px;
  background: var(--input-bg, #12121f);
  border: 1px solid var(--border-color, #333);
  border-radius: 4px;
  color: var(--text-primary, #e0e0e0);
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  resize: vertical;
  box-sizing: border-box;
}

.btn-add {
  background: none;
  border: 1px dashed var(--border-color, #444);
  color: var(--accent, #4fc3f7);
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-remove {
  background: none;
  border: none;
  color: #ef5350;
  cursor: pointer;
  font-size: 14px;
  padding: 4px;
  margin-top: 16px;
}

.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
}

.tag-hints {
  font-size: 11px;
  color: var(--text-muted, #666);
  margin-top: 4px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.btn-primary {
  padding: 8px 24px;
  background: var(--accent, #4fc3f7);
  color: #000;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 16px;
  background: none;
  color: var(--text-secondary, #999);
  border: 1px solid var(--border-color, #333);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.result-box {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
}

.result-box.success {
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
}

.result-box.error {
  background: rgba(239, 83, 80, 0.15);
  border: 1px solid rgba(239, 83, 80, 0.3);
  color: #ef9a9a;
}

/* Batch import */
.drop-zone {
  padding: 30px;
  border: 2px dashed var(--border-color, #444);
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
  margin-bottom: 14px;
}

.drop-zone:hover {
  border-color: var(--accent, #4fc3f7);
}

.drop-hint {
  color: var(--text-muted, #666);
  font-size: 14px;
}

.file-info {
  color: var(--text-primary, #e0e0e0);
  font-size: 14px;
}

.progress-box {
  margin-top: 16px;
  padding: 14px;
  background: var(--card-bg, #1e1e30);
  border-radius: 8px;
  border: 1px solid var(--border-color, #333);
}

.progress-bar-wrap {
  height: 6px;
  background: var(--border-color, #333);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-bar {
  height: 100%;
  background: var(--accent, #4fc3f7);
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 14px;
  color: var(--text-primary, #e0e0e0);
  margin-bottom: 8px;
}

.progress-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.stat-imported { color: #81c784; }
.stat-skipped { color: #ffd54f; }
.stat-failed { color: #ef9a9a; }

.failed-details {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color, #333);
}

.failed-title {
  font-size: 12px;
  color: var(--text-secondary, #999);
  margin-bottom: 4px;
}

.failed-item {
  font-size: 11px;
  color: #ef9a9a;
  margin-bottom: 2px;
}
</style>
