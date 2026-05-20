<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { createApiClient } from '../services/apiClient'
import { useOjStore } from '../stores/ojStore'
import { sanitizeTextInput } from '../utils/validators'

const apiClient = createApiClient(import.meta.env.VITE_OJ_API_BASE_URL || '/oj-api', import.meta.env.VITE_AGENT_API_BASE_URL || '/oj-test-cases')

const { ojUser, isAdmin } = useOjStore()

const loading = ref(false)
const message = ref('')
const error = ref('')
const accounts = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showPasswordModal = ref(false)
const editTarget = ref('')
const passwordTarget = ref('')

const PAGE_SIZE = 12
const currentPage = ref(1)
const totalCount = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE)))

const createForm = reactive({
  username: '',
  password: '',
  email: '',
  student_number: '',
  admin_type: 0
})

const editForm = reactive({
  email: '',
  student_number: '',
  admin_type: 0
})

const passwordForm = reactive({
  password: ''
})

const canManageSuperAdmin = computed(() => Number(ojUser.value?.adminType || 0) >= 2)

const normalizeAccount = (raw) => ({
  username: sanitizeTextInput(raw?.username || '', 32),
  email: sanitizeTextInput(raw?.email || '', 120),
  student_number: sanitizeTextInput(raw?.student_number || '', 64),
  admin_type: Number(raw?.admin_type || 0),
  is_disabled: Boolean(raw?.is_disabled),
  created_at: sanitizeTextInput(raw?.created_at || '', 64),
  updated_at: sanitizeTextInput(raw?.updated_at || '', 64)
})

const adminTypeLabel = (t) => {
  if (t === 2) return '超级管理员'
  if (t === 1) return '管理员'
  return '普通用户'
}

const loadAccounts = async () => {
  loading.value = true
  error.value = ''
  try {
    const resp = await apiClient.adminListAccounts(currentPage.value, PAGE_SIZE)
    const payload = resp.data
    if (!resp.ok || payload?.error || payload?.detail) {
      throw new Error(payload?.detail || payload?.error || '加载账号列表失败')
    }
    totalCount.value = Number(payload?.data?.total || 0)
    const rows = Array.isArray(payload?.data?.results) ? payload.data.results : []
    accounts.value = rows.map(normalizeAccount)
  } catch (e) {
    error.value = e.message || '加载账号列表失败'
  } finally {
    loading.value = false
  }
}

const goToPage = (page) => {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
  loadAccounts()
}

const resetCreateForm = () => {
  createForm.username = ''
  createForm.password = ''
  createForm.email = ''
  createForm.student_number = ''
  createForm.admin_type = 0
}

const openCreateModal = () => {
  resetCreateForm()
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

const openEditModal = (account) => {
  editTarget.value = account.username
  editForm.email = account.email || ''
  editForm.student_number = account.student_number || ''
  editForm.admin_type = Number(account.admin_type || 0)
  showEditModal.value = true
}

const closeEditModal = () => {
  showEditModal.value = false
  editTarget.value = ''
}

const createAccount = async () => {
  message.value = ''
  error.value = ''

  const username = sanitizeTextInput(createForm.username, 32)
  if (!username) {
    error.value = '请输入用户名'
    return
  }
  if (!createForm.password || createForm.password.length < 6) {
    error.value = '密码至少6个字符'
    return
  }

  const payload = {
    username,
    password: String(createForm.password || ''),
    email: sanitizeTextInput(createForm.email, 120),
    student_number: sanitizeTextInput(createForm.student_number, 64),
    admin_type: Math.max(0, Math.min(2, Number(createForm.admin_type || 0)))
  }

  if (!canManageSuperAdmin.value && payload.admin_type === 2) {
    error.value = '只有超级管理员才能创建超级管理员账号'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminCreateAccount(payload)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '创建账号失败')
    }
    message.value = `账号 ${payload.username} 创建成功`
    closeCreateModal()
    currentPage.value = 1
    await loadAccounts()
  } catch (e) {
    error.value = e.message || '创建账号失败'
  } finally {
    loading.value = false
  }
}

const saveEdit = async () => {
  message.value = ''
  error.value = ''

  const payload = {
    email: sanitizeTextInput(editForm.email, 120),
    student_number: sanitizeTextInput(editForm.student_number, 64),
    admin_type: Math.max(0, Math.min(2, Number(editForm.admin_type || 0)))
  }

  if (!canManageSuperAdmin.value && payload.admin_type === 2) {
    error.value = '只有超级管理员才能设置超级管理员'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminUpdateAccount(editTarget.value, payload)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '编辑账号失败')
    }
    message.value = `账号 ${editTarget.value} 已更新`
    closeEditModal()
    await loadAccounts()
  } catch (e) {
    error.value = e.message || '编辑账号失败'
  } finally {
    loading.value = false
  }
}

