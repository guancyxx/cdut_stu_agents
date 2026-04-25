import { computed, ref } from 'vue'
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
    signature: sanitizeTextInput(userNode.signature || userNode.motto || fallbackUser.signature, 280)
  }
}

export function useOjAuthAndProblems() {
  const apiClient = createApiClient('/oj-api')

  const authMode = ref(AUTH_MODES.LOGIN)
  const authUsernameRef = ref(null)
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
    error: ''
  })

  const problems = ref([])
  const problemLoading = ref(false)
  const problemError = ref('')
  const submitLoading = ref(false)

  // Per-session submit results — prevents stale result from polluting new sessions
  const submitResultBySessionId = ref({})

  const ensureSubmitResultForSession = (sessionId) => {
    if (!sessionId) return null
    if (submitResultBySessionId.value[sessionId] === undefined) {
      submitResultBySessionId.value[sessionId] = null
    }
    return submitResultBySessionId.value[sessionId]
  }

  const getSubmitResultForSession = (sessionId) => {
    if (!sessionId) return null
    return submitResultBySessionId.value[sessionId] ?? null
  }

  const setSubmitResultForSession = (sessionId, result) => {
    if (!sessionId) return
    submitResultBySessionId.value[sessionId] = result ?? null
  }

  const pruneSubmitResults = (validSessionIds) => {
    const valid = new Set(validSessionIds)
    submitResultBySessionId.value = Object.fromEntries(
      Object.entries(submitResultBySessionId.value).filter(([sid]) => valid.has(sid))
    )
  }
  const keyword = ref('')
  const difficulty = ref('')

  const currentPage = ref(1)
  const totalCount = ref(0)
  const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE)))

  const goToPage = (page) => {
    const target = Math.max(1, Math.min(page, totalPages.value))
    if (target === currentPage.value) return
    currentPage.value = target
    fetchProblems()
  }

  const searchProblems = () => {
    currentPage.value = 1
    fetchProblems()
  }

  const isLoginMode = computed(() => authMode.value === AUTH_MODES.LOGIN)

  const resetAuthError = () => {
    ojUser.value.error = ''
  }

  const resetUserProfileFields = () => {
    ojUser.value.avatar = ''
    ojUser.value.studentNumber = ''
    ojUser.value.signature = ''
    ojUser.value.email = ''
  }

  const refreshCaptcha = async () => {
    try {
      const response = await apiClient.fetchCaptcha()
      ojUser.value.captchaSrc = response.data?.data || ''
    } catch (error) {
      ojUser.value.captchaSrc = ''
      console.warn('Failed to refresh captcha.', error)
    }
  }

  const applyLoginSuccess = (usernameFromServer) => {
    const normalizedUsername = sanitizeTextInput(
      usernameFromServer || ojUser.value.username || ojUser.value.profileName,
      32
    )

    ojUser.value.loggedIn = true
    ojUser.value.profileName = normalizedUsername
    ojUser.value.username = normalizedUsername
    ojUser.value.password = ''
    ojUser.value.captcha = ''
    ojUser.value.error = ''

    persistLastUsername(normalizedUsername)
  }

  const applyUserProfileData = (profileData) => {
    const profile = resolveUserProfile(profileData, ojUser.value)

    if (profile.username) {
      applyLoginSuccess(profile.username)
    }

    ojUser.value.email = profile.email
    ojUser.value.avatar = profile.avatar
    ojUser.value.studentNumber = profile.studentNumber
    ojUser.value.signature = profile.signature
  }

  const fetchUserProfile = async () => {
    const response = await apiClient.fetchProfile()
    const result = response.data

    if (result?.error) {
      throw new Error(typeof result.data === 'string' ? result.data : result.error)
    }

    applyUserProfileData(result)
    return result
  }

  const hydrateAuthSession = async () => {
    resetAuthError()

    const fallbackUsername = getStoredLastUsername()
    if (!ojUser.value.username && fallbackUsername) {
      ojUser.value.username = fallbackUsername
    }

    try {
      await fetchUserProfile()
    } catch (error) {
      console.warn('Failed to hydrate auth session.', error)
    } finally {
      authReady.value = true
    }
  }

  const login = async () => {
    resetAuthError()

    const validation = validateLoginPayload(ojUser.value)
    if (!validation.valid) {
      ojUser.value.error = validation.message
      return
    }

    const csrfToken = await ensureCsrfToken(apiClient)
    const response = await apiClient.login(validation.value, csrfToken)
    const result = response.data

    if (result?.error) {
      ojUser.value.error = typeof result.data === 'string' ? result.data : result.error
      return
    }

    applyLoginSuccess(result.data?.username)

    try {
      await fetchUserProfile()
    } catch (error) {
      console.warn('Failed to fetch profile after login.', error)
    }
  }

  const register = async () => {
    resetAuthError()

    const validation = validateRegisterPayload(ojUser.value)
    if (!validation.valid) {
      ojUser.value.error = validation.message
      return
    }

    const csrfToken = await ensureCsrfToken(apiClient)
    const response = await apiClient.register(validation.value, csrfToken)
    const result = response.data

    if (result?.error) {
      ojUser.value.error = typeof result.data === 'string' ? result.data : result.error
      await refreshCaptcha()
      return
    }

    applyLoginSuccess(validation.value.username)

    try {
      await fetchUserProfile()
    } catch (error) {
      console.warn('Failed to fetch profile after register.', error)
    }
  }

  const clearAuthState = () => {
    ojUser.value.loggedIn = false
    ojUser.value.profileName = ''
    ojUser.value.password = ''
    ojUser.value.captcha = ''
    ojUser.value.error = ''
    persistLastUsername(ojUser.value.username)
    resetUserProfileFields()
  }

  const logout = async () => {
    resetAuthError()

    try {
      await apiClient.logout()
    } catch (error) {
      console.warn('Logout request failed, fallback to local sign out.', error)
    }

    clearAuthState()
    return true
  }

  const fetchProblems = async () => {
    problemError.value = ''
    problemLoading.value = true

    try {
      const normalizedKeyword = sanitizeTextInput(keyword.value, 60)
      const normalizedDifficulty = validateDifficulty(difficulty.value)

      const offset = Math.max(0, (currentPage.value - 1) * PAGE_SIZE)
      const params = {
        ...DEFAULT_PROBLEM_QUERY,
        offset: String(offset),
        ...(normalizedKeyword ? { keyword: normalizedKeyword } : {}),
        ...(normalizedDifficulty ? { difficulty: normalizedDifficulty } : {})
      }

      const response = await apiClient.fetchProblems(params)
      const result = response.data

      if (result?.error) {
        problemError.value = typeof result.data === 'string' ? result.data : result.error
        problems.value = []
        return
      }

      const rows = Array.isArray(result.data?.results) ? result.data.results : []
      problems.value = rows
      totalCount.value = Number(result.data?.total ?? rows.length)
      const maxPage = Math.ceil(totalCount.value / PAGE_SIZE) || 1
      if (currentPage.value > maxPage) {
        currentPage.value = maxPage
      }
    } catch (error) {
      problemError.value = error.message || String(error)
      problems.value = []
    } finally {
      problemLoading.value = false
    }
  }

  const JUDGE_STATUS_MAP = {
    '-2': { label: 'COMPILING', display: 'Compiling', icon: '⏳', color: '#fbbf24' },
    '-1': { label: 'SYSTEM_ERROR', display: 'System Error', icon: '⚠️', color: '#ef4444' },
    '0': { label: 'PENDING', display: 'Pending', icon: '⏳', color: '#9ca3af' },
    '1': { label: 'JUDGING', display: 'Judging', icon: '🔄', color: '#60a5fa' },
    '2': { label: 'COMPILING', display: 'Compiling', icon: '⏳', color: '#fbbf24' },
    '3': { label: 'COMPILE_ERROR', display: 'Compile Error', icon: '❌', color: '#ef4444' },
    '4': { label: 'ACCEPTED', display: 'Accepted', icon: '✅', color: '#10b981' },
    '5': { label: 'PRESENTATION_ERROR', display: 'Presentation Error', icon: '⚠️', color: '#f59e0b' },
    '6': { label: 'WRONG_ANSWER', display: 'Wrong Answer', icon: '❌', color: '#ef4444' },
    '7': { label: 'TIME_LIMIT_EXCEEDED', display: 'Time Limit Exceeded', icon: '⏰', color: '#f59e0b' },
    '8': { label: 'MEMORY_LIMIT_EXCEEDED', display: 'Memory Limit Exceeded', icon: '💾', color: '#f59e0b' },
    '9': { label: 'RUNTIME_ERROR', display: 'Runtime Error', icon: '💥', color: '#ef4444' },
    '10': { label: 'SYSTEM_ERROR', display: 'System Error', icon: '⚠️', color: '#ef4444' }
  }

  const normalizeSubmissionResult = (row) => {
    if (!row || typeof row !== 'object') {
      return {
        status: null,
        label: 'UNKNOWN',
        display: 'Unknown',
        icon: '❓',
        color: '#9ca3af',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: '',
        errInfo: '',
        testCases: []
      }
    }

    const status = Number(row.result)
    const statusInfo = JUDGE_STATUS_MAP[String(status)] || { label: 'UNKNOWN', display: 'Unknown', icon: '❓', color: '#9ca3af' }
    const statisticInfo = row.statistic_info && typeof row.statistic_info === 'object' ? row.statistic_info : {}
    const errInfo = typeof statisticInfo.err_info === 'string' ? statisticInfo.err_info : ''

    return {
      status,
      label: statusInfo.label,
      display: statusInfo.display,
      icon: statusInfo.icon,
      color: statusInfo.color,
      score: Number(statisticInfo.score || 0),
      timeCost: Number(statisticInfo.time_cost || 0),
      memoryCost: Number(statisticInfo.memory_cost || 0),
      submissionId: sanitizeTextInput(String(row.id || ''), 64),
      errInfo,
      testCases: []
    }
  }

  const isFinalSubmissionStatus = (status) => ![0, 1, 2, -2].includes(status)

  // Parse test case detail from submission detail API response
  const parseTestCases = (detailData) => {
    if (!detailData || !detailData.info) return []
    const infoData = detailData.info
    if (!infoData) return []

    // Handle compile error: info = {err: "compile error message", data: "compiler output"}
    const infoErr = typeof infoData.err === 'string' ? infoData.err : ''

    const testCases = infoData.data
    // If data is a string (e.g. compile error output), return empty but preserve error
    if (!Array.isArray(testCases)) return []

    return testCases.map((tc) => {
      const tcStatus = Number(tc.result)
      const tcStatusInfo = JUDGE_STATUS_MAP[String(tcStatus)] || { label: 'UNKNOWN', display: 'Unknown', icon: '❓', color: '#9ca3af' }
      return {
        index: Number(tc.test_case || 0),
        status: tcStatus,
        label: tcStatusInfo.label,
        display: tcStatusInfo.display,
        icon: tcStatusInfo.icon,
        color: tcStatusInfo.color,
        cpuTime: Number(tc.cpu_time || 0),
        realTime: Number(tc.real_time || 0),
        memory: Number(tc.memory || 0),
        score: Number(tc.score || 0),
        signal: tc.signal != null ? Number(tc.signal) : null,
        exitCode: tc.exit_code != null ? Number(tc.exit_code) : null
      }
    })
  }

  const submitSolution = async ({ problemId, problemQueryId, language, code, sessionId }) => {
    const sid = sessionId || '_default'
    submitLoading.value = true
    setSubmitResultForSession(sid, null)

    try {
      const parsedProblemId = Number(problemId)
      if (!Number.isInteger(parsedProblemId) || parsedProblemId <= 0) {
        throw new Error('Invalid problem id.')
      }

      const normalizedLanguage = sanitizeTextInput(language, 24)
      const normalizedCode = sanitizeTextInput(code, 20000)
      if (normalizedCode.length < 10) {
        throw new Error('Code must be at least 10 characters.')
      }

      const csrfToken = await ensureCsrfToken(apiClient)
      const submitResponse = await apiClient.submitCode(
        {
          problem_id: parsedProblemId,
          language: normalizedLanguage,
          code: normalizedCode
        },
        csrfToken
      )

      if (submitResponse.data?.error) {
        throw new Error(typeof submitResponse.data.data === 'string' ? submitResponse.data.data : submitResponse.data.error)
      }

      const submittedId = sanitizeTextInput(String(submitResponse.data?.data?.submission_id || ''), 64)
      if (!submittedId) {
        throw new Error('Submission id is missing in submit response.')
      }

      const startTimestamp = Date.now()
      const timeoutMs = 45000
      const intervalMs = 1500
      const queryProblemId = sanitizeTextInput(String(problemQueryId || problemId || ''), 64)
      const query = {
        myself: '1',
        ...(queryProblemId ? { problem_id: queryProblemId } : {}),
        limit: '20',
        page: '1'
      }

      let normalized = {
        status: 0,
        label: 'PENDING',
        display: 'Pending',
        icon: '⏳',
        color: '#9ca3af',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: submittedId,
        errInfo: '',
        testCases: []
      }
      setSubmitResultForSession(sid, normalized)

      while (Date.now() - startTimestamp <= timeoutMs) {
        const listResponse = await apiClient.fetchSubmissions(query)
        const payload = listResponse.data
        if (payload?.error) {
          throw new Error(typeof payload.data === 'string' ? payload.data : payload.error)
        }

        const rows = Array.isArray(payload.data?.results) ? payload.data.results : []
        const matchedRow = rows.find((row) => sanitizeTextInput(String(row?.id || ''), 64) === submittedId)
        if (!matchedRow) {
          await new Promise((resolve) => setTimeout(resolve, intervalMs))
          continue
        }

        normalized = normalizeSubmissionResult(matchedRow)
        setSubmitResultForSession(sid, normalized)

        if (isFinalSubmissionStatus(normalized.status)) {
          // Submission finished — fetch detailed test case results
          try {
            const detailResponse = await apiClient.fetchSubmissionDetail(submittedId)
            const detailData = detailResponse.data?.data
            if (detailData) {
              const info = detailData.info
              // Check for compile/system error in info.err
              if (info && typeof info === 'object' && typeof info.err === 'string' && info.err) {
                normalized.errInfo = info.err
              }
              // Handle compile error: info.data may be a string (compiler output)
              if (info && typeof info === 'object' && typeof info.data === 'string' && info.data) {
                normalized.errInfo = normalized.errInfo
                  ? normalized.errInfo + '\n\n' + info.data
                  : info.data
              }
              // Enrich with test case details from the detail API
              const testCases = parseTestCases(detailData)
              if (testCases.length > 0) {
                normalized.testCases = testCases
              }
              // Also update errInfo from statistic_info if available
              const detailStatInfo = detailData.statistic_info
              if (detailStatInfo && typeof detailStatInfo.err_info === 'string' && detailStatInfo.err_info) {
                normalized.errInfo = normalized.errInfo
                  ? normalized.errInfo + '\n\n' + detailStatInfo.err_info
                  : detailStatInfo.err_info
              }
              setSubmitResultForSession(sid, { ...normalized })
            }
          } catch (detailErr) {
            // Non-critical: test case detail is best-effort
            console.warn('Failed to fetch submission detail for test case info.', detailErr)
          }
          return normalized
        }

        await new Promise((resolve) => setTimeout(resolve, intervalMs))
      }

      return normalized || {
        status: null,
        label: 'TIMEOUT',
        display: 'Timeout',
        icon: '⏰',
        color: '#f59e0b',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: '',
        errInfo: '',
        testCases: []
      }
    } catch (error) {
      const failedResult = {
        status: null,
        label: 'ERROR',
        display: 'Error',
        icon: '❌',
        color: '#ef4444',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: '',
        errInfo: error.message || String(error),
        testCases: [],
        message: error.message || String(error)
      }
      setSubmitResultForSession(sid, failedResult)
      return failedResult
    } finally {
      submitLoading.value = false
    }
  }

  return {
    AUTH_MODES,
    authMode,
    authUsernameRef,
    authReady,
    ojUser,
    problems,
    problemLoading,
    problemError,
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
    hydrateAuthSession,
    fetchUserProfile,
    refreshCaptcha,
    login,
    register,
    logout,
    fetchProblems,
    submitSolution
  }
}
