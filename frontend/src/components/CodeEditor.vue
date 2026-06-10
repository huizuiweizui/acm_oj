<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as monaco from 'monaco-editor'

if (typeof window !== 'undefined' && !window.MonacoEnvironment) {
  window.MonacoEnvironment = {
    getWorkerUrl: () => {
      const blob = new Blob(['self.onmessage=function(){}'], { type: 'text/javascript' })
      return URL.createObjectURL(blob)
    },
  }
}

const LANG_MAP = { 'C': 'c', 'C++': 'cpp', 'Java': 'java', 'Python': 'python', 'Go': 'go' }

const props = defineProps({
  modelValue: { type: String, default: '' },
  language:   { type: String, default: 'C++' },
  theme:      { type: String, default: 'vs-dark' },
  fontSize:   { type: Number, default: 14 },
})
const emit = defineEmits(['update:modelValue'])

const editorEl = ref(null)
let editorInstance = null

onMounted(() => {
  editorInstance = monaco.editor.create(editorEl.value, {
    value: props.modelValue,
    language: LANG_MAP[props.language] ?? 'cpp',
    theme: props.theme,
    fontSize: props.fontSize,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
    renderWhitespace: 'selection',
    tabSize: 4,
    automaticLayout: true,
    padding: { top: 8, bottom: 8 },
  })

  editorInstance.onDidChangeModelContent(() => {
    emit('update:modelValue', editorInstance.getValue())
  })
})

watch(() => props.language, (lang) => {
  if (!editorInstance) return
  monaco.editor.setModelLanguage(editorInstance.getModel(), LANG_MAP[lang] ?? 'plaintext')
})

watch(() => props.modelValue, (val) => {
  if (editorInstance && editorInstance.getValue() !== val) {
    editorInstance.setValue(val)
  }
})

watch(() => props.theme, (t) => {
  if (editorInstance) monaco.editor.setTheme(t)
})

watch(() => props.fontSize, (s) => {
  if (editorInstance) editorInstance.updateOptions({ fontSize: s })
})

function format() {
  editorInstance?.getAction('editor.action.formatDocument')?.run()
}

function focus() {
  editorInstance?.focus()
}

onBeforeUnmount(() => {
  editorInstance?.dispose()
})

defineExpose({ format, focus })
</script>

<template>
  <div ref="editorEl" class="code-editor"></div>
</template>

<style scoped>
.code-editor {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
