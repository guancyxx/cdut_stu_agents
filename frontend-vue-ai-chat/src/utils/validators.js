export const AUTH_MODES = {
  LOGIN: 'login',
  REGISTER: 'register'
}

export const OJ_DIFFICULTY_OPTIONS = ['', 'Low', 'Mid', 'High']

const USERNAME_REGEX = /^[A-Za-z0-9_]{3,32}$/
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function sanitizeTextInput(value, maxLength = 4000) {
  if (typeof value !== 'string') return ''
  return value.trim().slice(0, maxLength)
}

export function validateChatInput(value) {
  const query = sanitizeTextInput(value, 4000)
  if (!query) {
    return { valid: false, message: 'Message is required.' }
  }
  return { valid: true, value: query }
}

export function validateLoginPayload(payload) {
  const username = sanitizeTextInput(payload.username, 32)
  const password = sanitizeTextInput(payload.password, 128)

  if (!USERNAME_REGEX.test(username)) {
    return { valid: false, message: 'Username must be 3-32 chars: letters, numbers, underscore.' }
  }

  if (password.length < 6) {
    return { valid: false, message: 'Password must be at least 6 characters.' }
  }

  return {
    valid: true,
    value: {
      username,
      password
    }
  }
}

export function validateRegisterPayload(payload) {
  const base = validateLoginPayload(payload)
  if (!base.valid) return base

  const email = sanitizeTextInput(payload.email, 120)
  const captcha = sanitizeTextInput(payload.captcha, 16)

  if (!EMAIL_REGEX.test(email)) {
    return { valid: false, message: 'Email format is invalid.' }
  }

  if (!captcha) {
    return { valid: false, message: 'Captcha is required.' }
  }

  return {
    valid: true,
    value: {
      ...base.value,
      email,
      captcha
    }
  }
}

export function validateDifficulty(value) {
  if (!OJ_DIFFICULTY_OPTIONS.includes(value)) {
    return ''
  }
  return value
}
