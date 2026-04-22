export function readCookie(name) {
  const matched = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return matched ? decodeURIComponent(matched[1]) : ''
}

export async function ensureCsrfToken(apiClient) {
  await apiClient.fetchProfile()
  return readCookie('csrftoken')
}
