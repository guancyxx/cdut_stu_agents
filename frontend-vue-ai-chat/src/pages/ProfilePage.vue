<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'
import { sanitizeTextInput } from '../utils/validators'

const router = useRouter()
const { ojUser, logout, updateUserProfile } = useOjStore()
const { switchToUser } = useChatStore()

const editing = ref(false)
const saving = ref(false)
const profileState = reactive({
  email: '',
  studentNumber: '',
  signature: '',
  message: '',
  error: ''
})

const syncDraftFromUser = () => {
  profileState.email = ojUser.value.email || ''
  profileState.studentNumber = ojUser.value.studentNumber || ''
  profileState.signature = ojUser.value.signature || ''
}

const startEdit = () => {
  profileState.message = ''
  profileState.error = ''
  syncDraftFromUser()
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

const handleLogout = async () => {
  const succeeded = await logout()
  if (!succeeded) return
  switchToUser('')
  router.replace('/auth')
}
</script>

<template>
  <section class="profile-screen">
    <div class="profile-page card">
      <div class="profile-header">
        <div class="profile-avatar" v-if="ojUser.avatar">
          <img :src="ojUser.avatar" alt="avatar" />
        </div>
        <div class="profile-avatar profile-avatar-fallback" v-else>{{ (ojUser.profileName || 'U').slice(0, 1).toUpperCase() }}</div>

        <div class="profile-title-group">
          <h2>{{ ojUser.profileName || ojUser.username || '未命名用户' }}</h2>
          <p>{{ ojUser.email || 'No email available' }}</p>
        </div>
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
          <strong>{{ ojUser.adminType >= 2 ? 'Super Admin' : ojUser.adminType >= 1 ? 'Admin' : 'Regular User' }}</strong>
        </div>
        <div class="profile-item profile-item-full">
          <span>个性签名</span>
          <strong>{{ ojUser.signature || '-' }}</strong>
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
        <label>
          <span>个性签名</span>
          <textarea v-model="profileState.signature" maxlength="280" rows="4" placeholder="写一句你的竞赛宣言..." />
        </label>
        <div class="profile-edit-hint">{{ profileState.signature.length }}/280</div>
        <div class="profile-actions">
          <button class="secondary-btn" type="button" @click="cancelEdit">取消</button>
          <button type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存资料' }}</button>
        </div>
      </form>

      <div class="profile-actions" v-if="!editing">
        <button class="secondary-btn" @click="router.push('/')">返回主页</button>
        <button class="secondary-btn" @click="startEdit">编辑资料</button>
        <button class="danger-btn" @click="handleLogout">退出登录</button>
      </div>

      <div class="success-tip" v-if="profileState.message">{{ profileState.message }}</div>
      <div class="error" v-if="profileState.error || ojUser.error">{{ profileState.error || ojUser.error }}</div>
    </div>
  </section>
</template>
