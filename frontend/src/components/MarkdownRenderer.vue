<script setup>
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import katex from 'katex'

const props = defineProps({
  content: { type: String, default: '' },
})

marked.setOptions({ breaks: true, gfm: true })

function renderContent(raw) {
  if (!raw) return ''

  // 1. 提取数学块，用占位符替换，防止 marked 破坏 LaTeX 语法
  const maths = []

  // $$ ... $$ 块级（先处理，避免被 $ ... $ 误匹配）
  let text = raw.replace(/\$\$([\s\S]+?)\$\$/g, (_, expr) => {
    maths.push({ display: true, expr: expr.trim() })
    return `\x00MATH${maths.length - 1}\x00`
  })

  // $ ... $ 行内（不跨行，排除空格仅包含的情况）
  text = text.replace(/\$([^$\n]{1,300}?)\$/g, (_, expr) => {
    if (!expr.trim()) return _
    maths.push({ display: false, expr: expr })
    return `\x00MATH${maths.length - 1}\x00`
  })

  // 2. marked 处理剩余 Markdown
  let html = marked.parse(text)

  // 3. 将占位符替换为 KaTeX 渲染结果
  html = html.replace(/\x00MATH(\d+)\x00/g, (_, i) => {
    const { display, expr } = maths[+i]
    try {
      return katex.renderToString(expr, { displayMode: display, throwOnError: false, strict: false })
    } catch {
      return `<code class="math-err">${expr}</code>`
    }
  })

  return DOMPurify.sanitize(html)
}

const html = computed(() => renderContent(props.content))
</script>

<template>
  <div class="md-body" v-html="html"></div>
</template>

<style>
/* 全局样式（非 scoped），让 v-html 内部生效 */
.md-body { color: var(--text-primary); line-height: 1.9; font-size: 15px; }
.md-body h1, .md-body h2, .md-body h3,
.md-body h4, .md-body h5, .md-body h6 {
  color: var(--text-primary); margin: 1.2em 0 0.5em; font-weight: 700;
}
.md-body p { margin: 0.6em 0; }
.md-body a { color: var(--accent); text-decoration: underline; }
.md-body code {
  background: var(--bg-input); padding: 0.15em 0.4em;
  border-radius: 4px; font-size: 0.875em; color: var(--code-color);
  font-family: 'Fira Code', 'Consolas', monospace;
}
.md-body pre {
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem; overflow-x: auto;
  margin: 0.8em 0;
}
.md-body pre code {
  background: none; padding: 0; color: var(--text-secondary);
  font-size: 0.875rem;
}
.md-body blockquote {
  border-left: 3px solid var(--accent); margin: 0.8em 0;
  padding: 0.3em 1em; color: var(--text-muted); background: var(--bg-secondary);
}
.md-body ul, .md-body ol { padding-left: 1.5em; margin: 0.5em 0; }
.md-body li { margin: 0.25em 0; }
.md-body table {
  border-collapse: collapse; width: 100%; margin: 0.8em 0;
}
.md-body th, .md-body td {
  border: 1px solid var(--border); padding: 0.5rem 0.75rem;
  font-size: 0.88rem;
}
.md-body th { background: var(--bg-secondary); color: var(--text-primary); }
.md-body hr { border: none; border-top: 1px solid var(--border); margin: 1em 0; }
/* KaTeX 数学公式适配主题 */
.md-body .katex { color: var(--text-primary); font-size: 1em; }
.md-body .katex-display { margin: 0.8em 0; overflow-x: auto; }
.math-err { color: #ef4444; }
.md-body img {
  max-width: 100% !important;
  width: auto !important;
  height: auto !important;
  display: block;
  border-radius: 6px;
}
</style>
