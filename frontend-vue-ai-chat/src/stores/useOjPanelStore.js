import { computed, effectScope, ref, watch } from 'vue'
import { useOjStore } from './ojStore'
import { useChatStore } from './chatStore'
import { sanitizeTextInput, sanitizeHtmlContent } from '../utils/validators'

export const ALL_LANGUAGES = ['C++', 'C', 'Java', 'Python3']
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

function createOjPanelState() {
  const {
    problems, problemDetail, problemDetailLoading,
    submitLoading, getSubmitResultForSession,
    fetchProblemDetail, submitSolution
  } = useOjStore()

  const {
    sessions, currentSessionId,
    addPendingAttachment, clearPendingAttachments
  } = useChatStore()

  const langDropdownOpen = ref(false)
  const activeSubmitLanguage = ref(DEFAULT_LANGUAGE)
  const codes = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
  const templateRawByLanguage = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
  const activeSubmitState = ref({ type: '', message: '' })
  const loadedSessionProblemKey = ref('')
  let problemDetailRequestSeq = 0

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

  const buildSessionProblemKey = (sessionId, problemId) =>
    `${String(sessionId || '')}::${String(problemId || '')}`

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
      if (!pid) { resetStarterCodes(); return }
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

  const mapSubmissionLabelToUiMessage = (result) => {
    if (!result) return { type: 'error', message: 'No submission result returned.' }
    if (result.label === 'ERROR') return { type: 'error', message: result.message || 'Submission failed.' }
    if (result.label === 'TIMEOUT') return { type: 'warning', message: 'Judge polling timed out. Please refresh later.' }
    const detail = `Result: ${result.label} | Score: ${result.score} | Time: ${result.timeCost}ms | Memory: ${result.memoryCost}KB | Submission: ${result.submissionId || '-'}`
    if (result.label === 'ACCEPTED') return { type: 'success', message: detail }
    return { type: 'info', message: detail }
  }

  const formatMemory = (kb) => {
    if (!kb || kb <= 0) return '0KB'
    if (kb >= 1024) return `${(kb / 1024).toFixed(1)}MB`
    return `${kb}KB`
  }

  const buildResultAttachmentContent = (result) => {
    if (!result) return ''
    const lines = [
      `[${result.label}] ${result.display || result.label}`,
      ...(result.submissionId ? [`Submission: ${result.submissionId}`] : []),
      ...(result.score ? [`Score: ${result.score}`] : []),
      `Time: ${result.timeCost}ms | Memory: ${formatMemory(result.memoryCost)}`,
      ...(result.errInfo ? [`\nError: ${result.errInfo}`] : [])
    ]
    return lines.join('\n')
  }

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

  const getResultClass = (result) => {
    if (!result || !result.label) return 'result-unknown'
    if (result.label === 'ACCEPTED') return 'result-accepted'
    if (result.label === 'COMPILE_ERROR') return 'result-compile-error'
    if (['WRONG_ANSWER', 'RUNTIME_ERROR', 'CPU_TIME_LIMIT_EXCEEDED', 'REAL_TIME_LIMIT_EXCEEDED',
      'MEMORY_LIMIT_EXCEEDED', 'SYSTEM_ERROR', 'PARTIALLY_ACCEPTED'].includes(result.label)) return 'result-wrong'
    if (result.label === 'ERROR') return 'result-error'
    return 'result-unknown'
  }

  const getTestCaseClass = (tc) =>
    (tc.status === 0 || tc.label === 'ACCEPTED') ? 'tc-passed' : 'tc-failed'

  return {
    ALL_LANGUAGES,
    problemDetailLoading,
    submitLoading,
    langDropdownOpen,
    activeSubmitLanguage,
    codes,
    activeSubmitState,
    hasSelectedProblem,
    selectedProblem,
    selectedProblemDescriptionHtml,
    selectedProblemInputDesc,
    selectedProblemInputHtml,
    selectedProblemOutputDesc,
    selectedProblemOutputHtml,
    selectedProblemHint,
    selectedProblemHintHtml,
    selectedProblemSource,
    selectedProblemSamples,
    submitResult,
    getResultClass,
    getTestCaseClass,
    formatMemory,
    handleSubmitCode
  }
}

// ponytail: effectScope detaches watchers from any component lifecycle
let _state = null
export function useOjPanelStore() {
  if (!_state) {
    const scope = effectScope(true)
    _state = scope.run(() => createOjPanelState())
  }
  return _state
}
