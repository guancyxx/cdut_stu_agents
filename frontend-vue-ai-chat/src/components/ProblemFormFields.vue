<script setup>
import { ref } from 'vue'

const props = defineProps({
  form: {
    type: Object,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  },
  availableTags: {
    type: Array,
    default: () => []
  },
  showExample: {
    type: Boolean,
    default: false
  }
})

const activeTemplateTab = ref('C')

const templatePlaceholder = (lang) => {
  const placeholders = {
    C: 'void solve(void) {\n    // TODO: read input with scanf, compute, output with printf\n}',
    'C++': 'void solve() {\n    // TODO: read input with cin, compute, output with cout\n}',
    Java: 'public static void solve(Scanner sc) {\n    // TODO: read input with sc.nextInt(), output with System.out.println\n}',
    Python3: 'def solve() -> None:\n    # TODO: read input with input(), output with print()\n'
  }
  return placeholders[lang] || ''
}

const selectedExample = ref('A+B Problem')
const exampleProblems = [
  {
    title: 'A+B Problem',
    desc: '最简单的入门题，输入两个整数输出和',
    fields: {
      title: 'A+B Problem',
      description: '<p>输入两个整数 a 和 b，输出它们的和。0 ≤ a, b ≤ 1000</p>',
      input_description: '<p>一行，两个整数，空格分隔。</p>',
      output_description: '<p>一个整数，a + b 的和。</p>',
      samples: 'input: "1 2" → output: "3"',
      hint: '（留空）',
      难度: 'Low',
      来源: '课本入门',
      标签: '数学, 入门',
      时间限制: '1000 ms',
      内存限制: '256 MB'
    }
  }
]

const ensureArray = (key) => {
  if (!Array.isArray(props.form[key])) props.form[key] = []
}

const addSample = () => {
  ensureArray('samples')
  props.form.samples.push({ input: '', output: '' })
}

const removeSample = (index) => {
  ensureArray('samples')
  if (props.form.samples.length > 1) props.form.samples.splice(index, 1)
}

const addTestCase = () => {
  ensureArray('test_cases')
  props.form.test_cases.push({ input: '', output: '' })
}

const removeTestCase = (index) => {
  ensureArray('test_cases')
  if (props.form.test_cases.length > 1) props.form.test_cases.splice(index, 1)
}
</script>

