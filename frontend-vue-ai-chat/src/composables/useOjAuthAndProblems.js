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

const DEFAULT_PROBLEM_QUERY = {
  limit: '100',
  page: '1'
}

export function useOjAuthAndProblems() {
  const apiClient = createApiClient('/oj-api')

  const authMode = ref(AUTH_MODES.LOGIN)
  const showAuthModal = ref(false)
  const authUsernameRef = ref(null)

  const ojUser = ref({
    username: '',
    password: '',
    email: '',
    captcha: '',
    captchaSrc: '',
    loggedIn: false,
    profileName: '',
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
    ojUser.value.loggedIn = true
    ojUser.value.profileName = usernameFromServer || ojUser.value.username
    ojUser.value.password = ''
    showAuthModal.value = false
  }

  const openAuthModal = async (nextTickCallback) => {
    showAuthModal.value = true
    resetAuthError()
    await nextTickCallback()
    authUsernameRef.value?.focus()
  }

  const closeAuthModal = () => {
    showAuthModal.value = false
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

    if (result.error) {
      ojUser.value.error = typeof result.data === 'string' ? result.data : result.error
      return
    }

    applyLoginSuccess(result.data?.username)
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

    if (result.error) {
      ojUser.value.error = typeof result.data === 'string' ? result.data : result.error
      await refreshCaptcha()
      return
    }

    applyLoginSuccess(validation.value.username)
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
      if (result.error) {
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
    showAuthModal,
    authUsernameRef,
    ojUser,
    problems,
    problemLoading,
    problemError,
    keyword,
    difficulty,
    isLoginMode,
    openAuthModal,
    closeAuthModal,
    refreshCaptcha,
    login,
    register,
    fetchProblems
  }
}
