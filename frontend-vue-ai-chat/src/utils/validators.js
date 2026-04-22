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

const ALLOWED_HTML_TAGS = new Set([
  'p', 'br', 'pre', 'code', 'blockquote',
  'ul', 'ol', 'li',
  'strong', 'b', 'em', 'i', 'u', 'span',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'table', 'thead', 'tbody', 'tr', 'th', 'td'
])

const ALLOWED_HTML_ATTRIBUTES = new Set(['class'])

const isBrowserEnvironment =
  typeof window !== 'undefined' &&
  typeof DOMParser !== 'undefined' &&
  typeof Node !== 'undefined'

export function sanitizeHtmlContent(rawHtml) {
  if (typeof rawHtml !== 'string') return ''
  if (!isBrowserEnvironment) return sanitizeTextInput(rawHtml, 100000)

  const parser = new DOMParser()
  const documentNode = parser.parseFromString(rawHtml, 'text/html')

  const walk = (node) => {
    if (!node || !node.childNodes) return

    Array.from(node.childNodes).forEach((childNode) => {
      if (childNode.nodeType === Node.ELEMENT_NODE) {
        const tagName = childNode.tagName.toLowerCase()

        if (!ALLOWED_HTML_TAGS.has(tagName)) {
          const textNode = documentNode.createTextNode(childNode.textContent || '')
          childNode.replaceWith(textNode)
          return
        }

        Array.from(childNode.attributes).forEach((attribute) => {
          const attrName = attribute.name.toLowerCase()
          const attrValue = attribute.value || ''
          const isEventHandler = attrName.startsWith('on')
          const hasUnsafeProtocol = /javascript:|data:/i.test(attrValue)

          if (!ALLOWED_HTML_ATTRIBUTES.has(attrName) || isEventHandler || hasUnsafeProtocol) {
            childNode.removeAttribute(attribute.name)
          }
        })
      }

      walk(childNode)
    })
  }

  walk(documentNode.body)
  return documentNode.body.innerHTML
}
