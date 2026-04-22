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

  return {
    AUTH_MODES,
    authMode,
    authUsernameRef,
    authReady,
    ojUser,
    problems,
    problemLoading,
    problemError,
    keyword,
    difficulty,
    isLoginMode,
    hydrateAuthSession,
    fetchUserProfile,
    refreshCaptcha,
    login,
    register,
    logout,
    fetchProblems
  }
}
