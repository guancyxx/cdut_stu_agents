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

const DEFAULT_PROBLEM_QUERY = {
  limit: '100',
  page: '1'
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
  const submitResult = ref(null)
  const keyword = ref('')
  const difficulty = ref('')

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

      const params = {
        ...DEFAULT_PROBLEM_QUERY,
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
    } catch (error) {
      problemError.value = error.message || String(error)
      problems.value = []
    } finally {
      problemLoading.value = false
    }
  }

  const normalizeSubmissionResult = (row) => {
    if (!row || typeof row !== 'object') {
      return {
        status: null,
        label: 'UNKNOWN',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: ''
      }
    }

    const status = Number(row.result)
    const statusMap = {
      '-2': 'COMPILING',
      '-1': 'SYSTEM_ERROR',
      '0': 'PENDING',
      '1': 'JUDGING',
      '2': 'COMPILING',
      '3': 'COMPILE_ERROR',
      '4': 'ACCEPTED',
      '5': 'PRESENTATION_ERROR',
      '6': 'WRONG_ANSWER',
      '7': 'TIME_LIMIT_EXCEEDED',
      '8': 'MEMORY_LIMIT_EXCEEDED',
      '9': 'RUNTIME_ERROR',
      '10': 'SYSTEM_ERROR'
    }

    const statisticInfo = row.statistic_info && typeof row.statistic_info === 'object' ? row.statistic_info : {}

    return {
      status,
      label: statusMap[String(status)] || 'UNKNOWN',
      score: Number(statisticInfo.score || 0),
      timeCost: Number(statisticInfo.time_cost || 0),
      memoryCost: Number(statisticInfo.memory_cost || 0),
      submissionId: sanitizeTextInput(String(row.id || ''), 64)
    }
  }

  const isFinalSubmissionStatus = (status) => ![0, 1, 2, -2].includes(status)

  const submitSolution = async ({ problemId, problemQueryId, language, code }) => {
    submitLoading.value = true
    submitResult.value = null

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
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: submittedId
      }
      submitResult.value = normalized

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
        submitResult.value = normalized

        if (isFinalSubmissionStatus(normalized.status)) {
          return normalized
        }

        await new Promise((resolve) => setTimeout(resolve, intervalMs))
      }

      return normalized || {
        status: null,
        label: 'TIMEOUT',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: ''
      }
    } catch (error) {
      const failedResult = {
        status: null,
        label: 'ERROR',
        score: 0,
        timeCost: 0,
        memoryCost: 0,
        submissionId: '',
        message: error.message || String(error)
      }
      submitResult.value = failedResult
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
    submitResult,
    keyword,
    difficulty,
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
