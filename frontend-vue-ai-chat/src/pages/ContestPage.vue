<script setup>
import { computed, ref } from 'vue'
import CodeEditor from '../components/CodeEditor.vue'
import ContestCreateModal from '../components/ContestCreateModal.vue'
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
  contestList, contestListLoading, contestError,
  currentContestId, contestDetail, contestDetailLoading,
  contestRankRows, contestRankLoading,
  fetchContestDetail, fetchContestRank, joinContest, fetchContests,
  problemDetail, fetchProblemDetail,
  submitSolution, submitLoading, submitResultBySessionId,
  getSubmitResultForSession, setSubmitResultForSession,
  isAdmin
} = useOjStore()

const { currentSessionId } = useChatStore()

const selectedContestProblemId = ref('')
const langDropdownOpen = ref(false)
const showContestCreateModal = ref(false)
const activeSubmitLanguage = ref(DEFAULT_LANGUAGE)
const codes = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
const templateRawByLanguage = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
const activeSubmitState = ref({ type: '', message: '' })

const selectedContest = computed(() => {
  const cid = String(currentContestId.value || '')
  if (!cid) return null
  return contestList.value.find((item) => String(item.id) === cid) || null
})

const contestStatusText = computed(() => {
  const status = String(contestDetail.value?.status || selectedContest.value?.status || '').toLowerCase()
  if (status === 'running') return '进行中'
  if (status === 'upcoming') return '即将开始'
  if (status === 'ended') return '已结束'
  return '-'
})

const selectedContestProblem = computed(() => {
  const rows = Array.isArray(contestDetail.value?.problems) ? contestDetail.value.problems : []
  const pid = String(selectedContestProblemId.value || '')
  if (!pid) return null
  return rows.find((item) => String(item._id) === pid) || null
})

const submitResult = computed(() => getSubmitResultForSession(currentSessionId.value))

const handleContestSelect = async (contestId) => {
  const cid = sanitizeTextInput(String(contestId || ''), 64)
  if (!cid) return
  await fetchContestDetail(cid)
  await fetchContestRank(cid)
  const firstProblem = Array.isArray(contestDetail.value?.problems) ? contestDetail.value.problems[0] : null
  selectedContestProblemId.value = firstProblem?._id ? String(firstProblem._id) : ''
}

const handleContestJoin = async () => {
  const cid = sanitizeTextInput(String(currentContestId.value || ''), 64)
  if (!cid) return
  const ok = await joinContest(cid)
  if (ok) {
    await fetchContestDetail(cid)
    await fetchContestRank(cid)
  }
}

const handleContestProblemPick = async (problem) => {
  if (!problem?._id) return
  selectedContestProblemId.value = String(problem._id)
  await fetchProblemDetail(String(problem._id))
  const source = problemDetail.value && String(problemDetail.value._id) === String(problem._id)
    ? problemDetail.value
    : problem
  for (const lang of ALL_LANGUAGES) {
    const starterRaw = getStarterCode(source, lang)
    codes.value[lang] = extractEditableTemplateSection(starterRaw)
    templateRawByLanguage.value[lang] = starterRaw
  }
}

const getStarterCode = (problem, language) => {
  const tpl = problem?.template || {}
  return tpl[language] || STARTER_CODE[language] || ''
}

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

const handleContestSubmitCode = async () => {
  activeSubmitState.value = { type: '', message: '' }
  if (!selectedContestProblem.value) {
    activeSubmitState.value = { type: 'error', message: '请先选择比赛题目。' }
    return
  }
  if (!currentContestId.value) {
    activeSubmitState.value = { type: 'error', message: 'Invalid contest id.' }
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
    problemId: selectedContestProblem.value.id,
    problemQueryId: selectedContestProblem.value._id,
    language: activeSubmitLanguage.value,
    code: normalizedCode,
    sessionId: currentSessionId.value,
    contestId: currentContestId.value
  })

  activeSubmitState.value = mapSubmissionLabelToUiMessage(result)
  await fetchContestRank(currentContestId.value)
}

