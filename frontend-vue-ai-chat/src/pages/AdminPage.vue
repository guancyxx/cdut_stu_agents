<script setup>
import { ref } from 'vue'
import AdminProblemUpload from '../components/AdminProblemUpload.vue'
import ContestCreateModal from '../components/ContestCreateModal.vue'
import { useOjStore } from '../stores/ojStore'

const { fetchContests } = useOjStore()

const showContestCreateModal = ref(false)

const onContestCreated = async (result) => {
  await fetchContests('all')
  if (result?.contest_id) {
    // contest created — list refreshes
  }
}
</script>

<template>
  <section class="admin-screen">
    <div class="admin-actions-bar">
      <button class="btn-create-contest" @click="showContestCreateModal = true">+ Create Contest</button>
    </div>
    <AdminProblemUpload />
    <ContestCreateModal
      v-if="showContestCreateModal"
      @close="showContestCreateModal = false"
      @created="onContestCreated"
    />
  </section>
</template>
