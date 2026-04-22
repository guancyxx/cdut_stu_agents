<script setup>
import { computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'
import { cpp } from '@codemirror/lang-cpp'
import { java } from '@codemirror/lang-java'
import { python } from '@codemirror/lang-python'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'C++'
  },
  placeholder: {
    type: String,
    default: 'Enter your source code here'
  }
})

const emit = defineEmits(['update:modelValue'])

const basicSetup = {
  lineNumbers: true,
  foldGutter: true,
  highlightActiveLine: true,
  highlightActiveLineGutter: true,
  autocompletion: true
}

const codeExtensions = computed(() => {
  if (props.language === 'C' || props.language === 'C++') {
    return [cpp()]
  }

  if (props.language === 'Java') {
    return [java()]
  }

  if (props.language === 'Python3') {
    return [python()]
  }

  return []
})

const editorExtensions = computed(() => [
  oneDark,
  ...codeExtensions.value
])

const handleCodeChange = (value) => {
  emit('update:modelValue', value)
}
</script>

<template>
  <Codemirror
    :model-value="modelValue"
    :placeholder="placeholder"
    :extensions="editorExtensions"
    :basic-setup="basicSetup"
    :indent-with-tab="true"
    :tab-size="2"
    :autofocus="false"
    :style="{ height: '100%' }"
    @update:model-value="handleCodeChange"
  />
</template>
