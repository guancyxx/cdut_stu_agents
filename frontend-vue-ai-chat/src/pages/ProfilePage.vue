<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'
import { sanitizeTextInput } from '../utils/validators'

const router = useRouter()
const { ojUser, logout, updateUserProfile, changeUserPassword } = useOjStore()
const { switchToUser } = useChatStore()

const activeSection = ref('account')
const editing = ref(false)
const saving = ref(false)
const passwordSaving = ref(false)

const profileState = reactive({
  email: '',
  studentNumber: '',
  signature: '',
  message: '',
  error: ''
})

const passwordState = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
  message: '',
  error: ''
})

const navItems = [
  { key: 'account', label: '账号信息' },
  { key: 'security', label: '安全设置' },
  { key: 'personalization', label: '个性化' },
  { key: 'contest', label: '竞赛数据' }
]

const roleLabel = computed(() => {
  if (ojUser.value.adminType >= 2) return 'Super Admin'
  if (ojUser.value.adminType >= 1) return 'Admin'
  return 'Regular User'
})

const profileName = computed(() => ojUser.value.profileName || ojUser.value.username || '未命名用户')
const avatarFallback = computed(() => profileName.value.slice(0, 1).toUpperCase())

const profileCompletion = computed(() => {
  const fields = [ojUser.value.email, ojUser.value.studentNumber, ojUser.value.signature]
  const filled = fields.filter((value) => String(value || '').trim().length > 0).length
  return Math.round((filled / fields.length) * 100)
})

const contestHighlights = computed(() => {
  return [
    { label: '登录状态', value: ojUser.value.loggedIn ? '在线' : '离线' },
    { label: '身份级别', value: roleLabel.value },
    { label: '资料完整度', value: `${profileCompletion.value}%` }
  ]
})

const syncDraftFromUser = () => {
  profileState.email = ojUser.value.email || ''
  profileState.studentNumber = ojUser.value.studentNumber || ''
  profileState.signature = ojUser.value.signature || ''
}

const startEdit = (section = 'account') => {
  profileState.message = ''
  profileState.error = ''
  passwordState.message = ''
  passwordState.error = ''
  syncDraftFromUser()
  activeSection.value = section
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
  profileState.message = ''
  profileState.error = ''
  syncDraftFromUser()
}

