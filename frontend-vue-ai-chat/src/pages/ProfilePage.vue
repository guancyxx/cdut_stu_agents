<script setup>
import { useRouter } from 'vue-router'
import { useOjStore } from '../stores/ojStore'
import { useChatStore } from '../stores/chatStore'

const router = useRouter()
const { ojUser, logout } = useOjStore()
const { switchToUser } = useChatStore()

const handleLogout = async () => {
  const succeeded = await logout()
  if (!succeeded) return
  switchToUser('')
  router.replace('/')
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

      <div class="profile-grid">
        <div class="profile-item">
          <span>用户名</span>
          <strong>{{ ojUser.username || '-' }}</strong>
        </div>
        <div class="profile-item">
          <span>学号</span>
          <strong>{{ ojUser.studentNumber || '-' }}</strong>
        </div>
        <div class="profile-item profile-item-full">
          <span>个性签名</span>
          <strong>{{ ojUser.signature || '-' }}</strong>
        </div>
      </div>

      <div class="profile-actions">
        <button class="secondary-btn" @click="router.push('/')">返回主页</button>
        <button class="danger-btn" @click="handleLogout">退出登录</button>
      </div>

      <div class="error" v-if="ojUser.error">{{ ojUser.error }}</div>
    </div>
  </section>
</template>
