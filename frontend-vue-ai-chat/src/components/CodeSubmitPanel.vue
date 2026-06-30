<script setup>
import CodeEditor from './CodeEditor.vue'
import { useOjPanelStore, ALL_LANGUAGES } from '../stores/useOjPanelStore'

const {
  submitLoading,
  langDropdownOpen,
  activeSubmitLanguage,
  codes,
  activeSubmitState,
  hasSelectedProblem,
  submitResult,
  getResultClass,
  getTestCaseClass,
  formatMemory,
  handleSubmitCode
} = useOjPanelStore()
</script>

<template>
  <div class="code-submit-panel" v-if="hasSelectedProblem">
    <div class="submit-layout">
      <div class="submit-editor-area">
        <div class="submit-form">
          <div class="lang-select-wrap">
            <div
              class="lang-select-trigger"
              :class="{ open: langDropdownOpen }"
              @click="langDropdownOpen = !langDropdownOpen"
              tabindex="0"
              role="combobox"
              :aria-expanded="langDropdownOpen"
            >
              <span class="lang-select-label">{{ activeSubmitLanguage }}</span>
              <span class="lang-select-arrow">▼</span>
            </div>
            <div v-if="langDropdownOpen" class="lang-select-dropdown" @mouseleave="langDropdownOpen = false">
              <div
                v-for="lang in ALL_LANGUAGES"
                :key="lang"
                class="lang-select-option"
                :class="{ selected: activeSubmitLanguage === lang }"
                @click="activeSubmitLanguage = lang; langDropdownOpen = false"
              >
                <span class="lang-select-option-icon" :class="{ cpp: lang === 'C++', c: lang === 'C', java: lang === 'Java', py: lang === 'Python3' }">
                  {{ lang === 'C++' ? '++' : lang[0] }}
                </span>
                {{ lang }}
              </div>
            </div>
          </div>

          <CodeEditor
            v-for="lang in ALL_LANGUAGES"
            :key="lang"
            v-show="activeSubmitLanguage === lang"
            v-model="codes[lang]"
            class="oj-code-editor"
            :language="lang"
            placeholder="Enter your source code here"
          />

          <div class="submit-action-row">
            <button :disabled="submitLoading" @click="handleSubmitCode">
              {{ submitLoading ? '提交中...' : '提交代码' }}
            </button>
          </div>
        </div>
      </div>

      <div class="submit-result-area scrollbar-unified">
        <div class="submit-result-empty" v-if="submitLoading">
          <div class="result-spinner"></div>
          <span>Judging...</span>
        </div>

        <div class="submit-result-panel" v-else-if="submitResult" :class="getResultClass(submitResult)">
          <div class="result-header">
            <span class="result-icon">{{ submitResult.icon || '❓' }}</span>
            <span class="result-label">{{ submitResult.display || submitResult.label }}</span>
            <span class="result-submission-id" v-if="submitResult.submissionId">#{{ submitResult.submissionId }}</span>
          </div>
          <div class="result-stats-row">
            <div class="result-stat" v-if="submitResult.score > 0">
              <span class="stat-label">Score</span>
              <span class="stat-value">{{ submitResult.score }}</span>
            </div>
            <div class="result-stat">
              <span class="stat-label">Time</span>
              <span class="stat-value">{{ submitResult.timeCost }}ms</span>
            </div>
            <div class="result-stat">
              <span class="stat-label">Memory</span>
              <span class="stat-value">{{ formatMemory(submitResult.memoryCost) }}</span>
            </div>
          </div>

          <div class="result-error-block" v-if="submitResult.errInfo">
            <div class="error-block-header">
              <span class="error-block-icon">⚠</span>
              <span>{{ submitResult.label === 'COMPILE_ERROR' ? 'Compile Error' : 'Error Details' }}</span>
            </div>
            <pre class="error-block-content">{{ submitResult.errInfo }}</pre>
          </div>

          <div class="result-test-cases" v-if="submitResult.testCases && submitResult.testCases.length > 0">
            <div class="test-cases-header">
              <span class="tc-summary-label">Test Cases</span>
              <span class="tc-pass-count">
                {{ submitResult.testCases.filter(tc => tc.status === 0 || tc.label === 'ACCEPTED').length }}/{{ submitResult.testCases.length }} passed
              </span>
            </div>
            <div class="tc-progress-bar">
              <div
                v-for="tc in submitResult.testCases"
                :key="'bar-' + tc.index"
                class="tc-progress-segment"
                :class="getTestCaseClass(tc)"
                :title="`#${tc.index} ${tc.display}`"
              ></div>
            </div>
          </div>
        </div>

        <div class="submit-result-empty" v-else>
          <span class="empty-icon">📋</span>
          <span>Submit code to see results</span>
        </div>
      </div>
    </div>
  </div>
  <div class="empty" v-else>请先选择题目后再提交代码</div>
</template>

<style scoped>
.code-submit-panel {
  height: 100%;
  padding: 12px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.code-submit-panel > .submit-layout {
  flex: 1;
  min-height: 0;
}
</style>