const saveProfile = async () => {
  profileState.message = ''
  profileState.error = ''
  passwordState.message = ''
  saving.value = true
  try {
    await updateUserProfile({
      email: sanitizeTextInput(profileState.email, 120),
      studentNumber: sanitizeTextInput(profileState.studentNumber, 64),
      signature: sanitizeTextInput(profileState.signature, 280)
    })
    profileState.message = '个人资料已更新'
    editing.value = false
  } catch (error) {
    profileState.error = error?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

const clearPasswordForm = () => {
  passwordState.oldPassword = ''
  passwordState.newPassword = ''
  passwordState.confirmPassword = ''
}

const savePassword = async () => {
  passwordState.message = ''
  passwordState.error = ''
  profileState.message = ''

  const oldPassword = String(passwordState.oldPassword || '')
  const newPassword = String(passwordState.newPassword || '')
  const confirmPassword = String(passwordState.confirmPassword || '')

  if (!oldPassword || !newPassword || !confirmPassword) {
    passwordState.error = '请填写旧密码、新密码和确认密码'
    return
  }
  if (newPassword.length < 6) {
    passwordState.error = '新密码至少 6 位'
    return
  }
  if (newPassword !== confirmPassword) {
    passwordState.error = '两次输入的新密码不一致'
    return
  }

  passwordSaving.value = true
  try {
    await changeUserPassword({ oldPassword, newPassword })
    passwordState.message = '密码修改成功'
    clearPasswordForm()
  } catch (error) {
    passwordState.error = error?.message || '密码修改失败'
  } finally {
    passwordSaving.value = false
  }
}

const handleLogout = async () => {
  const succeeded = await logout()
  if (!succeeded) return
  switchToUser('')
  router.replace('/auth')
}
</script>

<template>
  <section class="profile-v2-screen">
    <div class="profile-v2-page card">
      <header class="profile-v2-hero">
        <div class="profile-v2-hero-main">
          <div class="profile-avatar" v-if="ojUser.avatar">
            <img :src="ojUser.avatar" alt="avatar" />
          </div>
          <div class="profile-avatar profile-avatar-fallback" v-else>{{ avatarFallback }}</div>

          <div class="profile-v2-title-group">
            <h2>{{ profileName }}</h2>
            <div class="profile-v2-meta-row">
              <span class="profile-v2-role-badge">{{ roleLabel }}</span>
              <span>{{ ojUser.email || 'No email available' }}</span>
            </div>
            <p class="profile-v2-signature">{{ ojUser.signature || '还没有个性签名，去设置一句你的竞赛宣言吧。' }}</p>
          </div>
        </div>

        <div class="profile-v2-hero-actions">
          <button class="secondary-btn" @click="router.push('/')">返回主页</button>
          <button class="secondary-btn" @click="startEdit('account')">编辑资料</button>
          <button class="danger-btn" @click="handleLogout">退出登录</button>
        </div>
      </header>

      <div class="profile-v2-layout">
        <aside class="profile-v2-nav card">
          <button
            v-for="item in navItems"
            :key="item.key"
            class="profile-v2-nav-item"
            :class="{ active: activeSection === item.key }"
            @click="activeSection = item.key"
          >
            {{ item.label }}
          </button>
        </aside>

        <main class="profile-v2-content">
          <section v-show="activeSection === 'account'" class="profile-v2-section card">
            <div class="profile-v2-section-head">
              <h3>账号信息</h3>
              <button v-if="!editing" class="secondary-btn" @click="startEdit('account')">编辑</button>
            </div>

            <div class="profile-grid" v-if="!editing">
              <div class="profile-item">
                <span>用户名</span>
                <strong>{{ ojUser.username || '-' }}</strong>
              </div>
              <div class="profile-item">
                <span>邮箱</span>
                <strong>{{ ojUser.email || '-' }}</strong>
              </div>
              <div class="profile-item">
                <span>学号</span>
                <strong>{{ ojUser.studentNumber || '-' }}</strong>
              </div>
              <div class="profile-item">
                <span>角色</span>
                <strong>{{ roleLabel }}</strong>
              </div>
            </div>

            <form class="profile-edit-form" v-else @submit.prevent="saveProfile">
              <label>
                <span>邮箱</span>
                <input v-model="profileState.email" maxlength="120" type="email" placeholder="请输入邮箱" />
              </label>
              <label>
                <span>学号</span>
                <input v-model="profileState.studentNumber" maxlength="64" type="text" placeholder="请输入学号" />
              </label>
              <div class="profile-actions">
                <button class="secondary-btn" type="button" @click="cancelEdit">取消</button>
                <button type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存资料' }}</button>
              </div>
            </form>
          </section>

          <section v-show="activeSection === 'security'" class="profile-v2-section card">
            <div class="profile-v2-section-head">
              <h3>安全设置</h3>
            </div>
            <form class="profile-password-form" @submit.prevent="savePassword">
              <label>
                <span>旧密码</span>
                <input v-model="passwordState.oldPassword" type="password" autocomplete="current-password" placeholder="请输入旧密码" />
              </label>
              <label>
                <span>新密码</span>
                <input v-model="passwordState.newPassword" type="password" minlength="6" autocomplete="new-password" placeholder="请输入新密码（至少6位）" />
              </label>
              <label>
                <span>确认新密码</span>
                <input v-model="passwordState.confirmPassword" type="password" minlength="6" autocomplete="new-password" placeholder="请再次输入新密码" />
              </label>
              <div class="profile-actions">
                <button class="secondary-btn" type="button" @click="clearPasswordForm">清空</button>
                <button type="submit" :disabled="passwordSaving">{{ passwordSaving ? '提交中...' : '修改密码' }}</button>
              </div>
            </form>
          </section>

          <section v-show="activeSection === 'personalization'" class="profile-v2-section card">
            <div class="profile-v2-section-head">
              <h3>个性化</h3>
              <button class="secondary-btn" @click="startEdit('personalization')">编辑签名</button>
            </div>

            <div v-if="!editing || activeSection !== 'personalization'" class="profile-v2-signature-card">
              <span>个性签名</span>
              <p>{{ ojUser.signature || '还未设置签名' }}</p>
            </div>

            <form v-else class="profile-edit-form" @submit.prevent="saveProfile">
              <label>
                <span>个性签名</span>
                <textarea v-model="profileState.signature" maxlength="280" rows="5" placeholder="写一句你的竞赛宣言..." />
              </label>
              <div class="profile-edit-hint">{{ profileState.signature.length }}/280</div>
              <div class="profile-actions">
                <button class="secondary-btn" type="button" @click="cancelEdit">取消</button>
                <button type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存签名' }}</button>
              </div>
            </form>
          </section>

          <section v-show="activeSection === 'contest'" class="profile-v2-section card">
            <div class="profile-v2-section-head">
              <h3>竞赛数据</h3>
            </div>
            <div class="profile-v2-stats-grid">
              <div class="profile-v2-stat-card" v-for="item in contestHighlights" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
            <div class="profile-v2-note">
              后续可扩展真实参赛统计（场次、通过题数、最近提交）。当前先展示账号维度可用数据。
            </div>
          </section>

          <div class="success-tip" v-if="profileState.message || passwordState.message">
            {{ profileState.message || passwordState.message }}
          </div>
          <div class="error" v-if="profileState.error || passwordState.error || ojUser.error">
            {{ profileState.error || passwordState.error || ojUser.error }}
          </div>
        </main>
      </div>
    </div>
  </section>
</template>