const mapSubmissionLabelToUiMessage = (result) => {
  if (!result) return { type: 'error', message: 'No submission result returned.' }
  if (result.label === 'ERROR') return { type: 'error', message: result.message || 'Submission failed.' }
  if (result.label === 'TIMEOUT') return { type: 'warning', message: 'Judge polling timed out. Please refresh later.' }
  const detail = `Result: ${result.label} | Score: ${result.score} | Time: ${result.timeCost}ms | Memory: ${result.memoryCost}KB`
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

const formatMemory = (kb) => {
  if (!kb || kb <= 0) return '0KB'
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)}MB`
  return `${kb}KB`
}

const handleContestRefresh = async () => {
  await fetchContests('all')
  if (currentContestId.value) {
    await fetchContestDetail(currentContestId.value)
    await fetchContestRank(currentContestId.value)
  }
}

const onContestCreated = async (result) => {
  await fetchContests('all')
  if (result?.contest_id) {
    currentContestId.value = result.contest_id
  }
}

// Problem detail computed (shared with right side)
const selectedProblemDescription = computed(() => {
  const detail = problemDetail.value
  if (!detail) return ''
  return String(detail.description || detail.content || detail.desc || detail.problem_description || '').trim() || '暂无题目描述'
})

const selectedProblemDescriptionHtml = computed(() => sanitizeHtmlContent(selectedProblemDescription.value))
</script>

<template>
  <section class="contest-screen">
    <div class="contest-layout">
      <div class="contest-left card">
        <div class="contest-head-row">
          <h3>比赛列表</h3>
          <button @click="handleContestRefresh" :disabled="contestListLoading">刷新</button>
        </div>
        <div class="contest-list" v-if="!contestListLoading">
          <button
            v-for="item in contestList"
            :key="item.id"
            class="contest-item"
            :class="{ active: String(item.id) === String(currentContestId) }"
            @click="handleContestSelect(item.id)"
          >
            <div class="contest-item-top">
              <strong>{{ item.title }}</strong>
              <span class="contest-badge" :class="item.status">{{ item.status }}</span>
            </div>
            <div class="contest-item-meta">{{ item.start_time }} ~ {{ item.end_time }}</div>
          </button>
          <div class="empty" v-if="!contestList.length">暂无比赛</div>
        </div>
        <div class="empty" v-else>加载中...</div>
        <div class="error" v-if="contestError">{{ contestError }}</div>
      </div>

      <div class="contest-main card">
        <div class="contest-title-row" v-if="contestDetail">
          <div>
            <h3>{{ contestDetail.title }}</h3>
            <p>{{ contestDetail.description || 'No description' }}</p>
          </div>
          <div class="contest-actions">
            <span class="contest-badge" :class="contestDetail.status">{{ contestStatusText }}</span>
            <button v-if="!contestDetail.joined" @click="handleContestJoin">报名</button>
          </div>
        </div>

        <div class="contest-problems" v-if="contestDetail">
          <h4>题目</h4>
          <div class="contest-problem-list">
            <button
              v-for="p in (contestDetail.problems || [])"
              :key="p._id"
              class="contest-problem-item"
              :class="{ active: String(selectedContestProblemId) === String(p._id) }"
              @click="handleContestProblemPick(p)"
            >
              <span>{{ p._id }}</span>
              <strong>{{ p.title }}</strong>
            </button>
          </div>
        </div>

        <!-- Problem description -->
        <div class="contest-problem-detail" v-if="contestDetail && selectedContestProblem">
          <div class="problem-detail-top">
            <div class="card-title">{{ selectedContestProblem.title }}</div>
            <div class="card-subtitle">Problem ID: {{ selectedContestProblem._id }}</div>
          </div>
          <div class="problem-section" v-if="selectedProblemDescription && selectedProblemDescription !== '暂无题目描述'">
            <h4 class="problem-section-title">Description</h4>
            <div class="problem-description" v-html="selectedProblemDescriptionHtml" />
          </div>
        </div>

        <!-- Submit area -->
        <div class="contest-submit" v-if="contestDetail && selectedContestProblem">
          <h4>比赛提交 - {{ selectedContestProblem._id }}</h4>
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
                :key="`contest-${lang}`"
                class="lang-select-option"
                :class="{ selected: activeSubmitLanguage === lang }"
                @click="activeSubmitLanguage = lang; langDropdownOpen = false"
              >{{ lang }}</div>
            </div>
          </div>
          <CodeEditor
            v-for="lang in ALL_LANGUAGES"
            :key="`contest-editor-${lang}`"
            v-show="activeSubmitLanguage === lang"
            v-model="codes[lang]"
            class="oj-code-editor"
            :language="lang"
            placeholder="Enter your source code here"
          />
          <div class="submit-action-row">
            <button :disabled="submitLoading" @click="handleContestSubmitCode">{{ submitLoading ? '提交中...' : '提交代码' }}</button>
          </div>
          <div class="error" v-if="activeSubmitState.message && !submitResult">{{ activeSubmitState.message }}</div>
        </div>

        <div class="empty" v-if="!contestDetail && !contestDetailLoading">请选择一个比赛</div>
        <div class="empty" v-if="contestDetailLoading">加载中...</div>
      </div>

      <div class="contest-rank card">
        <h3>排行榜</h3>
        <div v-if="contestRankLoading" class="empty">加载中...</div>
        <div v-else class="rank-list">
          <div class="rank-row rank-head">
            <span>#</span><span>用户</span><span>通过</span><span>罚时(ms)</span>
          </div>
          <div class="rank-row" v-for="row in contestRankRows" :key="`${row.rank}-${row.user_id}`">
            <span>{{ row.rank }}</span>
            <span>{{ row.user_id }}</span>
            <span>{{ row.solved_count }}</span>
            <span>{{ row.penalty_time_ms }}</span>
          </div>
          <div class="empty" v-if="!contestRankRows.length">暂无排行数据</div>
        </div>
      </div>
    </div>

    <!-- Admin contest create button -->
    <div class="admin-actions-bar" v-if="isAdmin">
      <button class="btn-create-contest" @click="showContestCreateModal = true">+ Create Contest</button>
    </div>
    <ContestCreateModal v-if="showContestCreateModal" @close="showContestCreateModal = false" @created="onContestCreated" />
  </section>
</template>