<template>
  <div class="problem-form-fields">
    <details v-if="showExample" class="example-panel">
      <summary class="example-title">📖 录入示例 (点击展开参考)</summary>
      <div class="example-content">
        <p class="example-intro">以下是一个完整题目的填写示例，参考各字段的填写方式：</p>
        <div class="example-tabs">
          <button
            v-for="ex in exampleProblems"
            :key="ex.title"
            :class="{ active: selectedExample === ex.title }"
            @click="selectedExample = ex.title"
            class="ex-tab-btn"
            type="button"
          >{{ ex.title }}</button>
        </div>
        <div v-for="ex in exampleProblems" :key="'ex-'+ex.title" v-show="selectedExample === ex.title" class="example-body">
          <p><strong>说明：</strong>{{ ex.desc }}</p>
          <table class="example-table">
            <tr v-for="(val, key) in ex.fields" :key="key">
              <td class="ex-field">{{ key }}</td>
              <td class="ex-value"><code>{{ val }}</code></td>
            </tr>
          </table>
        </div>
      </div>
    </details>

    <div class="form-row">
      <label>标题 <span class="required">*</span></label>
      <input v-model="form.title" type="text" maxlength="128" :disabled="disabled" placeholder="题目标题" />
    </div>

    <div class="form-row inline">
      <div class="form-field">
        <label>难度</label>
        <select v-model="form.difficulty" :disabled="disabled">
          <option value="Low">Low（简单）</option>
          <option value="Mid">Mid（中等）</option>
          <option value="High">High（困难）</option>
        </select>
      </div>
      <div class="form-field">
        <label>来源</label>
        <input v-model="form.source" type="text" :disabled="disabled" placeholder="如：蓝桥杯" />
      </div>
    </div>

    <div class="form-row">
      <label>题目描述</label>
      <textarea v-model="form.description" rows="5" :disabled="disabled" placeholder="题目描述（支持HTML）"></textarea>
    </div>

    <div class="form-row">
      <label>输入描述</label>
      <textarea v-model="form.input_description" rows="3" :disabled="disabled" placeholder="输入格式说明"></textarea>
    </div>

    <div class="form-row">
      <label>输出描述</label>
      <textarea v-model="form.output_description" rows="3" :disabled="disabled" placeholder="输出格式说明"></textarea>
    </div>

    <div class="form-section">
      <label>样例</label>
      <div v-for="(sample, i) in form.samples" :key="`s${i}`" class="sample-row">
        <div class="sample-field">
          <span class="sample-label">输入{{ i + 1 }}</span>
          <textarea v-model="sample.input" rows="2" :disabled="disabled" placeholder="样例输入"></textarea>
        </div>
        <div class="sample-field">
          <span class="sample-label">输出{{ i + 1 }}</span>
          <textarea v-model="sample.output" rows="2" :disabled="disabled" placeholder="样例输出"></textarea>
        </div>
        <button v-if="form.samples.length > 1" class="btn-remove" type="button" @click="removeSample(i)" :disabled="disabled">✕</button>
      </div>
      <button class="btn-add" type="button" @click="addSample" :disabled="disabled">+ 添加样例</button>
    </div>

    <div class="form-row">
      <label>提示</label>
      <textarea v-model="form.hint" rows="2" :disabled="disabled" placeholder="解题提示（可选）"></textarea>
    </div>

    <div class="form-row">
      <label>标签</label>
      <input v-model="form.tags" type="text" :disabled="disabled" placeholder="逗号分隔，如：数学,动态规划" />
      <div v-if="availableTags.length" class="tag-hints">可用标签：{{ availableTags.join('、') }}</div>
    </div>

    <div class="form-section">
      <label>模板代码 (Starter Code)</label>
      <div class="template-tabs">
        <button
          v-for="lang in ['C', 'C++', 'Java', 'Python3']"
          :key="lang"
          :class="{ active: activeTemplateTab === lang }"
          @click="activeTemplateTab = lang"
          class="tab-btn"
          type="button"
          :disabled="disabled"
        >{{ lang }}</button>
      </div>
      <textarea
        v-model="form.template[activeTemplateTab]"
        :placeholder="templatePlaceholder(activeTemplateTab)"
        rows="8"
        class="template-code"
        :disabled="disabled"
      ></textarea>
    </div>

    <div class="form-section">
      <label>测试数据</label>
      <div v-for="(tc, i) in form.test_cases" :key="`tc${i}`" class="sample-row">
        <div class="sample-field">
          <span class="sample-label">输入{{ i + 1 }}</span>
          <textarea v-model="tc.input" rows="2" :disabled="disabled" placeholder="测试输入"></textarea>
        </div>
        <div class="sample-field">
          <span class="sample-label">输出{{ i + 1 }}</span>
          <textarea v-model="tc.output" rows="2" :disabled="disabled" placeholder="测试输出"></textarea>
        </div>
        <button v-if="form.test_cases.length > 1" class="btn-remove" type="button" @click="removeTestCase(i)" :disabled="disabled">✕</button>
      </div>
      <button class="btn-add" type="button" @click="addTestCase" :disabled="disabled">+ 添加测试数据</button>
    </div>

    <div class="form-row inline">
      <div class="form-field">
        <label>时间限制 (ms)</label>
        <input v-model.number="form.time_limit" type="number" min="100" max="60000" :disabled="disabled" />
      </div>
      <div class="form-field">
        <label>内存限制 (MB)</label>
        <input v-model.number="form.memory_limit" type="number" min="16" max="1024" :disabled="disabled" />
      </div>
    </div>

    <div class="form-section">
      <label>特殊判题 (SPJ)</label>
      <label class="checkbox-label" style="margin-bottom: 8px">
        <input v-model="form.spj" type="checkbox" :disabled="disabled" />
        启用特殊判题
      </label>
      <template v-if="form.spj">
        <div class="form-row">
          <label>SPJ 语言</label>
          <select v-model="form.spj_language" :disabled="disabled">
            <option value="">— 选择语言 —</option>
            <option value="C">C</option>
            <option value="C++">C++</option>
            <option value="Java">Java</option>
            <option value="Python3">Python3</option>
          </select>
        </div>
        <div class="form-row">
          <label>SPJ 代码</label>
          <textarea v-model="form.spj_code" rows="6" :disabled="disabled" placeholder="自定义判题逻辑代码"></textarea>
        </div>
      </template>
    </div>

    <div class="form-row">
      <label class="checkbox-label">
        <input v-model="form.visible" type="checkbox" :disabled="disabled" />
        公开可见
      </label>
    </div>
  </div>
