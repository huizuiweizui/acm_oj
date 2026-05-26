<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: { type: String, default: '' },
})

// 配置 marked：换行保留、安全转义
marked.setOptions({ breaks: true, gfm: true })

const html = computed(() => marked.parse(props.content || ''))
</script>

<template>
  <div class="md-body" v-html="html"></div>
</template>

<style>
/* 全局样式（非 scoped），让 v-html 内部生效 */
.md-body { color: #c8c8d8; line-height: 1.8; font-size: 0.95rem; }
.md-body h1, .md-body h2, .md-body h3,
.md-body h4, .md-body h5, .md-body h6 {
  color: #e0e0f0; margin: 1.2em 0 0.5em; font-weight: 700;
}
.md-body p { margin: 0.6em 0; }
.md-body a { color: #a78bfa; text-decoration: underline; }
.md-body code {
  background: #1e1e38; padding: 0.15em 0.4em;
  border-radius: 4px; font-size: 0.875em; color: #f8b4d9;
  font-family: 'Fira Code', 'Consolas', monospace;
}
.md-body pre {
  background: #12121e; border: 1px solid #2d2d4e;
  border-radius: 8px; padding: 1rem; overflow-x: auto;
  margin: 0.8em 0;
}
.md-body pre code {
  background: none; padding: 0; color: #c8c8d8;
  font-size: 0.875rem;
}
.md-body blockquote {
  border-left: 3px solid #7c6af7; margin: 0.8em 0;
  padding: 0.3em 1em; color: #888; background: #1a1a30;
}
.md-body ul, .md-body ol { padding-left: 1.5em; margin: 0.5em 0; }
.md-body li { margin: 0.25em 0; }
.md-body table {
  border-collapse: collapse; width: 100%; margin: 0.8em 0;
}
.md-body th, .md-body td {
  border: 1px solid #2d2d4e; padding: 0.5rem 0.75rem;
  font-size: 0.88rem;
}
.md-body th { background: #1a1a30; color: #e0e0f0; }
.md-body hr { border: none; border-top: 1px solid #2d2d4e; margin: 1em 0; }
</style>
