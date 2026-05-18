<script setup>
import { computed, ref, watch } from 'vue'
import CodeEditor from './CodeEditor.vue'
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'
import { sanitizeTextInput, sanitizeHtmlContent } from '../utils/validators'

const ALL_LANGUAGES = ['C++', 'C', 'Java', 'Python3']
const DEFAULT_LANGUAGE = 'C++'
const STARTER_CODE = {
  'C++': '#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}\n',
  'C': '#include <stdio.h>\n\nint main() {\n    \n    return 0;\n}\n',
  'Java': 'import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}\n',
  'Python3': '# Read input\n# n = int(input())\n# Process\n# Print output\n'
}

const TEMPLATE_MARKERS = {
  prependBegin: '//PREPEND BEGIN', prependEnd: '//PREPEND END',
  templateBegin: '//TEMPLATE BEGIN', templateEnd: '//TEMPLATE END',
  appendBegin: '//APPEND BEGIN', appendEnd: '//APPEND END'
}

const {
  problems, problemDetail, problemDetailLoading,
  submitLoading, submitResultBySessionId,
  getSubmitResultForSession, setSubmitResultForSession,
  fetchProblemDetail, submitSolution, reportSubmissionToFallback
} = useOjStore()

const {
  sessions, currentSessionId, messages,
  addPendingAttachment, clearPendingAttachments
} = useChatStore()

const rightPanelTab = ref('problem')
const langDropdownOpen = ref(false)
const activeSubmitLanguage = ref(DEFAULT_LANGUAGE)
const codes = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
const templateRawByLanguage = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
const activeSubmitState = ref({ type: '', message: '' })

// Find the problem ID from the currently active session
const selectedProblemId = computed(() => {
  const session = sessions.value.find((s) => s.id === currentSessionId.value)
  return session?.problemId ? String(session.problemId) : ''
})

const selectedProblem = computed(() =>
  problems.value.find((item) => String(item._id) === selectedProblemId.value) || null
)

const hasSelectedProblem = computed(() => Boolean(selectedProblem.value))

const problemDetailData = computed(() => {
  if (problemDetail.value && String(problemDetail.value._id) === String(selectedProblemId.value)) {
    return problemDetail.value
  }
  return selectedProblem.value
})

const selectedProblemDescription = computed(() => {
  const detail = problemDetailData.value
  if (!detail) return ''
  const candidate = detail.description || detail.content || detail.desc || detail.problem_description || ''
  return String(candidate).trim() || '暂无题目描述'
})

const selectedProblemDescriptionHtml = computed(() => sanitizeHtmlContent(selectedProblemDescription.value))
const selectedProblemInputDesc = computed(() => String(problemDetailData.value?.input_description || '').trim())
const selectedProblemInputHtml = computed(() => sanitizeHtmlContent(selectedProblemInputDesc.value))
const selectedProblemOutputDesc = computed(() => String(problemDetailData.value?.output_description || '').trim())
const selectedProblemOutputHtml = computed(() => sanitizeHtmlContent(selectedProblemOutputDesc.value))
const selectedProblemHint = computed(() => String(problemDetailData.value?.hint || '').trim())
const selectedProblemHintHtml = computed(() => sanitizeHtmlContent(selectedProblemHint.value))
const selectedProblemSource = computed(() => String(problemDetailData.value?.source || '').trim())

const selectedProblemSamples = computed(() => {
  const raw = problemDetailData.value?.samples
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return [] }
  }
  return []
})

const submitResult = computed(() => getSubmitResultForSession(currentSessionId.value))

const extractEditableTemplateSection = (code) => {
  const text = String(code || '')
  const begin = text.indexOf(TEMPLATE_MARKERS.templateBegin)
  const end = text.indexOf(TEMPLATE_MARKERS.templateEnd)
  if (begin === -1 || end === -1 || end <= begin) return text
  let editable = text.slice(begin + TEMPLATE_MARKERS.templateBegin.length, end)
  editable = editable.replace(/^\s*\n/, '').replace(/\n\s*$/, '\n')
  return editable
}

