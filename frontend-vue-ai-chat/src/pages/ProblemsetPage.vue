<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'
import { OJ_DIFFICULTY_OPTIONS } from '../utils/validators'

const router = useRouter()

const {
  problems, problemLoading, problemError,
  keyword, difficulty, currentPage, totalCount, totalPages,
  goToPage, searchProblems, fetchProblemDetail, fetchProblemTags, problemTags
} = useOjStore()

const { selectOrCreateProblemSession } = useChatStore()

const selectedTag = ref('')

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
  await fetchProblemDetail(String(problem._id))
  selectOrCreateProblemSession(problem)
  router.push('/')
}

const handleSearch = () => {
  selectedTag.value = ''
  searchProblems()
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

      <button @click="handleSearch">刷新</button>
    </div>

    <div class="problem-list" v-if="!problemLoading">
      <div class="problem-grid" v-if="filteredProblems.length">
        <button class="problem-item" v-for="p in filteredProblems" :key="p._id" @click="selectProblem(p)">
          <div class="problem-item-main">
            <div class="pid">{{ p._id }}</div>
            <div class="pdiff">{{ p.difficulty || 'Unknown' }}</div>
          </div>
          <div class="ptitle">{{ p.title }}</div>
        </button>
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
  </section>
</template>