const toggleAccountStatus = async (account) => {
  message.value = ''
  error.value = ''

  const username = account.username
  const newDisabled = !account.is_disabled

  if (username === sanitizeTextInput(ojUser.value?.username || '', 32)) {
    error.value = '不能禁用当前登录账号'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminSetAccountStatus(username, { is_disabled: newDisabled })
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '操作失败')
    }
    message.value = newDisabled ? `账号 ${username} 已禁用` : `账号 ${username} 已启用`
    await loadAccounts()
  } catch (e) {
    error.value = e.message || '操作失败'
  } finally {
    loading.value = false
  }
}

const openPasswordModal = (account) => {
  passwordTarget.value = account.username
  passwordForm.password = ''
  showPasswordModal.value = true
}

const closePasswordModal = () => {
  showPasswordModal.value = false
  passwordTarget.value = ''
}

const changePassword = async () => {
  message.value = ''
  error.value = ''

  if (!passwordForm.password || passwordForm.password.length < 6) {
    error.value = '密码至少6个字符'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminChangeAccountPassword(passwordTarget.value, {
      password: String(passwordForm.password)
    })
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '修改密码失败')
    }
    message.value = `${passwordTarget.value} 密码已修改`
    closePasswordModal()
  } catch (e) {
    error.value = e.message || '修改密码失败'
  } finally {
    loading.value = false
  }
}

const removeAccount = async (account) => {
  message.value = ''
  error.value = ''

  const username = account.username
  if (!username) return
  if (username === sanitizeTextInput(ojUser.value?.username || '', 32)) {
    error.value = '不能删除当前登录账号'
    return
  }

  const confirmed = window.confirm(`确定要删除账号 ${username} 吗？`)
  if (!confirmed) return

  loading.value = true
  try {
    const resp = await apiClient.adminDeleteAccount(username)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '删除账号失败')
    }
    message.value = `账号 ${username} 已删除`
    await loadAccounts()
  } catch (e) {
    error.value = e.message || '删除账号失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAccounts()
})
</script>

