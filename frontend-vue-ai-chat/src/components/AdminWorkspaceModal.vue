<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container admin-workspace-modal" role="dialog" aria-label="Problem management workspace">
      <div class="modal-header">
        <h3>新增题目 / 题目管理</h3>
        <button class="modal-close-btn" @click="$emit('close')" aria-label="Close">&times;</button>
      </div>

      <div class="modal-body">
        <div class="admin-actions-bar">
          <button class="btn-create-contest" @click="showContestCreateModal = true">+ Create Contest</button>
        </div>

        <AdminProblemUpload />

        <ContestCreateModal
          v-if="showContestCreateModal"
          @close="showContestCreateModal = false"
          @created="onContestCreated"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AdminProblemUpload from './AdminProblemUpload.vue'
import ContestCreateModal from './ContestCreateModal.vue'
import { useOjStore } from '../stores/ojStore'

const { fetchContests } = useOjStore()
const showContestCreateModal = ref(false)

const onContestCreated = async () => {
  await fetchContests('all')
}
</script>

<style scoped>
.admin-workspace-modal {
  width: min(1200px, 96vw);
  max-height: 92vh;
}

.admin-workspace-modal .modal-body {
  overflow-y: auto;
  padding: 12px 16px 16px;
}

.admin-actions-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.btn-create-contest {
  padding: 8px 18px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: #191a1b;
  color: #f7f8f8;
  font-size: 0.9rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-create-contest:hover {
  background: rgba(255, 255, 255, 0.08);
}
</style>
