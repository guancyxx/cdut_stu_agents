export function createApiClient(baseUrl = '/oj-api', aiAgentBaseUrl = '/oj-test-cases') {
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

  const fetchProblemDetail = (problemId) =>
    requestJson(`/api/problem/?problem_id=${encodeURIComponent(problemId)}`)

  const fetchProblemTags = () =>
    requestJson('/admin/problems/tags')

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

  const createContest = (payload) =>
    requestJson('/api/contest/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Referer: window.location.origin,
        Origin: window.location.origin
      },
      body: JSON.stringify(payload)
    })

  const fetchContests = (params = {}) => {
    const query = new URLSearchParams(params)
    return requestJson(`/api/contest/list?${query.toString()}`)
  }

  const fetchContestDetail = (contestId) =>
    requestJson(`/api/contest/detail?contest_id=${encodeURIComponent(contestId)}`)

  const joinContest = (payload) =>
    requestJson('/api/contest/join', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Referer: window.location.origin,
        Origin: window.location.origin
      },
      body: JSON.stringify(payload)
    })

  const submitContestCode = (payload) =>
    requestJson('/api/contest/submission', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Referer: window.location.origin,
        Origin: window.location.origin
      },
      body: JSON.stringify(payload)
    })

  const fetchContestRank = (contestId) =>
    requestJson(`/api/contest/rank?contest_id=${encodeURIComponent(contestId)}`)

  const fetchTestCaseContent = (params) => {
    const query = new URLSearchParams(params)
    return fetch(`${aiAgentBaseUrl}/test_case_content?${query.toString()}`, {
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

  const reportSubmissionFallback = (payload) =>
    fetch(`${aiAgentBaseUrl}/submission-events/fallback`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  // Admin problem upload API methods (all go through ai-agent-lite)
  const adminCreateProblem = (payload) =>
    fetch(`${aiAgentBaseUrl}/admin/problems/create`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  const adminBatchUpload = (formData) =>
    fetch(`${aiAgentBaseUrl}/admin/problems/upload/batch`, {
      method: 'POST',
      credentials: 'include',
      body: formData
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  const adminImportStatus = (taskId) =>
    fetch(`${aiAgentBaseUrl}/admin/problems/import/status/${encodeURIComponent(taskId)}`, {
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

  const adminFetchTags = () =>
    fetch(`${aiAgentBaseUrl}/admin/problems/tags`, {
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

  const adminUpdateProblem = (problemId, payload) =>
    fetch(`${aiAgentBaseUrl}/admin/problems/${encodeURIComponent(problemId)}`, {
      method: 'PUT',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  const adminListAccounts = (page = 1, size = 12) => {
    const params = new URLSearchParams({ page: String(page), size: String(size) })
    return fetch(`${baseUrl}/admin/accounts?${params.toString()}`, {
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

  const adminCreateAccount = (payload) =>
    fetch(`${baseUrl}/admin/accounts`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  const adminUpdateAccount = (username, payload) =>
    fetch(`${baseUrl}/admin/accounts/${encodeURIComponent(username)}`, {
      method: 'PUT',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  const adminDeleteAccount = (username) =>
    fetch(`${baseUrl}/admin/accounts/${encodeURIComponent(username)}`, {
      method: 'DELETE',
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

  const adminSetAccountStatus = (username, payload) =>
    fetch(`${baseUrl}/admin/accounts/${encodeURIComponent(username)}/status`, {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  const adminChangeAccountPassword = (username, payload) =>
    fetch(`${baseUrl}/admin/accounts/${encodeURIComponent(username)}/password`, {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(async (response) => {
      const rawText = await response.text()
      if (!rawText) return { ok: response.ok, status: response.status, data: { error: `Empty response (${response.status})`, data: '' } }
      try {
        return { ok: response.ok, status: response.status, data: JSON.parse(rawText) }
      } catch {
        return { ok: response.ok, status: response.status, data: { error: `Invalid JSON response (${response.status})`, data: rawText } }
      }
    })

  return {
    fetchProfile,
    fetchCaptcha,
    login,
    register,
    logout,
    fetchProblems,
    fetchProblemDetail,
    fetchProblemTags,
    submitCode,
    fetchSubmissions,
    fetchSubmissionDetail,
    createContest,
    fetchContests,
    fetchContestDetail,
    joinContest,
    submitContestCode,
    fetchContestRank,
    fetchTestCaseContent,
    reportSubmissionFallback,
    adminCreateProblem,
    adminBatchUpload,
    adminImportStatus,
    adminFetchTags,
    adminUpdateProblem,
    adminListAccounts,
    adminCreateAccount,
    adminUpdateAccount,
    adminDeleteAccount,
    adminSetAccountStatus,
    adminChangeAccountPassword
  }
}
