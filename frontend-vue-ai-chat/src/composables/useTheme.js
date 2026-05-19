// Light/dark theme composable — detect, toggle, persist.
// Reads localStorage first, then falls back to prefers-color-scheme, then defaults to dark.

import { ref, watchEffect } from 'vue'

const STORAGE_KEY = 'oj-theme'

function getSystemTheme() {
  if (!window.matchMedia) return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return getSystemTheme()
}

const themeSingleton = (() => {
  const theme = ref(getInitialTheme())

  // Apply to <html> reactively — no FOUC because main.js also applies once before mount
  watchEffect(() => {
    document.documentElement.setAttribute('data-theme', theme.value)
  })

  // Listen for system preference changes (only used if user has no manual override)
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored || (stored !== 'light' && stored !== 'dark')) {
        theme.value = e.matches ? 'light' : 'dark'
      }
    })
  }

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem(STORAGE_KEY, theme.value)
  }

  return { theme, toggleTheme }
})()

export function useTheme() {
  return themeSingleton
}
