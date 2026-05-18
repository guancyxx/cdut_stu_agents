// Singleton store — module-level so all pages share the same reactive state.
// Wraps useOjAuthAndProblems() composable once.
import { computed, ref, watch } from 'vue'
import { createApiClient } from '../services/apiClient'
import { ensureCsrfToken } from '../services/csrfService'
import {
  AUTH_MODES,
  sanitizeTextInput,
  validateDifficulty,
  validateLoginPayload,
  validateRegisterPayload
} from '../utils/validators'

const AUTH_LAST_USERNAME_KEY = 'oj-auth-last-username'

const API_BASE_URL = import.meta.env.VITE_OJ_API_BASE_URL || '/oj-api'
const AGENT_API_BASE_URL = import.meta.env.VITE_AGENT_API_BASE_URL || '/oj-test-cases'

const PAGE_SIZE = 21

const DEFAULT_PROBLEM_QUERY = {
  limit: String(PAGE_SIZE),
  offset: '0'
}

const isBrowserEnvironment = typeof window !== 'undefined'

const getStoredLastUsername = () => {
  if (!isBrowserEnvironment) return ''
  return window.localStorage.getItem(AUTH_LAST_USERNAME_KEY) || ''
}

const persistLastUsername = (username) => {
  if (!isBrowserEnvironment) return
  const normalized = sanitizeTextInput(username, 32)
  if (!normalized) {
    window.localStorage.removeItem(AUTH_LAST_USERNAME_KEY)
    return
  }
  window.localStorage.setItem(AUTH_LAST_USERNAME_KEY, normalized)
}

const ADMIN_TYPE_MAP = {
  'super admin': 2,
  'admin': 1,
  'regular user': 0
}

const resolveAdminType = (rawValue) => {
  if (rawValue === null || rawValue === undefined) return 0
  const num = Number(rawValue)
  if (Number.isInteger(num)) return num
  return ADMIN_TYPE_MAP[String(rawValue).toLowerCase()] ?? 0
}

const resolveUserProfile = (profileResponseData, fallbackUser = {}) => {
  const payload = profileResponseData?.data ?? profileResponseData
  const userNode = payload?.user || payload?.profile || payload || {}
  return {
    username: sanitizeTextInput(
      userNode.username || userNode.profile_name || userNode.name || fallbackUser.username || fallbackUser.profileName,
      32
    ),
    email: sanitizeTextInput(userNode.email || fallbackUser.email, 120),
    avatar: sanitizeTextInput(userNode.avatar || userNode.avatar_url || fallbackUser.avatar, 500),
    studentNumber: sanitizeTextInput(
      userNode.student_number || userNode.studentNumber || userNode.student_id || fallbackUser.studentNumber,
      64
    ),
    signature: sanitizeTextInput(userNode.signature || userNode.motto || fallbackUser.signature, 280),
    adminType: resolveAdminType(userNode.admin_type ?? fallbackUser.adminType ?? 0)
  }
}

// ─── Module-level singleton state ───────────────────────────────────────────

const apiClient = createApiClient(API_BASE_URL, AGENT_API_BASE_URL)

const authMode = ref(AUTH_MODES.LOGIN)
const authReady = ref(false)

const ojUser = ref({
  username: getStoredLastUsername(),
  password: '',
  email: '',
  captcha: '',
  captchaSrc: '',
  loggedIn: false,
  profileName: '',
  avatar: '',
  studentNumber: '',
  signature: '',
  adminType: 0,
  error: ''
})

const problems = ref([])
const problemLoading = ref(false)
const problemError = ref('')

const problemDetail = ref(null)
const problemDetailLoading = ref(false)

const submitLoading = ref(false)
const submitResultBySessionId = ref({})

const keyword = ref('')
const difficulty = ref('')
const currentPage = ref(1)
const totalCount = ref(0)
const totalPages = ref(0)

const contestList = ref([])
const contestListLoading = ref(false)
const contestError = ref('')
const currentContestId = ref('')
const contestDetail = ref(null)
const contestDetailLoading = ref(false)
const contestRankRows = ref([])
const contestRankLoading = ref(false)

// ─── Computed ───────────────────────────────────────────────────────────────

const isLoginMode = computed(() => authMode.value === AUTH_MODES.LOGIN)
const isAdmin = computed(() => ojUser.value.adminType > 0)

// ─── Actions ────────────────────────────────────────────────────────────────

async function hydrateAuthSession() {
  authReady.value = false
  try {
    await ensureCsrfToken()
    const resp = await apiClient.get(`/api/oj-user/login-status`)
    const data = resp?.data ?? resp

    if (data?.data?.is_login === true && data?.data?.username) {
      const userData = data.data
      ojUser.value.username = sanitizeTextInput(userData.username, 32)
      ojUser.value.loggedIn = true
      persistLastUsername(userData.username)
      await fetchUserProfile()
    } else {
      ojUser.value.loggedIn = false
    }
  } catch (error) {
    console.warn('Auth hydration failed:', error)
    ojUser.value.loggedIn = false
  } finally {
    authReady.value = true
  }
}

