<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
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
  submitSolution, submitLoading,
  getSubmitResultForSession,
  isAdmin
} = useOjStore()

const { currentSessionId } = useChatStore()

const selectedContestProblemId = ref('')
const langDropdownOpen = ref(false)
const showContestCreateModal = ref(false)
const showContestDetailModal = ref(false)
const listCollapsed = ref(false)
const contestInfoCollapsed = ref(false)
const activeSubmitLanguage = ref(DEFAULT_LANGUAGE)
const codes = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
const templateRawByLanguage = ref(Object.fromEntries(ALL_LANGUAGES.map((l) => [l, ''])))
const activeSubmitState = ref({ type: '', message: '' })
const timerTick = ref(0)

const parseContestDate = (value) => {
  if (!value) return null
  const dt = new Date(String(value))
  if (Number.isNaN(dt.getTime())) return null
  return dt
}

const deriveContestStatus = (contest) => {
  const explicit = String(contest?.status || '').toLowerCase()
  if (['upcoming', 'running', 'ended'].includes(explicit)) return explicit
  const now = Date.now()
  const st = parseContestDate(contest?.start_time)
  const et = parseContestDate(contest?.end_time)
  if (st && now < st.getTime()) return 'upcoming'
  if (et && now >= et.getTime()) return 'ended'
  return 'running'
}

const contestStatusText = (status) => {
  if (status === 'running') return '进行中'
  if (status === 'upcoming') return '即将开始'
  if (status === 'ended') return '已结束'
  return '-'
}

const formatContestTimeRange = (contest) => {
  const start = contest?.start_time || '-'
  const end = contest?.end_time || '-'
  return `${start} ~ ${end}`
}

const sortedContestList = computed(() => {
  const rows = Array.isArray(contestList.value) ? [...contestList.value] : []
  return rows.sort((a, b) => {
    const ta = parseContestDate(a?.start_time || a?.created_at)?.getTime() || 0
    const tb = parseContestDate(b?.start_time || b?.created_at)?.getTime() || 0
    return tb - ta
  })
})

const selectedContest = computed(() => {
  const cid = String(currentContestId.value || '')
  if (!cid) return null
  return sortedContestList.value.find((item) => String(item.id) === cid) || null
})

const activeContestStatus = computed(() => deriveContestStatus(contestDetail.value || selectedContest.value || {}))

const formatDuration = (ms) => {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000))
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (days > 0) return `${days}天 ${String(hours).padStart(2, '0')}时 ${String(minutes).padStart(2, '0')}分`
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

const contestTimerText = computed(() => {
  void timerTick.value
  const status = activeContestStatus.value
  const now = Date.now()
  const startAt = parseContestDate(contestDetail.value?.start_time || selectedContest.value?.start_time)
  const endAt = parseContestDate(contestDetail.value?.end_time || selectedContest.value?.end_time)
  if (status === 'upcoming' && startAt) {
    const diff = Math.max(0, startAt.getTime() - now)
    return `距离开赛：${formatDuration(diff)}`
  }
  if (status === 'running' && endAt) {
    const diff = Math.max(0, endAt.getTime() - now)
    return `剩余时间：${formatDuration(diff)}`
  }
  if (status === 'ended') return '比赛已结束'
  return '时间信息不可用'
})

const canJoinContest = computed(() => {
  if (!contestDetail.value) return false
  if (contestDetail.value.joined) return false
  return activeContestStatus.value === 'running'
})

const joinDisabledReason = computed(() => {
  if (!contestDetail.value || contestDetail.value.joined) return ''
  if (activeContestStatus.value === 'upcoming') return '比赛未开始，暂不可报名'
  if (activeContestStatus.value === 'ended') return '比赛已结束，无法报名'
  return ''
})

const canSubmitContest = computed(() => {
  if (!contestDetail.value || !selectedContestProblem.value) return false
  return activeContestStatus.value === 'running' && Boolean(contestDetail.value.joined)
})

const contestSubmitBlockReason = computed(() => {
  if (!contestDetail.value) return '请先选择一个比赛。'
  if (activeContestStatus.value === 'upcoming') return '比赛尚未开始，暂不可提交。'
  if (activeContestStatus.value === 'ended') return '比赛已结束，提交入口已关闭。'
  if (!contestDetail.value.joined) return '请先完成报名后再提交。'
  return ''
})