</template>

<style scoped>
.form-row { margin-bottom: 14px; }
.form-row label { display: block; font-size: 13px; color: var(--text-secondary, #999); margin-bottom: 4px; }
.form-row.inline { display: flex; gap: 16px; }
.form-row.inline .form-field { flex: 1; }
.form-row input[type="text"],
.form-row input[type="number"],
.form-row textarea,
.form-row select {
  width: 100%; padding: 8px 10px; background: var(--input-bg, #1a1a2e);
  border: 1px solid var(--border-color, #333); border-radius: 6px;
  color: var(--text-primary, #e0e0e0); font-size: 13px; box-sizing: border-box;
}
.form-row textarea { resize: vertical; font-family: 'Consolas', 'Monaco', monospace; }
.required { color: #ef5350; }
.form-section { margin-bottom: 14px; padding: 10px; background: var(--card-bg, #1e1e30); border-radius: 8px; border: 1px solid var(--border-color, #333); }
.form-section > label { display: block; font-size: 13px; color: var(--text-secondary, #999); margin-bottom: 8px; }
.sample-row { display: flex; gap: 8px; align-items: flex-start; margin-bottom: 8px; }
.sample-field { flex: 1; }
.sample-label { display: block; font-size: 11px; color: var(--text-muted, #666); margin-bottom: 2px; }
.sample-field textarea { width: 100%; padding: 6px 8px; background: var(--input-bg, #12121f); border: 1px solid var(--border-color, #333); border-radius: 4px; color: var(--text-primary, #e0e0e0); font-size: 12px; font-family: 'Consolas','Monaco',monospace; resize: vertical; box-sizing: border-box; }
.btn-add { background: none; border: 1px dashed var(--border-color, #444); color: var(--accent, #4fc3f7); padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-remove { background: none; border: none; color: #ef5350; cursor: pointer; font-size: 14px; padding: 4px; margin-top: 16px; }
.checkbox-label { display: flex !important; align-items: center; gap: 8px; cursor: pointer; }
.checkbox-label input[type="checkbox"] { width: 16px; height: 16px; }
.tag-hints { font-size: 11px; color: var(--text-muted, #666); margin-top: 4px; }
.template-tabs { display: flex; gap: 4px; margin-bottom: 6px; }
.tab-btn { padding: 4px 14px; font-size: 12px; background: var(--input-bg, #1a1a2e); border: 1px solid var(--border-color, #333); border-radius: 4px 4px 0 0; color: var(--text-secondary, #999); cursor: pointer; transition: all 0.2s; }
.tab-btn.active { background: var(--accent, #4fc3f7); color: #000; border-color: var(--accent, #4fc3f7); }
.template-code { width: 100%; padding: 10px; background: var(--input-bg, #12121f); border: 1px solid var(--border-color, #333); border-radius: 0 4px 4px 4px; color: var(--text-primary, #e0e0e0); font-family: 'Consolas','Monaco',monospace; font-size: 13px; resize: vertical; box-sizing: border-box; }
.example-panel { margin-bottom: 16px; padding: 12px; background: var(--card-bg, #1e1e30); border: 1px solid var(--border-color, #333); border-radius: 8px; }
.example-title { font-size: 14px; font-weight: 600; color: var(--accent, #4fc3f7); cursor: pointer; padding: 4px 0; }
.example-content { margin-top: 10px; }
.example-intro { font-size: 12px; color: var(--text-secondary, #999); margin-bottom: 8px; }
.example-tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.ex-tab-btn { padding: 4px 12px; font-size: 12px; background: var(--input-bg, #1a1a2e); border: 1px solid var(--border-color, #333); border-radius: 4px; color: var(--text-secondary, #999); cursor: pointer; }
.ex-tab-btn.active { background: var(--accent, #4fc3f7); color: #000; border-color: var(--accent, #4fc3f7); }
.example-table { width: 100%; border-collapse: collapse; }
.example-table td { padding: 4px 8px; border: 1px solid var(--border-color, #333); vertical-align: top; }
.ex-field { width: 140px; font-size: 11px; color: var(--text-muted, #666); white-space: nowrap; }
.ex-value code { font-family: 'Consolas','Monaco',monospace; font-size: 11px; white-space: pre-wrap; word-break: break-all; }
</style>