async function fetchUserProfile() {
  try {
    await ensureCsrfToken()
    const resp = await apiClient.get('/api/oj-user/profile')
    const profile = resolveUserProfile(resp?.data ?? resp, ojUser.value)
    ojUser.value.profileName = profile.username || ojUser.value.username
    ojUser.value.email = profile.email
    ojUser.value.avatar = profile.avatar
    ojUser.value.studentNumber = profile.studentNumber
    ojUser.value.signature = profile.signature
    ojUser.value.adminType = profile.adminType
  } catch (error) {
    console.warn('Failed to fetch user profile.', error)
  }
}

async function refreshCaptcha() {
  try {
    const resp = await apiClient.get('/api/oj-user/captcha')
    ojUser.value.captchaSrc = resp?.data?.captcha_url || resp?.captcha_url || ''
  } catch (error) {
    console.warn('Failed to refresh captcha.', error)
  }
}

async function login() {
  ojUser.value.error = ''
  const payload = validateLoginPayload({
    username: ojUser.value.username,
    password: ojUser.value.password
  })
  if (!payload) {
    ojUser.value.error = 'Invalid login payload.'
    return
  }
  try {
    await ensureCsrfToken()
    const resp = await apiClient.post('/api/oj-user/login', payload)
    const data = resp?.data ?? resp
    if (data?.error) {
      ojUser.value.error = data.data || data.error
      return
    }
    ojUser.value.loggedIn = true
    persistLastUsername(payload.username)
    await fetchUserProfile()
  } catch (error) {
    ojUser.value.error = error.message || 'Login failed.'
  }
}

async function register() {
  ojUser.value.error = ''
  const payload = validateRegisterPayload({
    username: ojUser.value.username,
    password: ojUser.value.password,
    email: ojUser.value.email,
    studentNumber: ojUser.value.studentNumber,
    captcha: ojUser.value.captcha
  })
  if (!payload) {
    ojUser.value.error = 'Invalid registration payload.'
    return
  }
  try {
    await ensureCsrfToken()
    const resp = await apiClient.post('/api/oj-user/register', payload)
    const data = resp?.data ?? resp
    if (data?.error) {
      ojUser.value.error = data.data || data.error
      return
    }
    // Auto-login after register
    await login()
  } catch (error) {
    ojUser.value.error = error.message || 'Registration failed.'
  }
}

async function logout() {
  try {
    await ensureCsrfToken()
    await apiClient.post('/api/oj-user/logout')
  } catch {
    // Best-effort
  }
  ojUser.value.loggedIn = false
  ojUser.value.password = ''
  ojUser.value.email = ''
  ojUser.value.profileName = ''
  ojUser.value.avatar = ''
  ojUser.value.studentNumber = ''
  ojUser.value.signature = ''
  ojUser.value.adminType = 0
  ojUser.value.error = ''
  problems.value = []
  problemDetail.value = null
  contestList.value = []
  contestDetail.value = null
  submitResultBySessionId.value = {}
  return true
}

async function fetchProblems() {
  problemLoading.value = true
  problemError.value = ''
  try {
    const params = { ...DEFAULT_PROBLEM_QUERY }
    const kw = keyword.value.trim()
    if (kw) params.keyword = kw
    if (difficulty.value) params.difficulty = difficulty.value
    params.offset = String((currentPage.value - 1) * PAGE_SIZE)

    const resp = await apiClient.get('/api/problem/list', { params })
    const data = resp?.data ?? resp
    if (data?.error) {
      problemError.value = data.data || data.error
      return
    }
    problems.value = Array.isArray(data?.data?.results)
      ? data.data.results
      : Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data?.data)
      ? data.data
      : []
    totalCount.value = data?.data?.total_count ?? data?.total_count ?? problems.value.length
    totalPages.value = Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE))
  } catch (error) {
    problemError.value = error.message || 'Failed to load problems.'
  } finally {
    problemLoading.value = false
  }
}

async function fetchProblemDetail(problemId) {
  problemDetailLoading.value = true
  try {
    const resp = await apiClient.get(`/api/problem/detail/${problemId}`)
    const data = resp?.data ?? resp
    if (data?.error) {
      console.warn('Problem detail error:', data.error)
      return
    }
    problemDetail.value = data?.data ?? data
  } catch (error) {
    console.warn('Failed to fetch problem detail:', error)
  } finally {
    problemDetailLoading.value = false
  }
}

async function searchProblems() {
  currentPage.value = 1
  await fetchProblems()
}

function goToPage(page) {
  const p = Number(page)
  if (p < 1 || p > totalPages.value) return
  currentPage.value = p
  fetchProblems()
}

// ─── Submission helpers ─────────────────────────────────────────────────────

function getSubmitResultForSession(sessionId) {
  return submitResultBySessionId.value[sessionId] || null
}

function setSubmitResultForSession(sessionId, result) {
  submitResultBySessionId.value[sessionId] = result
}

function pruneSubmitResults(validSessionIds) {
  submitResultBySessionId.value = Object.fromEntries(
    Object.entries(submitResultBySessionId.value).filter(([sid]) => validSessionIds.includes(sid))
  )
}

