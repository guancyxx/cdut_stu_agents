import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// ── FOUC guard: apply data-theme before Vue mounts so the correct CSS vars are active ──
;(function () {
  const stored = localStorage.getItem('oj-theme')
  if (stored === 'light' || stored === 'dark') {
    document.documentElement.setAttribute('data-theme', stored)
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    document.documentElement.setAttribute('data-theme', 'light')
  }
})()

createApp(App).use(router).mount('#app')
