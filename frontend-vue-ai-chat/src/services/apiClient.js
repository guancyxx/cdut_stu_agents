export function createApiClient(baseUrl = '/oj-api') {
  const requestJson = async (path, options = {}) => {
    const response = await fetch(`${baseUrl}${path}`, {
      credentials: 'include',
      ...options
    })

    const rawText = await response.text()
    let data = null

    if (rawText) {
      try {
        data = JSON.parse(rawText)
      } catch {
        data = {
          error: `Invalid JSON response (${response.status})`,
          data: rawText
        }
      }
    } else {
      data = {
        error: `Empty response (${response.status})`,
        data: ''
      }
    }

    return {
      ok: response.ok,
      status: response.status,
      data
    }
  }

  const fetchProfile = () => requestJson('/api/profile')

  const fetchCaptcha = () => requestJson('/api/captcha?refresh=1')

  const login = (payload, csrfToken) =>
    requestJson('/api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        Referer: window.location.origin
      },
      body: JSON.stringify(payload)
    })

  const register = (payload, csrfToken) =>
    requestJson('/api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        Referer: window.location.origin
      },
      body: JSON.stringify(payload)
    })

  const logout = (csrfToken) =>
    requestJson('/api/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
        Referer: window.location.origin
      },
      body: JSON.stringify({})
    })

  const fetchProblems = (params) => {
    const query = new URLSearchParams(params)
    return requestJson(`/api/problem/?${query.toString()}`)
  }

  const submitCode = (payload, csrfToken) =>
    requestJson('/api/submission', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
        Referer: window.location.origin,
        Origin: window.location.origin
      },
      body: JSON.stringify(payload)
    })

  const fetchSubmissions = (params = {}) => {
    const query = new URLSearchParams(params)
    return requestJson(`/api/submissions?${query.toString()}`)
  }

  const fetchSubmissionDetail = (submissionId) =>
    requestJson(`/api/submission?id=${encodeURIComponent(submissionId)}`)

  const fetchTestCaseContent = (params) => {
    // Uses a separate base URL that routes through ai-agent-lite proxy
    // Vite config rewrites /oj-test-cases/* -> ai-agent-lite:8848/oj/*
    const query = new URLSearchParams(params)
    return fetch(`/oj-test-cases/test_case_content?${query.toString()}`, {
      credentials: 'include'
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })
  }

  return {
    fetchProfile,
    fetchCaptcha,
    login,
    register,
    logout,
    fetchProblems,
    submitCode,
    fetchSubmissions,
    fetchSubmissionDetail,
    fetchTestCaseContent
  }
}
