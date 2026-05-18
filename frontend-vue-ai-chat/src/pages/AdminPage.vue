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
const editingUsername = ref('')

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
  admin_type: 0,
  password: ''
})

const canManageSuperAdmin = computed(() => Number(ojUser.value?.adminType || 0) >= 2)

const normalizeAccount = (raw) => ({
  username: sanitizeTextInput(raw?.username || '', 32),
  email: sanitizeTextInput(raw?.email || '', 120),
  student_number: sanitizeTextInput(raw?.student_number || '', 64),
  admin_type: Number(raw?.admin_type || 0),
  created_at: sanitizeTextInput(raw?.created_at || '', 64),
  updated_at: sanitizeTextInput(raw?.updated_at || '', 64)
})

const loadAccounts = async () => {
  loading.value = true
  error.value = ''
  try {
    const resp = await apiClient.adminListAccounts()
    const payload = resp.data
    if (!resp.ok || payload?.error || payload?.detail) {
      throw new Error(payload?.detail || payload?.error || '加载账户失败')
    }
    const rows = Array.isArray(payload?.data?.results) ? payload.data.results : []
    accounts.value = rows.map(normalizeAccount)
  } catch (e) {
    error.value = e.message || '加载账户失败'
  } finally {
    loading.value = false
  }
}

const resetCreateForm = () => {
  createForm.username = ''
  createForm.password = ''
  createForm.email = ''
  createForm.student_number = ''
  createForm.admin_type = 0
}

const startEdit = (account) => {
  editingUsername.value = account.username
  editForm.email = account.email || ''
  editForm.student_number = account.student_number || ''
  editForm.admin_type = Number(account.admin_type || 0)
  editForm.password = ''
}

const cancelEdit = () => {
  editingUsername.value = ''
  editForm.email = ''
  editForm.student_number = ''
  editForm.admin_type = 0
  editForm.password = ''
}

const createAccount = async () => {
  message.value = ''
  error.value = ''

  const username = sanitizeTextInput(createForm.username, 32)
  if (!username) {
    error.value = '用户名不能为空'
    return
  }
  if (!createForm.password || createForm.password.length < 6) {
    error.value = '密码至少6位'
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
    error.value = '仅超级管理员可创建超级管理员账号'
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
    resetCreateForm()
    await loadAccounts()
  } catch (e) {
    error.value = e.message || '创建账号失败'
  } finally {
    loading.value = false
  }
}

const saveEdit = async (username) => {
  message.value = ''
  error.value = ''

  const payload = {
    email: sanitizeTextInput(editForm.email, 120),
    student_number: sanitizeTextInput(editForm.student_number, 64),
    admin_type: Math.max(0, Math.min(2, Number(editForm.admin_type || 0))),
    password: String(editForm.password || '')
  }

  if (!canManageSuperAdmin.value && payload.admin_type === 2) {
    error.value = '仅超级管理员可授予超级管理员权限'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminUpdateAccount(username, payload)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '更新账号失败')
    }
    message.value = `账号 ${username} 更新成功`
    cancelEdit()
    await loadAccounts()
  } catch (e) {
    error.value = e.message || '更新账号失败'
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

  const confirmed = window.confirm(`确认删除账号 ${username} ?`)
  if (!confirmed) return

  loading.value = true
  try {
    const resp = await apiClient.adminDeleteAccount(username)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || '删除账号失败')
    }
    message.value = `账号 ${username} 删除成功`
    if (editingUsername.value === username) cancelEdit()
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
    <h2>账户管理</h2>
    <p class="admin-account-desc">管理系统账号（创建、编辑、删除、权限调整）</p>

    <div class="error" v-if="!isAdmin">仅管理员可访问该页面</div>

    <div class="admin-account-panel" v-else>
      <div class="admin-account-alert success" v-if="message">{{ message }}</div>
      <div class="admin-account-alert error" v-if="error">{{ error }}</div>

      <div class="admin-account-create">
        <h3>新增账号</h3>
        <div class="admin-account-form-grid">
          <label>
            <span>用户名</span>
            <input v-model="createForm.username" maxlength="32" placeholder="username" />
          </label>
          <label>
            <span>初始密码</span>
            <input v-model="createForm.password" type="password" maxlength="128" placeholder="至少6位" />
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
            <span>管理员级别</span>
            <select v-model.number="createForm.admin_type">
              <option :value="0">Regular User</option>
              <option :value="1">Admin</option>
              <option :value="2" :disabled="!canManageSuperAdmin">Super Admin</option>
            </select>
          </label>
        </div>
        <div class="admin-account-actions">
          <button :disabled="loading" @click="createAccount">{{ loading ? '处理中...' : '创建账号' }}</button>
        </div>
      </div>

      <div class="admin-account-list">
        <h3>账号列表</h3>
        <div class="admin-account-list-empty" v-if="!loading && accounts.length === 0">暂无账号</div>
        <div class="admin-account-card" v-for="account in accounts" :key="account.username">
          <div class="admin-account-card-head">
            <div>
              <strong>{{ account.username }}</strong>
              <span class="admin-type-badge" :class="`admin-type-${account.admin_type}`">
                {{ account.admin_type === 2 ? 'Super Admin' : account.admin_type === 1 ? 'Admin' : 'Regular User' }}
              </span>
            </div>
            <div class="admin-account-meta">
              <span>created: {{ account.created_at || '-' }}</span>
              <span>updated: {{ account.updated_at || '-' }}</span>
            </div>
          </div>

          <div v-if="editingUsername !== account.username" class="admin-account-readonly">
            <div><span>Email:</span> {{ account.email || '-' }}</div>
            <div><span>Student Number:</span> {{ account.student_number || '-' }}</div>
            <div class="admin-account-actions">
              <button :disabled="loading" @click="startEdit(account)">编辑</button>
              <button :disabled="loading || account.username === ojUser.username" class="danger" @click="removeAccount(account)">
                删除
              </button>
            </div>
          </div>

          <div v-else class="admin-account-editing">
            <div class="admin-account-form-grid">
              <label>
                <span>邮箱</span>
                <input v-model="editForm.email" maxlength="120" />
              </label>
              <label>
                <span>学号</span>
                <input v-model="editForm.student_number" maxlength="64" />
              </label>
              <label>
                <span>管理员级别</span>
                <select v-model.number="editForm.admin_type">
                  <option :value="0">Regular User</option>
                  <option :value="1">Admin</option>
                  <option :value="2" :disabled="!canManageSuperAdmin">Super Admin</option>
                </select>
              </label>
              <label>
                <span>重置密码（可选）</span>
                <input v-model="editForm.password" type="password" maxlength="128" placeholder="不修改则留空" />
              </label>
            </div>
            <div class="admin-account-actions">
              <button :disabled="loading" @click="saveEdit(account.username)">保存</button>
              <button :disabled="loading" @click="cancelEdit">取消</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