const buildSubmissionCode = (templateRaw, editableSection) => {
  const tpl = String(templateRaw || '')
  if (!tpl) return String(editableSection || '')
  const begin = tpl.indexOf(TEMPLATE_MARKERS.templateBegin)
  const end = tpl.indexOf(TEMPLATE_MARKERS.templateEnd)
  if (begin === -1 || end === -1 || end <= begin) return String(editableSection || '')
  const editable = String(editableSection || '').replace(/\s+$/, '')
  return `${tpl.slice(0, begin + TEMPLATE_MARKERS.templateBegin.length)}\n${editable}\n${tpl.slice(end)}`
}

const getStarterCode = (problem, language) => {
  const tpl = problem?.template || {}
  return tpl[language] || STARTER_CODE[language] || ''
}

const loadedSessionProblemKey = ref('')
let problemDetailRequestSeq = 0

const buildSessionProblemKey = (sessionId, problemId) => `${String(sessionId || '')}::${String(problemId || '')}`

const resetStarterCodes = () => {
  for (const lang of ALL_LANGUAGES) {
    codes.value[lang] = ''
    templateRawByLanguage.value[lang] = ''
  }
  activeSubmitLanguage.value = DEFAULT_LANGUAGE
  loadedSessionProblemKey.value = ''
}

const applyStarterCodesFromProblem = (problemSource) => {
  if (!problemSource?._id) return
  const pid = String(problemSource._id)
  for (const lang of ALL_LANGUAGES) {
    const starterRaw = getStarterCode(problemSource, lang)
    codes.value[lang] = extractEditableTemplateSection(starterRaw)
    templateRawByLanguage.value[lang] = starterRaw
  }
  activeSubmitLanguage.value = DEFAULT_LANGUAGE
  loadedSessionProblemKey.value = buildSessionProblemKey(currentSessionId.value, pid)
}

watch(
  [() => currentSessionId.value, () => selectedProblemId.value],
  async ([sessionId, pid]) => {
    if (!pid) {
      resetStarterCodes()
      return
    }

    const expectedKey = buildSessionProblemKey(sessionId, pid)
    const requestSeq = ++problemDetailRequestSeq

    const detail = await fetchProblemDetail(String(pid))

    if (requestSeq !== problemDetailRequestSeq) return
    if (buildSessionProblemKey(currentSessionId.value, selectedProblemId.value) !== expectedKey) return

    if (detail?._id && String(detail._id) === String(pid)) {
      applyStarterCodesFromProblem(detail)
      return
    }

    if (selectedProblem.value?._id && String(selectedProblem.value._id) === String(pid)) {
      applyStarterCodesFromProblem(selectedProblem.value)
    }
  },
  { immediate: true }
)

watch(
  () => problemDetail.value,
  (detail) => {
    if (!detail?._id) return
    const pid = String(selectedProblemId.value || '')
    if (!pid || String(detail._id) !== pid) return

    const expectedKey = buildSessionProblemKey(currentSessionId.value, pid)
    if (loadedSessionProblemKey.value === expectedKey) return

    applyStarterCodesFromProblem(detail)
  },
  { immediate: true }
)

