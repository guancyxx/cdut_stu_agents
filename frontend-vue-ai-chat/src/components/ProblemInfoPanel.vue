<script setup>
import { useOjPanelStore } from '../stores/useOjPanelStore'

const {
  problemDetailLoading,
  hasSelectedProblem,
  selectedProblem,
  selectedProblemDescriptionHtml,
  selectedProblemInputDesc,
  selectedProblemInputHtml,
  selectedProblemOutputDesc,
  selectedProblemOutputHtml,
  selectedProblemSamples,
  selectedProblemHint,
  selectedProblemHintHtml,
  selectedProblemSource
} = useOjPanelStore()
</script>

<template>
  <div class="prob-info-panel scrollbar-unified" v-if="hasSelectedProblem">
    <div class="prob-info-top">
      <div class="card-title">{{ selectedProblem.title }}</div>
      <div class="card-subtitle">Problem ID: {{ selectedProblem._id }}</div>
    </div>

    <div class="prob-info-body scrollbar-unified">
      <div class="problem-section-loading" v-if="problemDetailLoading">加载题目详情...</div>

      <div class="problem-section" v-if="selectedProblemDescriptionHtml">
        <h4 class="problem-section-title">Description</h4>
        <div class="problem-description" v-html="selectedProblemDescriptionHtml" />
      </div>

      <div class="problem-section" v-if="selectedProblemInputDesc">
        <h4 class="problem-section-title">Input</h4>
        <div class="problem-description" v-html="selectedProblemInputHtml" />
      </div>

      <div class="problem-section" v-if="selectedProblemOutputDesc">
        <h4 class="problem-section-title">Output</h4>
        <div class="problem-description" v-html="selectedProblemOutputHtml" />
      </div>

      <div class="problem-section" v-if="selectedProblemSamples.length">
        <div v-for="(sample, idx) in selectedProblemSamples" :key="idx" class="problem-sample-block">
          <div class="problem-sample-item">
            <h4 class="problem-section-title">Sample Input {{ selectedProblemSamples.length > 1 ? idx + 1 : '' }}</h4>
            <pre class="problem-sample-code">{{ sample.input }}</pre>
          </div>
          <div class="problem-sample-item">
            <h4 class="problem-section-title">Sample Output {{ selectedProblemSamples.length > 1 ? idx + 1 : '' }}</h4>
            <pre class="problem-sample-code">{{ sample.output }}</pre>
          </div>
        </div>
      </div>

      <div class="problem-section" v-if="selectedProblemHint">
        <h4 class="problem-section-title">Hint</h4>
        <div class="problem-description" v-html="selectedProblemHintHtml" />
      </div>

      <div class="problem-section problem-source" v-if="selectedProblemSource">
        <span class="problem-source-label">Source:</span> {{ selectedProblemSource }}
      </div>
    </div>

    <div class="prob-info-bottom">
      <div class="detail-grid compact-detail-grid">
        <div class="detail-row compact-detail-row"><span>难度</span><strong>{{ selectedProblem.difficulty || 'Unknown' }}</strong></div>
        <div class="detail-row compact-detail-row"><span>时间限制</span><strong>{{ selectedProblem.time_limit || '-' }}</strong></div>
        <div class="detail-row compact-detail-row"><span>内存限制</span><strong>{{ selectedProblem.memory_limit || '-' }}</strong></div>
        <div class="detail-row compact-detail-row"><span>提交数</span><strong>{{ selectedProblem.submission_number || 0 }}</strong></div>
        <div class="detail-row compact-detail-row"><span>通过数</span><strong>{{ selectedProblem.accepted_number || 0 }}</strong></div>
        <div class="detail-row compact-detail-row">
          <span>通过率</span>
          <strong>{{ selectedProblem.submission_number ? `${Math.round((selectedProblem.accepted_number / selectedProblem.submission_number) * 100)}%` : '0%' }}</strong>
        </div>
      </div>
    </div>
  </div>
  <div class="empty" v-else>请先在题库中选择一道题目</div>
</template>

<style scoped>
.prob-info-panel {
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 10px;
  padding: 12px;
  min-height: 0;
}

.prob-info-top {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
}

.prob-info-body {
  min-height: 0;
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-soft);
  padding: 10px;
}

.prob-info-bottom {
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px;
}
</style>
