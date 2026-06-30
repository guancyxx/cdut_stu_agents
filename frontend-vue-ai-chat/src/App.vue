<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useOjStore } from './stores/ojStore'
import { useChatStore } from './stores/chatStore'
import ProblemInfoPanel from './components/ProblemInfoPanel.vue'
import CodeSubmitPanel from './components/CodeSubmitPanel.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { useTheme } from './composables/useTheme'
import { AUTH_MODES, OJ_DIFFICULTY_OPTIONS, initMessageRenderer } from './utils/validators'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const router = useRouter()
const route = useRoute()

const {
  authMode,
  authReady,
  ojUser,
  isLoginMode,
  isAdmin,
  hydrateAuthSession,
  fetchUserProfile,
  refreshCaptcha,
  login,
  register,
  logout,
  fetchProblems,
  fetchContests
} = useOjStore()

const {
  sessions,
  currentSessionId,
  switchToUser,
  loadSessions,
  selectSession,
  deleteOneSession,
  closeSocket
} = useChatStore()

// ─── Computed ───────────────────────────────────────────────────────────────

const requiresAuth = computed(() => authReady.value && !ojUser.value.loggedIn)

const routeTitle = computed(() => route.meta?.title || 'CDUT AI')

const showLayout = computed(() => {
  if (requiresAuth.value) return false
  return route.name === 'home' || route.name === 'problemset'
})

const panelCollapsed = reactive({ chat: false, problem: false, code: false })

const gridCols = computed(() => {
  if (route.name === 'problemset') return '260px 1fr'
  const w = (key) => panelCollapsed[key] ? '40px' : '1fr'
  return `260px ${w('chat')} ${w('problem')} ${w('code')}`
})

const authActionText = computed(() =>
  ojUser.value.loggedIn ? ojUser.value.profileName : '去登录'
)

// ─── Navigation ─────────────────────────────────────────────────────────────

const navItems = computed(() => {
  const items = [
    { label: '主页', to: '/' },
    { label: '题库', to: '/problemset' },
    { label: '比赛', to: '/contest' }
  ]
  if (isAdmin.value) {
    items.push({ label: '管理', to: '/admin' })
  }
  items.push({ label: '个人中心', to: '/profile' })
  return items
})

const goToAuth = () => {
  if (ojUser.value.loggedIn) {
    router.push('/profile')
    fetchUserProfile().catch(() => {})
    return
  }
  router.push('/auth')
}

const handleLogout = async () => {
  await logout()
  switchToUser('')
  router.push('/auth')
}

const handleClearAllSessions = () => {
  const { clearAllConversationData } = useChatStore()
  clearAllConversationData()
  router.push('/problemset')
}

const handleSelectSession = (sessionId) => {
  selectSession(sessionId)
  router.push('/')
}

const handleDeleteSession = (sessionId) => {
  deleteOneSession(sessionId)
}

const getSessionTag = (session) => {
  if (session?.problemId) return String(session.problemId)
  return String(session?.id || 'chat').slice(-4)
}

// ─── Auth guard: redirect to auth page if not logged in ─────────────────────

watch(
  [authReady, () => ojUser.value.loggedIn],
  ([ready, loggedIn]) => {
    if (!ready) return
    if (!loggedIn && route.name !== 'auth') {
      router.replace('/auth')
    }
  }
)

// Protect admin route
watch(
  () => route.name,
  (name) => {
    if (name === 'admin' && !isAdmin.value) {
      router.replace('/')
    }
  }
)

// ─── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  initMessageRenderer(marked, DOMPurify)
  loadSessions()
  await hydrateAuthSession()

  if (!ojUser.value.loggedIn) {
    await refreshCaptcha()
    router.replace('/auth')
    return
  }

  switchToUser(ojUser.value.profileName || ojUser.value.username)
  await fetchProblems()
  await fetchContests('all')

  if (route.name === 'auth') {
    router.replace('/')
  }
})

onBeforeUnmount(() => {
  closeSocket()
})
</script>

