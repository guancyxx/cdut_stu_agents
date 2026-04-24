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

// --- Chat message rendering: Markdown + HTML support ---

// Heuristic: content containing HTML block tags is treated as HTML source
const HTML_TAG_REGEX = /<(?:p|br|pre|code|blockquote|ul|ol|li|strong|b|em|i|u|span|h[1-6]|table|thead|tbody|tr|th|td|div|a|img|hr|dl|dt|dd|sup|sub|details|summary)\b[^>]*>/i

/**
 * Detect whether content should be rendered as HTML or Markdown.
 * - If content contains recognized HTML block tags -> HTML mode
 * - Otherwise -> Markdown mode
 */
export function detectContentType(content) {
  if (typeof content !== 'string' || !content.trim()) return 'text'
  if (HTML_TAG_REGEX.test(content)) return 'html'
  // Markdown indicators: headings, fenced blocks, lists, bold/italic, links
  if (/^#{1,6}\s/m.test(content) || /```/.test(content) || /\*\*[^*]+\*\*/.test(content) || /\[[^\]]+\]\([^)]+\)/.test(content) || /^[-*+]\s/m.test(content) || /^\d+\.\s/m.test(content)) return 'markdown'
  return 'text'
}

/**
 * Render chat message content to safe HTML.
 * - HTML content: sanitize with DOMPurify (allows safe HTML tags)
 * - Markdown content: parse with marked, then sanitize with DOMPurify
 * - Plain text: escape and wrap in <p>
 *
 * Returns an object { html, contentType } for downstream use.
 */
export function renderMessageContent(content) {
  if (typeof content !== 'string') return { html: '', contentType: 'text' }
  const trimmed = content.trim()
  if (!trimmed) return { html: '', contentType: 'text' }

  const contentType = detectContentType(trimmed)

  if (contentType === 'html') {
    return { html: dompurifySanitize(trimmed), contentType: 'html' }
  }

  if (contentType === 'markdown') {
    const rawHtml = markedParse(trimmed)
    return { html: dompurifySanitize(rawHtml), contentType: 'markdown' }
  }

  // Plain text: escape and wrap
  return { html: `<p>${escapeHtml(trimmed)}</p>`, contentType: 'text' }
}

// Lazy-loaded module references (set by initMessageRenderer)
let _marked = null
let _dompurify = null

/**
 * Initialize the message renderer with marked and DOMPurify instances.
 * Call once at app startup (e.g. in App.vue onMounted).
 */
export function initMessageRenderer(marked, dompurify) {
  _marked = marked
  _dompurify = dompurify

  if (marked && typeof marked.setOptions === 'function') {
    marked.setOptions({
      breaks: true,
      gfm: true
    })
  }
}

function markedParse(text) {
  if (!_marked) {
    // Fallback: return escaped text if marked not initialized
    return `<p>${escapeHtml(text)}</p>`
  }
  try {
    return _marked.parse(text)
  } catch {
    return `<p>${escapeHtml(text)}</p>`
  }
}

function dompurifySanitize(html) {
  if (!_dompurify) {
    // Fallback to the existing DOMParser-based sanitizer
    return sanitizeHtmlContent(html)
  }
  return _dompurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'pre', 'code', 'blockquote',
      'ul', 'ol', 'li',
      'strong', 'b', 'em', 'i', 'u', 'span', 'a', 'img',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'hr', 'div', 'sup', 'sub', 'details', 'summary',
      'dl', 'dt', 'dd', 'input', 'del'
    ],
    ALLOWED_ATTR: ['class', 'href', 'src', 'alt', 'title', 'target', 'rel', 'id', 'name', 'type', 'checked', 'disabled'],
    ADD_ATTR: ['target']
  })
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
