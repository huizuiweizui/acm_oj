<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as monaco from 'monaco-editor'

// 用空 blob worker 跳过语言服务，基础编辑和语法高亮仍正常
if (typeof window !== 'undefined' && !window.MonacoEnvironment) {
  window.MonacoEnvironment = {
    getWorkerUrl: () => {
      const blob = new Blob(['self.onmessage=function(){}'], { type: 'text/javascript' })
      return URL.createObjectURL(blob)
    },
  }
}

const LANG_MAP = { 'C': 'c', 'C++': 'cpp', 'Java': 'java', 'Python': 'python' }

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'C++' },
})
const emit = defineEmits(['update:modelValue'])

const editorEl = ref(null)
let editorInstance = null

onMounted(() => {
  editorInstance = monaco.editor.create(editorEl.value, {
    value: props.modelValue,
    language: LANG_MAP[props.language] ?? 'cpp',
    theme: 'vs-dark',
    fontSize: 14,
    fontFamily: "'Fira Code', 'Consolas', 'Courier New', monospace",
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
    renderWhitespace: 'selection',
    tabSize: 4,
    automaticLayout: true,
  })

  editorInstance.onDidChangeModelContent(() => {
    emit('update:modelValue', editorInstance.getValue())
  })
})

watch(() => props.language, (lang) => {
  if (!editorInstance) return
  const model = editorInstance.getModel()
  monaco.editor.setModelLanguage(model, LANG_MAP[lang] ?? 'plaintext')
})

watch(() => props.modelValue, (val) => {
  if (editorInstance && editorInstance.getValue() !== val) {
    editorInstance.setValue(val)
  }
})

onBeforeUnmount(() => {
  editorInstance?.dispose()
})
</script>

<template>
  <div ref="editorEl" class="code-editor"></div>
</template>

<style scoped>
.code-editor {
  width: 100%;
  height: 100%;
  min-height: 400px;
  border-radius: 6px;
  overflow: hidden;
}
</style>