<template>
  <div class="app-shell">
    <!-- ─── Top Navigation ──────────────────────────────────────────────── -->
    <header class="top-nav">
      <div class="top-brand">
        <img src="/logo.svg" alt="CDUT AI" class="top-logo" />
        <span class="top-brand-name">CDUT AI 学习助手</span>
      </div>

      <!-- Authenticated nav -->
      <nav class="tabs" v-if="!requiresAuth">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          active-class="active"
          exact-active-class="active"
        >{{ item.label }}</router-link>
      </nav>

      <!-- Unauthenticated nav -->
      <nav class="tabs" v-else>
        <router-link to="/auth" active-class="active">登录 / 注册</router-link>
      </nav>

      <div class="top-status-wrap">
        <ThemeToggle />
        <button
          class="auth-open-btn"
          :class="{ 'auth-user-btn': ojUser.loggedIn }"
          @click="goToAuth"
        >
          {{ authActionText }}
        </button>
      </div>
    </header>

    <!-- ─── Auth Screen (full-page, no layout) ──────────────────────────── -->
    <router-view v-if="requiresAuth" />

    <!-- ─── Main Layout ───────────────────────────────────────────────── -->
    <div
      class="content-grid"
      :style="{ gridTemplateColumns: gridCols }"
      v-else-if="showLayout"
    >
      <!-- Left sidebar: sessions (fixed width, no collapse) -->
      <aside class="left-sidebar">
        <div class="card sessions-card">
          <div class="session-header-row">
            <div class="session-count">{{ sessions.length }} 会话</div>
            <button
              class="session-clear-btn"
              type="button"
              title="清空所有对话"
              @click="handleClearAllSessions"
            >clear</button>
          </div>
          <div class="session-list scrollbar-unified">
            <div
              v-for="s in sessions"
              :key="s.id"
              class="session-item"
              :class="{ active: s.id === currentSessionId }"
              role="button"
              tabindex="0"
              @click="handleSelectSession(s.id)"
              @keydown.enter.space.prevent="handleSelectSession(s.id)"
            >
              <div class="session-main">
                <div class="session-tag">{{ getSessionTag(s) }}</div>
                <div class="stitle">{{ s.title }}</div>
                <div class="smeta">{{ new Date(s.createdAt).toLocaleString() }}</div>
              </div>
              <button
                class="session-delete-btn"
                type="button"
                title="删除此会话"
                @click.stop="handleDeleteSession(s.id)"
              >&times;</button>
            </div>
          </div>
        </div>
      </aside>

      <!-- Chat panel (collapsible) -->
      <div class="panel-wrapper" :class="{ collapsed: panelCollapsed.chat }">
        <div class="panel-header" v-show="!panelCollapsed.chat">
          <span class="panel-title">AI 对话</span>
          <button class="panel-toggle-btn" title="折叠" @click="panelCollapsed.chat = true">◀</button>
        </div>
        <div class="panel-strip" v-show="panelCollapsed.chat">
          <button class="panel-toggle-btn" title="展开" @click="panelCollapsed.chat = false">▶</button>
          <span class="panel-title-v">AI 对话</span>
        </div>
        <div class="panel-body" v-show="!panelCollapsed.chat">
          <router-view />
        </div>
      </div>

      <!-- Problem info panel (home only, collapsible) -->
      <div class="panel-wrapper" v-if="route.name === 'home'" :class="{ collapsed: panelCollapsed.problem }">
        <div class="panel-header" v-show="!panelCollapsed.problem">
          <span class="panel-title">题目信息</span>
          <button class="panel-toggle-btn" title="折叠" @click="panelCollapsed.problem = true">◀</button>
        </div>
        <div class="panel-strip" v-show="panelCollapsed.problem">
          <button class="panel-toggle-btn" title="展开" @click="panelCollapsed.problem = false">▶</button>
          <span class="panel-title-v">题目信息</span>
        </div>
        <div class="panel-body" v-show="!panelCollapsed.problem">
          <ProblemInfoPanel />
        </div>
      </div>

      <!-- Code submit panel (home only, collapsible) -->
      <div class="panel-wrapper" v-if="route.name === 'home'" :class="{ collapsed: panelCollapsed.code }">
        <div class="panel-header" v-show="!panelCollapsed.code">
          <span class="panel-title">代码提交</span>
          <button class="panel-toggle-btn" title="折叠" @click="panelCollapsed.code = true">◀</button>
        </div>
        <div class="panel-strip" v-show="panelCollapsed.code">
          <button class="panel-toggle-btn" title="展开" @click="panelCollapsed.code = false">▶</button>
          <span class="panel-title-v">代码提交</span>
        </div>
        <div class="panel-body" v-show="!panelCollapsed.code">
          <CodeSubmitPanel />
        </div>
      </div>
    </div>

    <!-- ─── Full-Width Pages (contest / admin / profile) ────────────────── -->
    <router-view v-else />
  </div>
</template>

<style>
.admin-screen {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.admin-actions-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.btn-create-contest {
  padding: 8px 18px;
  border-radius: 6px;
  border: 1px solid var(--border-standard);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: 0.9rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-create-contest:hover {
  background: var(--bg-soft-hover);
}
</style>