const rankBannerText = computed(() => {
  if (activeContestStatus.value === 'running') return '当前排行榜为进行中临时榜单'
  if (activeContestStatus.value === 'ended') return '当前排行榜为最终榜单'
  if (activeContestStatus.value === 'upcoming') return '比赛未开始，排行榜仅供参考'
  return ''
})

const selectedContestProblem = computed(() => {
  const rows = Array.isArray(contestDetail.value?.problems) ? contestDetail.value.problems : []
  const pid = String(selectedContestProblemId.value || '')
  if (!pid) return null
  return rows.find((item) => String(item._id) === pid) || null
})

const selectedProblemDescription = computed(() => {
  const detail = problemDetail.value
  if (!detail) return ''
  return String(detail.description || detail.content || detail.desc || detail.problem_description || '').trim() || '暂无题目描述'
})

const selectedProblemDescriptionHtml = computed(() => sanitizeHtmlContent(selectedProblemDescription.value))
const submitResult = computed(() => getSubmitResultForSession(currentSessionId.value))

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

const handleContestQuickJoin = async (item) => {
  if (!item?.id) return
  await handleContestSelect(item.id)
  await handleContestJoin()
}

const getCardJoinLabel = (item) => {
  const status = deriveContestStatus(item)
  if (item?.joined) return '已报名'
  if (status === 'running') return '参加'
  return '报名'
}

const isCardJoinDisabled = (item) => {
  const status = deriveContestStatus(item)
  if (item?.joined) return true
  return status !== 'running'
}

const cardJoinTitle = (item) => {
  if (item?.joined) return '你已报名该比赛'
  const status = deriveContestStatus(item)
  if (status === 'upcoming') return '比赛未开始，暂不可报名'
  if (status === 'ended') return '比赛已结束，无法报名'
  return ''
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

const onContestCreated = async (result) => {
  await fetchContests('all')
  if (result?.contest_id) {
    currentContestId.value = result.contest_id
    await fetchContestDetail(result.contest_id)
    await fetchContestRank(result.contest_id)
    const firstProblem = Array.isArray(contestDetail.value?.problems) ? contestDetail.value.problems[0] : null
    selectedContestProblemId.value = firstProblem?._id ? String(firstProblem._id) : ''
  }
}

const handleCollapseToggle = () => {
  listCollapsed.value = !listCollapsed.value
}

const handleContestCardKeydown = (event, contestId) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    handleContestSelect(contestId)
  }
}

const handleProblemCardKeydown = (event, problem) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    handleContestProblemPick(problem)
  }
}

let timerHandle = null
onMounted(() => {
  timerHandle = window.setInterval(() => {
    timerTick.value += 1
  }, 1000)
})

onUnmounted(() => {
  if (timerHandle) {
    window.clearInterval(timerHandle)
    timerHandle = null
  }
})
</script>

