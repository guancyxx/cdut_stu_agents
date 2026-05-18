<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container admin-workspace-modal" role="dialog" aria-label="Problem management workspace">
      <div class="modal-header minimal-header">
        <button class="modal-close-btn" @click="$emit('close')" aria-label="Close">&times;</button>
      </div>

      <div class="modal-body">
        <AdminProblemUpload />
      </div>
    </div>
  </div>
</template>

<script setup>
import AdminProblemUpload from './AdminProblemUpload.vue'
</script>

<style scoped>
.admin-workspace-modal {
  width: min(1200px, 96vw);
  max-height: 92vh;
}

.admin-workspace-modal .modal-body {
  overflow-y: auto;
  padding: 8px 16px 16px;
}

.minimal-header {
  min-height: 32px;
  justify-content: flex-end;
  padding-bottom: 0;
  border-bottom: none;
}
</style>
