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
const showCreateModal = ref(false)
const showPasswordModal = ref(false)
const passwordTarget = ref('')

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

const loadAccounts = async () => {
  loading.value = true
  error.value = ''
  try {
    const resp = await apiClient.adminListAccounts()
    const payload = resp.data
    if (!resp.ok || payload?.error || payload?.detail) {
      throw new Error(payload?.detail || payload?.error || 'Failed to load accounts')
    }
    const rows = Array.isArray(payload?.data?.results) ? payload.data.results : []
    accounts.value = rows.map(normalizeAccount)
  } catch (e) {
    error.value = e.message || 'Failed to load accounts'
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

const openCreateModal = () => {
  resetCreateForm()
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

const startEdit = (account) => {
  editingUsername.value = account.username
  editForm.email = account.email || ''
  editForm.student_number = account.student_number || ''
  editForm.admin_type = Number(account.admin_type || 0)
}

const cancelEdit = () => {
  editingUsername.value = ''
  editForm.email = ''
  editForm.student_number = ''
  editForm.admin_type = 0
}

const createAccount = async () => {
  message.value = ''
  error.value = ''

  const username = sanitizeTextInput(createForm.username, 32)
  if (!username) {
    error.value = 'Username is required'
    return
  }
  if (!createForm.password || createForm.password.length < 6) {
    error.value = 'Password must be at least 6 characters'
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
    error.value = 'Only super admin can create super admin account'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminCreateAccount(payload)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || 'Failed to create account')
    }
    message.value = `Account ${payload.username} created`
    closeCreateModal()
    await loadAccounts()
  } catch (e) {
    error.value = e.message || 'Failed to create account'
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
    admin_type: Math.max(0, Math.min(2, Number(editForm.admin_type || 0)))
  }

  if (!canManageSuperAdmin.value && payload.admin_type === 2) {
    error.value = 'Only super admin can assign super admin'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminUpdateAccount(username, payload)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || 'Failed to update account')
    }
    message.value = `Account ${username} updated`
    cancelEdit()
    await loadAccounts()
  } catch (e) {
    error.value = e.message || 'Failed to update account'
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
    error.value = 'Cannot disable current login account'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminSetAccountStatus(username, { is_disabled: newDisabled })
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || 'Failed to change account status')
    }
    message.value = newDisabled ? `Account ${username} disabled` : `Account ${username} enabled`
    await loadAccounts()
  } catch (e) {
    error.value = e.message || 'Failed to change account status'
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
    error.value = 'Password must be at least 6 characters'
    return
  }

  loading.value = true
  try {
    const resp = await apiClient.adminChangeAccountPassword(passwordTarget.value, {
      password: String(passwordForm.password)
    })
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || 'Failed to change password')
    }
    message.value = `Password changed for ${passwordTarget.value}`
    closePasswordModal()
  } catch (e) {
    error.value = e.message || 'Failed to change password'
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
    error.value = 'Cannot delete current login account'
    return
  }

  const confirmed = window.confirm(`Are you sure you want to delete account ${username}?`)
  if (!confirmed) return

  loading.value = true
  try {
    const resp = await apiClient.adminDeleteAccount(username)
    const body = resp.data
    if (!resp.ok || body?.error || body?.detail) {
      throw new Error(body?.detail || body?.error || 'Failed to delete account')
    }
    message.value = `Account ${username} deleted`
    if (editingUsername.value === username) cancelEdit()
    await loadAccounts()
  } catch (e) {
    error.value = e.message || 'Failed to delete account'
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
    <h2>Account Management</h2>
    <p class="admin-account-desc">Manage system accounts</p>

    <div class="error" v-if="!isAdmin">Admin access required</div>

    <div class="admin-account-panel" v-else>
      <div class="admin-account-alert success" v-if="message">{{ message }}</div>
      <div class="admin-account-alert error" v-if="error">{{ error }}</div>

      <div class="admin-account-toolbar">
        <button class="btn-primary" :disabled="loading" @click="openCreateModal">
          + New Account
        </button>
      </div>

      <div class="admin-account-list" v-if="!loading || accounts.length > 0">
        <div class="admin-account-list-empty" v-if="!loading && accounts.length === 0">
          No accounts found
        </div>
        <div class="admin-account-card" v-for="account in accounts" :key="account.username">
          <div class="admin-account-card-head">
            <div class="admin-account-identity">
              <strong>{{ account.username }}</strong>
              <span v-if="account.is_disabled" class="admin-status-badge disabled">Disabled</span>
              <span v-else class="admin-status-badge enabled">Enabled</span>
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
              <button :disabled="loading" @click="startEdit(account)">Edit</button>
              <button :disabled="loading" @click="openPasswordModal(account)">Reset Password</button>
              <button
                :disabled="loading || account.username === ojUser?.username"
                :class="account.is_disabled ? '' : 'warning'"
                @click="toggleAccountStatus(account)"
              >
                {{ account.is_disabled ? 'Enable' : 'Disable' }}
              </button>
              <button
                :disabled="loading || account.username === ojUser?.username"
                class="danger"
                @click="removeAccount(account)"
              >
                Delete
              </button>
            </div>
          </div>

          <div v-else class="admin-account-editing">
            <div class="admin-account-form-grid">
              <label>
                <span>Email</span>
                <input v-model="editForm.email" maxlength="120" />
              </label>
              <label>
                <span>Student Number</span>
                <input v-model="editForm.student_number" maxlength="64" />
              </label>
              <label>
                <span>Admin Level</span>
                <select v-model.number="editForm.admin_type">
                  <option :value="0">Regular User</option>
                  <option :value="1">Admin</option>
                  <option :value="2" :disabled="!canManageSuperAdmin">Super Admin</option>
                </select>
              </label>
            </div>
            <div class="admin-account-actions">
              <button :disabled="loading" @click="saveEdit(account.username)">Save</button>
              <button :disabled="loading" @click="cancelEdit">Cancel</button>
            </div>
          </div>
        </div>
      </div>

      <div class="admin-account-loading" v-if="loading && accounts.length === 0">Loading...</div>
    </div>

    <!-- Create Account Modal -->
    <div class="modal-overlay" v-if="showCreateModal" @click.self="closeCreateModal">
      <div class="modal-container admin-create-modal" role="dialog" aria-label="Create new account">
        <div class="modal-header">
          <h3>New Account</h3>
          <button class="modal-close-btn" @click="closeCreateModal" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="admin-account-form-grid">
            <label>
              <span>Username</span>
              <input v-model="createForm.username" maxlength="32" placeholder="username" />
            </label>
            <label>
              <span>Initial Password</span>
              <input v-model="createForm.password" type="password" maxlength="128" placeholder="at least 6 chars" />
            </label>
            <label>
              <span>Email</span>
              <input v-model="createForm.email" maxlength="120" placeholder="user@example.com" />
            </label>
            <label>
              <span>Student Number</span>
              <input v-model="createForm.student_number" maxlength="64" placeholder="optional" />
            </label>
            <label>
              <span>Admin Level</span>
              <select v-model.number="createForm.admin_type">
                <option :value="0">Regular User</option>
                <option :value="1">Admin</option>
                <option :value="2" :disabled="!canManageSuperAdmin">Super Admin</option>
              </select>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button :disabled="loading" @click="createAccount">{{ loading ? 'Creating...' : 'Create' }}</button>
          <button :disabled="loading" @click="closeCreateModal">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Password Reset Modal -->
    <div class="modal-overlay" v-if="showPasswordModal" @click.self="closePasswordModal">
      <div class="modal-container admin-password-modal" role="dialog" aria-label="Reset account password">
        <div class="modal-header">
          <h3>Reset Password — {{ passwordTarget }}</h3>
          <button class="modal-close-btn" @click="closePasswordModal" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <label>
            <span>New Password</span>
            <input v-model="passwordForm.password" type="password" maxlength="128" placeholder="at least 6 chars" />
          </label>
        </div>
        <div class="modal-footer">
          <button :disabled="loading" @click="changePassword">{{ loading ? 'Saving...' : 'Save' }}</button>
          <button :disabled="loading" @click="closePasswordModal">Cancel</button>
        </div>
      </div>
    </div>
  </section>
</template>