<template>
  <section class="admin-account-screen">
    <h2>账号管理</h2>
    <p class="admin-account-desc">管理系统账号</p>

    <div class="error" v-if="!isAdmin">需要管理员权限</div>

    <div class="admin-account-panel" v-else>
      <div class="admin-account-alert success" v-if="message">{{ message }}</div>
      <div class="admin-account-alert error" v-if="error">{{ error }}</div>

      <div class="admin-account-toolbar">
        <button class="btn-primary" :disabled="loading" @click="openCreateModal">
          + 新增账号
        </button>
      </div>

      <div class="admin-account-grid" v-if="!loading || accounts.length > 0">
        <div class="admin-account-grid-empty" v-if="!loading && accounts.length === 0">
          暂无账号
        </div>
        <div class="admin-account-card" v-for="account in accounts" :key="account.username">
          <div class="admin-account-card-avatar">
            {{ account.username.charAt(0).toUpperCase() }}
          </div>
          <div class="admin-account-card-body">
            <div class="admin-account-card-row">
              <strong class="admin-account-card-username">{{ account.username }}</strong>
              <div class="admin-account-card-badges">
                <span
                  class="admin-status-badge"
                  :class="account.is_disabled ? 'disabled' : 'enabled'"
                >
                  {{ account.is_disabled ? '已禁用' : '已启用' }}
                </span>
                <span v-if="account.admin_type > 0" class="admin-type-badge" :class="`admin-type-${account.admin_type}`">
                  {{ adminTypeLabel(account.admin_type) }}
                </span>
              </div>
            </div>
            <div class="admin-account-card-meta">
              <span class="admin-account-card-field">
                <span class="admin-account-card-label">邮箱</span>
                <span class="admin-account-card-value">{{ account.email || '-' }}</span>
              </span>
              <span class="admin-account-card-field">
                <span class="admin-account-card-label">学号</span>
                <span class="admin-account-card-value">{{ account.student_number || '-' }}</span>
              </span>
              <span class="admin-account-card-field admin-account-card-time">
                创建于 {{ account.created_at || '-' }}
              </span>
            </div>
            <div class="admin-account-card-actions">
              <button :disabled="loading" @click="openEditModal(account)" title="编辑">编辑</button>
              <button :disabled="loading" @click="openPasswordModal(account)" title="修改密码">改密</button>
              <button
                :disabled="loading"
                :class="account.is_disabled ? '' : 'warning'"
                @click="toggleAccountStatus(account)"
                :title="account.is_disabled ? '启用' : '禁用'"
              >{{ account.is_disabled ? '启用' : '禁用' }}</button>
              <button
                :disabled="loading || account.username === ojUser?.username"
                class="danger"
                @click="removeAccount(account)"
                title="删除"
              >删除</button>
            </div>
          </div>
        </div>
      </div>

      <div class="admin-account-pagination" v-if="totalPages > 1">
        <button :disabled="currentPage <= 1 || loading" @click="goToPage(currentPage - 1)">
          上一页
        </button>
        <span class="admin-account-page-info">
          第 {{ currentPage }} / {{ totalPages }} 页（共 {{ totalCount }} 条）
        </span>
        <button :disabled="currentPage >= totalPages || loading" @click="goToPage(currentPage + 1)">
          下一页
        </button>
      </div>

      <div class="admin-account-loading" v-if="loading && accounts.length === 0">加载中...</div>
    </div>

    <!-- 新增账号弹窗 -->
    <div class="modal-overlay" v-if="showCreateModal" @click.self="closeCreateModal">
      <div class="modal-container admin-create-modal" role="dialog" aria-label="新增账号">
        <div class="modal-header">
          <h3>新增账号</h3>
          <button class="modal-close-btn" @click="closeCreateModal" aria-label="关闭">&times;</button>
        </div>
        <div class="modal-body">
          <div class="admin-account-form-grid">
            <label>
              <span>用户名</span>
              <input v-model="createForm.username" maxlength="32" placeholder="用户名" />
            </label>
            <label>
              <span>初始密码</span>
              <input v-model="createForm.password" type="password" maxlength="128" placeholder="至少6个字符" />
            </label>
            <label>
              <span>邮箱</span>
              <input v-model="createForm.email" maxlength="120" placeholder="user@example.com" />
            </label>
            <label>
              <span>学号</span>
              <input v-model="createForm.student_number" maxlength="64" placeholder="可选" />
            </label>
            <label>
              <span>权限级别</span>
              <select v-model.number="createForm.admin_type">
                <option :value="0">普通用户</option>
                <option :value="1">管理员</option>
                <option :value="2" :disabled="!canManageSuperAdmin">超级管理员</option>
              </select>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button :disabled="loading" @click="createAccount">{{ loading ? '创建中...' : '创建' }}</button>
          <button :disabled="loading" @click="closeCreateModal">取消</button>
        </div>
      </div>
    </div>

    <!-- 编辑账号弹窗 -->
    <div class="modal-overlay" v-if="showEditModal" @click.self="closeEditModal">
      <div class="modal-container admin-edit-modal" role="dialog" aria-label="编辑账号">
        <div class="modal-header">
          <h3>编辑账号 — {{ editTarget }}</h3>
          <button class="modal-close-btn" @click="closeEditModal" aria-label="关闭">&times;</button>
        </div>
        <div class="modal-body">
          <div class="admin-account-form-grid">
            <label>
              <span>邮箱</span>
              <input v-model="editForm.email" maxlength="120" placeholder="可选" />
            </label>
            <label>
              <span>学号</span>
              <input v-model="editForm.student_number" maxlength="64" placeholder="可选" />
            </label>
            <label>
              <span>权限级别</span>
              <select v-model.number="editForm.admin_type">
                <option :value="0">普通用户</option>
                <option :value="1">管理员</option>
                <option :value="2" :disabled="!canManageSuperAdmin">超级管理员</option>
              </select>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button :disabled="loading" @click="saveEdit">{{ loading ? '保存中...' : '保存' }}</button>
          <button :disabled="loading" @click="closeEditModal">取消</button>
        </div>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <div class="modal-overlay" v-if="showPasswordModal" @click.self="closePasswordModal">
      <div class="modal-container admin-password-modal" role="dialog" aria-label="修改密码">
        <div class="modal-header">
          <h3>修改密码 — {{ passwordTarget }}</h3>
          <button class="modal-close-btn" @click="closePasswordModal" aria-label="关闭">&times;</button>
        </div>
        <div class="modal-body">
          <label>
            <span>新密码</span>
            <input v-model="passwordForm.password" type="password" maxlength="128" placeholder="至少6个字符" />
          </label>
        </div>
        <div class="modal-footer">
          <button :disabled="loading" @click="changePassword">{{ loading ? '保存中...' : '保存' }}</button>
          <button :disabled="loading" @click="closePasswordModal">取消</button>
        </div>
      </div>
    </div>
  </section>
</template>