const handleSubmitCode = async () => {
  activeSubmitState.value = { type: '', message: '' }
  if (!selectedProblem.value) {
    activeSubmitState.value = { type: 'error', message: 'Please select a problem first.' }
    return
  }
  const normalizedEditableCode = sanitizeTextInput(codes.value[activeSubmitLanguage.value], 20000)
  codes.value[activeSubmitLanguage.value] = normalizedEditableCode
  if (normalizedEditableCode.length < 10) {
    activeSubmitState.value = { type: 'error', message: 'Code must be at least 10 characters.' }
    return
  }
  const templateRaw = templateRawByLanguage.value[activeSubmitLanguage.value] || ''
  const normalizedCode = sanitizeTextInput(buildSubmissionCode(templateRaw, normalizedEditableCode), 20000)

  const result = await submitSolution({
    problemId: selectedProblem.value.id,
    problemQueryId: selectedProblem.value._id,
    language: activeSubmitLanguage.value,
    code: normalizedCode,
    sessionId: currentSessionId.value
  })

  activeSubmitState.value = mapSubmissionLabelToUiMessage(result)

  if (!result || !result.label || !currentSessionId.value) return

  const language = activeSubmitLanguage.value
  const ext = language === 'C++' ? 'cpp' : language === 'C' ? 'c' : language === 'Java' ? 'java' : 'py'
  const codeFilename = `${language.toLowerCase().replace('3', '')}_${selectedProblem.value._id}.${ext}`
  clearPendingAttachments()
  addPendingAttachment({ filename: codeFilename, content: normalizedEditableCode, type: 'code' })

  const resultContent = buildResultAttachmentContent(result)
  if (resultContent) {
    addPendingAttachment({ filename: 'submit-result.txt', content: resultContent, type: 'result' })
  }

  activeSubmitState.value = {
    type: activeSubmitState.value.type || 'info',
    message: `${activeSubmitState.value.message || 'Submission finished.'} 已将代码和判题结果挂载到输入框上方附件，确认后手动发送给 AI。`
  }
}

const mapSubmissionLabelToUiMessage = (result) => {
  if (!result) return { type: 'error', message: 'No submission result returned.' }
  if (result.label === 'ERROR') return { type: 'error', message: result.message || 'Submission failed.' }
  if (result.label === 'TIMEOUT') return { type: 'warning', message: 'Judge polling timed out. Please refresh later.' }
  const detail = `Result: ${result.label} | Score: ${result.score} | Time: ${result.timeCost}ms | Memory: ${result.memoryCost}KB | Submission: ${result.submissionId || '-'}`
  if (result.label === 'ACCEPTED') return { type: 'success', message: detail }
  return { type: 'info', message: detail }
}

const getResultClass = (result) => {
  if (!result || !result.label) return 'result-unknown'
  if (result.label === 'ACCEPTED') return 'result-accepted'
  if (result.label === 'COMPILE_ERROR') return 'result-compile-error'
  if (['WRONG_ANSWER', 'RUNTIME_ERROR', 'CPU_TIME_LIMIT_EXCEEDED', 'REAL_TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED', 'SYSTEM_ERROR', 'PARTIALLY_ACCEPTED'].includes(result.label)) return 'result-wrong'
  if (result.label === 'ERROR') return 'result-error'
  return 'result-unknown'
}

const getTestCaseClass = (tc) => {
  if (tc.status === 0 || tc.label === 'ACCEPTED') return 'tc-passed'
  return 'tc-failed'
}

