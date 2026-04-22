export function createApiClient(baseUrl = '/oj-api') {
  const requestJson = async (path, options = {}) => {
    const response = await fetch(`${baseUrl}${path}`, {
      credentials: 'include',
      ...options
    })

    const data = await response.json()
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

  const fetchProblems = (params) => {
    const query = new URLSearchParams(params)
    return requestJson(`/api/problem/?${query.toString()}`)
  }

  return {
    fetchProfile,
    fetchCaptcha,
    login,
    register,
    fetchProblems
  }
}