<template>
  <section class="contest-screen">
    <div class="contest-layout-v2" :class="{ 'list-collapsed': listCollapsed }">
      <aside class="contest-list-pane card">
        <div class="contest-list-head">
          <div class="contest-list-title-group">
            <h3>比赛列表</h3>
            <span class="contest-list-count">{{ sortedContestList.length }} 场</span>
          </div>
          <div class="contest-list-head-actions">
            <button
              v-if="isAdmin && !listCollapsed"
              class="mini-btn primary"
              @click="showContestCreateModal = true"
            >新增比赛</button>
            <button
              class="icon-btn collapse-btn"
              @click="handleCollapseToggle"
              :title="listCollapsed ? '展开比赛列表' : '折叠比赛列表'"
              :aria-label="listCollapsed ? '展开比赛列表' : '折叠比赛列表'"
            >
              <span class="collapse-icon" :class="{ collapsed: listCollapsed }">▸</span>
            </button>
          </div>
        </div>

        <div v-if="!listCollapsed" class="contest-list-body">
          <div class="contest-list-scroll" v-if="!contestListLoading">
            <article
              v-for="item in sortedContestList"
              :key="item.id"
              class="contest-card-item"
              :class="{ active: String(item.id) === String(currentContestId) }"
              role="button"
              tabindex="0"
              @click="handleContestSelect(item.id)"
              @keydown="handleContestCardKeydown($event, item.id)"
            >
              <div class="contest-card-topbar">
                <span class="contest-badge" :class="deriveContestStatus(item)">{{ contestStatusText(deriveContestStatus(item)) }}</span>
                <div class="contest-card-actions">
                  <button class="mini-btn" @click.stop="handleContestSelect(item.id); showContestDetailModal = true">详情</button>
                  <button
                    class="mini-btn"
                    :disabled="isCardJoinDisabled(item)"
                    :title="cardJoinTitle(item)"
                    @click.stop="handleContestQuickJoin(item)"
                  >{{ getCardJoinLabel(item) }}</button>
                </div>
              </div>
              <div class="contest-card-main">
                <div class="contest-card-title-row">
                  <strong class="contest-card-title">{{ item.title }}</strong>
                </div>
                <div class="contest-card-meta">{{ formatContestTimeRange(item) }}</div>
              </div>
            </article>
            <div class="empty" v-if="!sortedContestList.length">暂无比赛</div>
          </div>
          <div class="empty" v-else>加载中...</div>
          <div class="error" v-if="contestError">{{ contestError }}</div>
        </div>
      </aside>

      <section class="contest-workspace card">
        <div v-if="!contestDetail && !contestDetailLoading" class="contest-empty-hero">
          <div class="hero-badge">Keep coding. Keep climbing.</div>
          <h2>每一场比赛，都是你进阶的下一步</h2>
          <p>
            选择左侧比赛，开始一次高质量训练。你可以先阅读赛制和时间信息，再进入题目区提交代码，实时查看排行榜变化。
          </p>
        </div>

        <div v-else-if="contestDetailLoading" class="empty">加载中...</div>

        <div v-else class="contest-selected-layout">
          <div class="contest-work-left">
            <section class="contest-info-panel">
              <div class="panel-head">
                <div>
                  <h3>{{ contestDetail.title }}</h3>
                  <p>{{ contestDetail.description || '暂无比赛描述' }}</p>
                </div>
                <div class="panel-head-right">
                  <span class="contest-badge" :class="activeContestStatus">{{ contestStatusText(activeContestStatus) }}</span>
                  <span class="contest-timer-chip">{{ contestTimerText }}</span>
                  <button
                    class="icon-btn"
                    @click="contestInfoCollapsed = !contestInfoCollapsed"
                    :title="contestInfoCollapsed ? '展开比赛信息' : '折叠比赛信息'"
                    :aria-label="contestInfoCollapsed ? '展开比赛信息' : '折叠比赛信息'"
                  >
                    <span class="collapse-icon" :class="{ collapsed: contestInfoCollapsed }">▸</span>
                  </button>
                </div>
              </div>

              <div class="contest-detail-grid" v-if="!contestInfoCollapsed">
                <div class="detail-item"><span>开始时间</span><strong>{{ contestDetail.start_time || '-' }}</strong></div>
                <div class="detail-item"><span>结束时间</span><strong>{{ contestDetail.end_time || '-' }}</strong></div>
                <div class="detail-item"><span>报名状态</span><strong>{{ contestDetail.joined ? '已报名' : '未报名' }}</strong></div>
                <div class="detail-item"><span>题目数量</span><strong>{{ Array.isArray(contestDetail.problems) ? contestDetail.problems.length : 0 }}</strong></div>
              </div>
            </section>

            <section class="contest-action-panel">
              <div v-if="activeContestStatus === 'upcoming'" class="contest-countdown-card">
                <div class="countdown-label">开赛倒计时</div>
                <div class="countdown-value">{{ contestTimerText }}</div>
              </div>

              <template v-else-if="activeContestStatus === 'running'">
                <div class="running-workspace">
                  <div class="running-problem-column">
                    <h4>赛题列表</h4>
                    <div class="contest-problem-list">
                      <article
                        v-for="p in (contestDetail.problems || [])"
                        :key="p._id"
                        class="contest-problem-item"
                        :class="{ active: String(selectedContestProblemId) === String(p._id) }"
                        role="button"
                        tabindex="0"
                        @click="handleContestProblemPick(p)"
                        @keydown="(event) => handleProblemCardKeydown(event, p)"
                      >
                        <div class="contest-problem-card-id">{{ p._id }}</div>
                        <strong>{{ p.title }}</strong>
                      </article>
                    </div>
                  </div>

                  <div class="running-submit-column">
                    <div class="contest-submit-layout" v-if="selectedContestProblem">
                      <div class="contest-problem-detail">
                        <div class="problem-detail-top">
                          <div class="card-title">{{ selectedContestProblem.title }}</div>
                          <div class="card-subtitle">Problem ID: {{ selectedContestProblem._id }}</div>
                        </div>
                        <div class="problem-section" v-if="selectedProblemDescription && selectedProblemDescription !== '暂无题目描述'">
                          <h4 class="problem-section-title">Description</h4>
                          <div class="problem-description" v-html="selectedProblemDescriptionHtml" />
                        </div>
                      </div>

                      <div class="submit-layout">
                        <div class="contest-submit">
                          <div class="contest-submit-hint" v-if="!canSubmitContest">{{ contestSubmitBlockReason }}</div>
                          <div class="lang-select-wrap" v-if="canSubmitContest">
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
                            v-if="canSubmitContest"
                            v-for="lang in ALL_LANGUAGES"
                            :key="`contest-editor-${lang}`"
                            v-show="activeSubmitLanguage === lang"
                            v-model="codes[lang]"
                            class="oj-code-editor"
                            :language="lang"
                            placeholder="Enter your source code here"
                          />

                          <div class="submit-action-row" v-if="canSubmitContest">
                            <button :disabled="submitLoading" @click="handleContestSubmitCode">{{ submitLoading ? '提交中...' : '提交代码' }}</button>
                          </div>

                          <div class="error" v-if="activeSubmitState.message && !submitResult">{{ activeSubmitState.message }}</div>
                        </div>

                        <div class="submit-result-area scrollbar-unified">
                          <div class="submit-result-empty" v-if="submitLoading">
                            <div class="result-spinner"></div>
                            <span>Judging...</span>
                          </div>
                          <div class="submit-result-panel" v-else-if="submitResult" :class="`result-${String(submitResult.label || '').toLowerCase()}`">
                            <div class="result-header">
                              <span class="result-label">{{ submitResult.label }}</span>
                            </div>
                            <div class="result-stats-row">
                              <div class="result-stat"><span class="stat-label">Score</span><span class="stat-value">{{ submitResult.score }}</span></div>
                              <div class="result-stat"><span class="stat-label">Time</span><span class="stat-value">{{ submitResult.timeCost }}ms</span></div>
                              <div class="result-stat"><span class="stat-label">Memory</span><span class="stat-value">{{ submitResult.memoryCost }}KB</span></div>
                            </div>
                            <pre class="result-error-block" v-if="submitResult.errInfo">{{ submitResult.errInfo }}</pre>
                          </div>
                          <div class="submit-result-empty" v-else>
                            <span>暂无提交结果</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <template v-else>
                <div class="contest-ended-card">
                  <h4>比赛已结束</h4>
                  <p>该比赛已关闭提交入口，你可以查看最终排行榜与赛后复盘信息。</p>
                </div>
              </template>
            </section>
          </div>

          <aside class="contest-rank-panel">
            <h3>排行榜</h3>
            <div class="rank-banner" v-if="rankBannerText">{{ rankBannerText }}</div>
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
          </aside>
        </div>
      </section>
    </div>

    <div v-if="showContestDetailModal && contestDetail" class="contest-detail-modal-overlay" @click.self="showContestDetailModal = false">
      <div class="contest-detail-modal card" role="dialog" aria-label="Contest details">
        <div class="detail-modal-head">
          <h3>{{ contestDetail.title }}</h3>
          <button class="mini-btn" @click="showContestDetailModal = false">关闭</button>
        </div>
        <div class="detail-modal-grid">
          <div class="detail-item"><span>状态</span><strong>{{ contestStatusText(activeContestStatus) }}</strong></div>
          <div class="detail-item"><span>开始时间</span><strong>{{ contestDetail.start_time || '-' }}</strong></div>
          <div class="detail-item"><span>结束时间</span><strong>{{ contestDetail.end_time || '-' }}</strong></div>
          <div class="detail-item"><span>报名状态</span><strong>{{ contestDetail.joined ? '已报名' : '未报名' }}</strong></div>
          <div class="detail-item full"><span>比赛描述</span><strong>{{ contestDetail.description || '暂无描述' }}</strong></div>
        </div>
      </div>
    </div>

    <ContestCreateModal
      v-if="showContestCreateModal"
      @close="showContestCreateModal = false"
      @created="onContestCreated"
    />
  </section>
</template>
