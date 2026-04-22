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

  return {
    fetchProfile,
    fetchCaptcha,
    login,
    register,
    logout,
    fetchProblems,
    submitCode,
    fetchSubmissions
  }
}
