<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'
import { OJ_DIFFICULTY_OPTIONS } from '../utils/validators'
import AdminWorkspaceModal from '../components/AdminWorkspaceModal.vue'
import ProblemEditModal from '../components/ProblemEditModal.vue'

const router = useRouter()

const {
  problems, problemLoading, problemError,
  keyword, difficulty, currentPage, totalCount, totalPages,
  goToPage, searchProblems, fetchProblemDetail, fetchProblemTags, problemTags,
  isAdmin
} = useOjStore()

const { selectOrCreateProblemSession, sendProblemContextToAi } = useChatStore()

const selectedTag = ref('')
const showAdminWorkspaceModal = ref(false)
const editProblemTarget = ref(null)

const normalizedTags = (value) => {
  if (Array.isArray(value)) return value.map((item) => String(item || '').trim()).filter(Boolean)
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return []
}

const availableTags = computed(() => {
  const remote = Array.isArray(problemTags.value)
    ? problemTags.value.map((tag) => String(tag || '').trim()).filter(Boolean)
    : []

  if (remote.length > 0) {
    return Array.from(new Set(remote)).sort((a, b) => a.localeCompare(b, 'zh-CN'))
  }

  const set = new Set()
  for (const problem of problems.value) {
    const tags = normalizedTags(problem?.tags)
    for (const tag of tags) set.add(tag)
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

const filteredProblems = computed(() => {
  if (!selectedTag.value) return problems.value
  return problems.value.filter((problem) => normalizedTags(problem?.tags).includes(selectedTag.value))
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const delta = 2
  const pages = []
  const start = Math.max(1, current - delta)
  const end = Math.min(total, current + delta)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const selectProblem = async (problem) => {
  if (!problem?._id) return
  const detail = await fetchProblemDetail(String(problem._id))
  const session = selectOrCreateProblemSession(problem)
  if (session) {
    const problemContext = {
      ...problem,
      ...(detail || {}),
      _id: detail?._id || problem._id,
      title: detail?.title || problem.title,
      difficulty: detail?.difficulty || problem.difficulty,
      description: detail?.description || detail?.problem_description || problem.description || ''
    }
    await sendProblemContextToAi(problemContext, { targetSessionId: session.id })
  }
  router.push('/')
}

const handleProblemItemKeydown = (event, problem) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    selectProblem(problem)
  }
}

const openEditProblem = async (problem) => {
  if (!isAdmin.value || !problem?._id) return
  const detail = await fetchProblemDetail(String(problem._id))
  editProblemTarget.value = detail
    ? {
        ...problem,
        ...detail,
        _id: detail._id || problem._id,
        id: detail.id || problem.id,
        visible: detail.visible ?? problem.visible ?? false,
        tags: detail.tags || problem.tags || []
      }
    : {
        ...problem,
        visible: problem.visible ?? false,
        tags: problem.tags || []
      }
}

const handleSearch = () => {
  selectedTag.value = ''
  searchProblems()
}

const handleAfterProblemSaved = async () => {
  await searchProblems()
}

onMounted(() => {
  fetchProblemTags().catch(() => {})
})
</script>

<template>
  <section class="main-panel problem-panel">
    <div class="problem-toolbar">
      <input v-model="keyword" placeholder="搜索题目编号或关键词 (如 LQ1273)" @keyup.enter="handleSearch" />

      <select class="problem-filter-select" v-model="difficulty" @change="handleSearch">
        <option value="">全部难度</option>
        <option v-for="level in OJ_DIFFICULTY_OPTIONS.filter((item) => item)" :key="level" :value="level">
          {{ level }}
        </option>
      </select>

      <select class="problem-filter-select" v-model="selectedTag">
        <option value="">全部标签</option>
        <option v-for="tag in availableTags" :key="tag" :value="tag">
          {{ tag }}
        </option>
      </select>

      <div class="problem-toolbar-actions">
        <button @click="handleSearch">搜索</button>
        <button v-if="isAdmin" class="btn-admin-add" @click="showAdminWorkspaceModal = true">新增题目</button>
      </div>
    </div>

    <div class="problem-list scrollbar-unified" v-if="!problemLoading">
      <div class="problem-grid" v-if="filteredProblems.length">
        <article
          class="problem-item"
          v-for="p in filteredProblems"
          :key="p._id"
          role="button"
          tabindex="0"
          @click="selectProblem(p)"
          @keydown="handleProblemItemKeydown($event, p)"
        >
          <div class="problem-item-main">
            <div class="pid">{{ p._id }}</div>
            <div class="pdiff">{{ p.difficulty || 'Unknown' }}</div>
            <span v-if="p.ac" class="ac-badge" title="已通过">✓</span>
          </div>
          <div class="ptitle">{{ p.title }}</div>
          <div v-if="isAdmin" class="problem-admin-actions">
            <button class="btn-problem-edit" @click.stop="openEditProblem(p)">编辑</button>
          </div>
        </article>
      </div>
      <div v-else class="empty">暂无符合筛选条件的题目</div>
    </div>
    <div class="empty" v-else>加载中...</div>
    <div class="error" v-if="problemError">{{ problemError }}</div>

    <div class="pagination" v-if="!problemLoading && totalPages > 1">
      <button class="page-btn" :disabled="currentPage === 1" @click="goToPage(1)">&laquo;</button>
      <button class="page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">&lsaquo;</button>
      <button v-if="visiblePages[0] > 1" class="page-btn page-ellipsis" disabled>...</button>
      <button
        v-for="page in visiblePages"
        :key="page"
        class="page-btn"
        :class="{ active: page === currentPage }"
        @click="goToPage(page)"
      >{{ page }}</button>
      <button v-if="visiblePages[visiblePages.length - 1] < totalPages" class="page-btn page-ellipsis" disabled>...</button>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">&rsaquo;</button>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(totalPages)">&raquo;</button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }} ({{ totalCount }})</span>
    </div>

    <AdminWorkspaceModal
      v-if="showAdminWorkspaceModal"
      @close="showAdminWorkspaceModal = false"
    />

    <ProblemEditModal
      v-if="editProblemTarget"
      :problem="editProblemTarget"
      @close="editProblemTarget = null"
      @saved="handleAfterProblemSaved"
    />
  </section>
</template>