const formatMemory = (kb) => {
  if (!kb || kb <= 0) return '0KB'
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)}MB`
  return `${kb}KB`
}

const buildResultAttachmentContent = (result) => {
  if (!result) return ''
  const lines = []
  lines.push(`[${result.label}] ${result.display || result.label}`)
  if (result.submissionId) lines.push(`Submission: ${result.submissionId}`)
  if (result.score) lines.push(`Score: ${result.score}`)
  lines.push(`Time: ${result.timeCost}ms | Memory: ${formatMemory(result.memoryCost)}`)
  if (result.errInfo) lines.push(`\nError: ${result.errInfo}`)
  return lines.join('\n')
}
</script>

<template>
  <div class="card side-tab-card">
    <div class="switch-row side-tabs">
      <button :class="{ active: rightPanelTab === 'problem' }" @click="rightPanelTab = 'problem'">题目信息</button>
      <button :class="{ active: rightPanelTab === 'submit' }" @click="rightPanelTab = 'submit'">OJ提交</button>
    </div>
  </div>

  <!-- Problem info tab -->
  <div class="card side-content-card" v-if="rightPanelTab === 'problem'">
    <div class="problem-detail" v-if="hasSelectedProblem">
      <div class="problem-detail-top">
        <div class="card-title">{{ selectedProblem.title }}</div>
        <div class="card-subtitle">Problem ID: {{ selectedProblem._id }}</div>
      </div>

      <div class="problem-detail-middle scrollbar-unified">
        <div class="problem-section-loading" v-if="problemDetailLoading">加载题目详情...</div>

        <div class="problem-section" v-if="selectedProblemDescription">
          <h4 class="problem-section-title">Description</h4>
          <div class="problem-description" v-html="selectedProblemDescriptionHtml" />
        </div>

        <div class="problem-section" v-if="selectedProblemInputDesc">
          <h4 class="problem-section-title">Input</h4>
          <div class="problem-description" v-html="selectedProblemInputHtml" />
        </div>

        <div class="problem-section" v-if="selectedProblemOutputDesc">
          <h4 class="problem-section-title">Output</h4>
          <div class="problem-description" v-html="selectedProblemOutputHtml" />
        </div>

        <div class="problem-section" v-if="selectedProblemSamples.length">
          <div v-for="(sample, idx) in selectedProblemSamples" :key="idx" class="problem-sample-block">
            <div class="problem-sample-item">
              <h4 class="problem-section-title">Sample Input {{ selectedProblemSamples.length > 1 ? idx + 1 : '' }}</h4>
              <pre class="problem-sample-code">{{ sample.input }}</pre>
            </div>
            <div class="problem-sample-item">
              <h4 class="problem-section-title">Sample Output {{ selectedProblemSamples.length > 1 ? idx + 1 : '' }}</h4>
              <pre class="problem-sample-code">{{ sample.output }}</pre>
            </div>
          </div>
        </div>

        <div class="problem-section" v-if="selectedProblemHint">
          <h4 class="problem-section-title">Hint</h4>
          <div class="problem-description" v-html="selectedProblemHintHtml" />
        </div>

        <div class="problem-section problem-source" v-if="selectedProblemSource">
          <span class="problem-source-label">Source:</span> {{ selectedProblemSource }}
        </div>
      </div>

      <div class="problem-detail-bottom">
        <div class="detail-grid compact-detail-grid">
          <div class="detail-row compact-detail-row"><span>难度</span><strong>{{ selectedProblem.difficulty || 'Unknown' }}</strong></div>
          <div class="detail-row compact-detail-row"><span>时间限制</span><strong>{{ selectedProblem.time_limit || '-' }}</strong></div>
          <div class="detail-row compact-detail-row"><span>内存限制</span><strong>{{ selectedProblem.memory_limit || '-' }}</strong></div>
          <div class="detail-row compact-detail-row"><span>提交数</span><strong>{{ selectedProblem.submission_number || 0 }}</strong></div>
          <div class="detail-row compact-detail-row"><span>通过数</span><strong>{{ selectedProblem.accepted_number || 0 }}</strong></div>
          <div class="detail-row compact-detail-row"><span>通过率</span><strong>{{ selectedProblem.submission_number ? `${Math.round((selectedProblem.accepted_number / selectedProblem.submission_number) * 100)}%` : '0%' }}</strong></div>
        </div>
      </div>
    </div>
    <div class="empty" v-else>请先在题库中选择一道题目</div>
  </div>

  <!-- Submit tab -->
  <div class="card side-content-card" v-else>
    <template v-if="hasSelectedProblem">
      <div class="submit-layout">
        <div class="submit-editor-area">
          <div class="submit-form">
            <div class="lang-select-wrap">
              <div
                class="lang-select-trigger"
                :class="{ open: langDropdownOpen }"
                @click="langDropdownOpen = !langDropdownOpen"
                tabindex="0"
                role="combobox"
                :aria-expanded="langDropdownOpen"
              >
                <span class="lang-select-label">{{ activeSubmitLanguage }}</span>
                <span class="lang-select-arrow">▼</span>
              </div>
              <div v-if="langDropdownOpen" class="lang-select-dropdown" @mouseleave="langDropdownOpen = false">
                <div
                  v-for="lang in ALL_LANGUAGES"
                  :key="lang"
                  class="lang-select-option"
                  :class="{ selected: activeSubmitLanguage === lang }"
                  @click="activeSubmitLanguage = lang; langDropdownOpen = false"
                >
                  <span class="lang-select-option-icon" :class="{ cpp: lang === 'C++', c: lang === 'C', java: lang === 'Java', py: lang === 'Python3' }">
                    {{ lang === 'C++' ? '++' : lang[0] }}
                  </span>
                  {{ lang }}
                </div>
              </div>
            </div>

            <CodeEditor
              v-for="lang in ALL_LANGUAGES"
              :key="lang"
              v-show="activeSubmitLanguage === lang"
              v-model="codes[lang]"
              class="oj-code-editor"
              :language="lang"
              placeholder="Enter your source code here"
            />
            <div class="submit-action-row">
              <button :disabled="submitLoading" @click="handleSubmitCode">{{ submitLoading ? '提交中...' : '提交代码' }}</button>
            </div>
          </div>
        </div>

        <!-- Submit result area -->
        <div class="submit-result-area scrollbar-unified">
          <div class="submit-result-empty" v-if="submitLoading">
            <div class="result-spinner"></div>
            <span>Judging...</span>
          </div>

          <div class="submit-result-panel" v-else-if="submitResult" :class="getResultClass(submitResult)">
            <div class="result-header">
              <span class="result-icon">{{ submitResult.icon || '❓' }}</span>
              <span class="result-label">{{ submitResult.display || submitResult.label }}</span>
              <span class="result-submission-id" v-if="submitResult.submissionId">#{{ submitResult.submissionId }}</span>
            </div>
            <div class="result-stats-row">
              <div class="result-stat" v-if="submitResult.score > 0">
                <span class="stat-label">Score</span>
                <span class="stat-value">{{ submitResult.score }}</span>
              </div>
              <div class="result-stat">
                <span class="stat-label">Time</span>
                <span class="stat-value">{{ submitResult.timeCost }}ms</span>
              </div>
              <div class="result-stat">
                <span class="stat-label">Memory</span>
                <span class="stat-value">{{ formatMemory(submitResult.memoryCost) }}</span>
              </div>
            </div>

            <div class="result-error-block" v-if="submitResult.errInfo">
              <div class="error-block-header">
                <span class="error-block-icon">⚠</span>
                <span>{{ submitResult.label === 'COMPILE_ERROR' ? 'Compile Error' : 'Error Details' }}</span>
              </div>
              <pre class="error-block-content">{{ submitResult.errInfo }}</pre>
            </div>

            <div class="result-test-cases" v-if="submitResult.testCases && submitResult.testCases.length > 0">
              <div class="test-cases-header">
                <span class="tc-summary-label">Test Cases</span>
                <span class="tc-pass-count">
                  {{ submitResult.testCases.filter(tc => tc.status === 0 || tc.label === 'ACCEPTED').length }}/{{ submitResult.testCases.length }} passed
                </span>
              </div>
              <div class="tc-progress-bar">
                <div
                  v-for="tc in submitResult.testCases"
                  :key="'bar-' + tc.index"
                  class="tc-progress-segment"
                  :class="getTestCaseClass(tc)"
                  :title="`#${tc.index} ${tc.display}`"
                ></div>
              </div>
            </div>
          </div>

          <div class="submit-result-empty" v-else>
            <span class="empty-icon">📋</span>
            <span>Submit code to see results</span>
          </div>
        </div>
      </div>
    </template>
    <div class="empty" v-else>请先选择题目后再提交代码</div>
  </div>
</template>