// ─── Submit solution ────────────────────────────────────────────────────────

async function submitSolution({ problemId, problemQueryId, language, code, sessionId, contestId }) {
  submitLoading.value = true
  const sid = sessionId || ''
  try {
    await ensureCsrfToken()
    const body = {
      problem_id: problemId,
      problem_query_id: problemQueryId,
      language,
      code
    }
    if (contestId) body.contest_id = contestId

    const resp = await apiClient.post('/api/submission/submit', body)
    const data = resp?.data ?? resp

    if (data?.error) {
      return { label: 'ERROR', message: data.data || data.error }
    }

    // Poll for result
    const submissionId = data?.data?.submission_id || data?.submission_id
    if (!submissionId) return { label: 'ERROR', message: 'No submission ID returned.' }

    const result = await pollSubmission(submissionId)
    setSubmitResultForSession(sid, result)
    return result
  } catch (error) {
    const errResult = { label: 'ERROR', message: error.message || 'Submission failed.' }
    setSubmitResultForSession(sid, errResult)
    return errResult
  } finally {
    submitLoading.value = false
  }
}

async function pollSubmission(submissionId, maxAttempts = 30, intervalMs = 2000) {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
    try {
      const resp = await apiClient.get(`/api/submission/result/${submissionId}`)
      const data = resp?.data ?? resp
      if (data?.error) continue

      const result = data?.data ?? data
      if (result && result.label !== 'WAITING' && result.label !== 'JUDGING' && result.label !== 'PENDING') {
        return result
      }
    } catch {
      // Retry
    }
  }
  return { label: 'TIMEOUT', message: 'Judge polling timed out.' }
}

// ─── Fallback report ────────────────────────────────────────────────────────

async function reportSubmissionToFallback({ sessionId, problemId, language, result }) {
  if (!sessionId || !problemId) return null
  try {
    const resp = await apiClient.post('/api/agent/submission-fallback', {
      session_id: sessionId,
      problem_id: problemId,
      language,
      result
    })
    return resp?.data?.data ?? resp?.data ?? null
  } catch {
    return null
  }
}

// ─── Contest actions ────────────────────────────────────────────────────────

async function fetchContests(filter = 'all') {
  contestListLoading.value = true
  contestError.value = ''
  try {
    const resp = await apiClient.get('/api/contest/list', { params: { filter } })
    const data = resp?.data ?? resp
    if (data?.error) {
      contestError.value = data.data || data.error
      return
    }
    contestList.value = Array.isArray(data?.data?.results)
      ? data.data.results
      : Array.isArray(data?.data)
      ? data.data
      : []
  } catch (error) {
    contestError.value = error.message || 'Failed to load contests.'
  } finally {
    contestListLoading.value = false
  }
}

async function fetchContestDetail(contestId) {
  contestDetailLoading.value = true
  try {
    const resp = await apiClient.get(`/api/contest/detail/${contestId}`)
    const data = resp?.data ?? resp
    if (data?.error) {
      contestError.value = data.data || data.error
      return
    }
    contestDetail.value = data?.data ?? data
    currentContestId.value = contestId
  } catch (error) {
    contestError.value = error.message || 'Failed to load contest.'
  } finally {
    contestDetailLoading.value = false
  }
}

async function joinContest(contestId) {
  try {
    await ensureCsrfToken()
    const resp = await apiClient.post('/api/contest/join', { contest_id: contestId })
    const data = resp?.data ?? resp
    if (data?.error) {
      contestError.value = data.data || data.error
      return false
    }
    return true
  } catch (error) {
    contestError.value = error.message || 'Failed to join contest.'
    return false
  }
}

async function fetchContestRank(contestId) {
  contestRankLoading.value = true
  try {
    const resp = await apiClient.get(`/api/contest/rank/${contestId}`)
    const data = resp?.data ?? resp
    if (data?.error) return
    contestRankRows.value = Array.isArray(data?.data) ? data.data : []
  } catch (error) {
    console.warn('Failed to load contest rank:', error)
  } finally {
    contestRankLoading.value = false
  }
}

// ─── Export ─────────────────────────────────────────────────────────────────

export function useOjStore() {
  return {
    AUTH_MODES,
    authMode,
    authReady,
    ojUser,
    problems,
    problemLoading,
    problemError,
    problemDetail,
    problemDetailLoading,
    fetchProblemDetail,
    submitLoading,
    submitResultBySessionId,
    getSubmitResultForSession,
    setSubmitResultForSession,
    pruneSubmitResults,
    keyword,
    difficulty,
    currentPage,
    totalCount,
    totalPages,
    PAGE_SIZE,
    goToPage,
    searchProblems,
    isLoginMode,
    isAdmin,
    hydrateAuthSession,
    fetchUserProfile,
    refreshCaptcha,
    login,
    register,
    logout,
    fetchProblems,
    submitSolution,
    reportSubmissionToFallback,
    contestList,
    contestListLoading,
    contestError,
    currentContestId,
    contestDetail,
    contestDetailLoading,
    contestRankRows,
    contestRankLoading,
    fetchContests,
    fetchContestDetail,
    joinContest,
    fetchContestRank
  }
}
