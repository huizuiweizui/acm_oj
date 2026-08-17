<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import katex from 'katex'

const props = defineProps({
  content: { type: String, default: '' },
})

marked.setOptions({ breaks: true, gfm: true })

// marked 自 v5 起不再内置净化，输出会原样带上正文里的 <script>/onerror。
// 这里的内容有用户产出的部分（讨论帖、回复、AI 回答），直接 v-html 等于把
// JWT（存在 localStorage）交给任何一个发帖的人，所以必须过一遍 DOMPurify。
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

function renderContent(raw) {
  if (!raw) return ''

  // 1. 提取数学块，用占位符替换，防止 marked 破坏 LaTeX 语法。
  //    占位符必须是纯 ASCII 文本：它要原样穿过下面的 DOMPurify。
  //    加随机后缀，避免正文里恰好写了同样的字面量而被误替换。
  const maths = []
  const token = `MATHTOKEN${Math.random().toString(36).slice(2, 10)}`

  // $$ ... $$ 块级（先处理，避免被 $ ... $ 误匹配）
  let text = raw.replace(/\$\$([\s\S]+?)\$\$/g, (_, expr) => {
    maths.push({ display: true, expr: expr.trim() })
    return `${token}${maths.length - 1}END`
  })

  // $ ... $ 行内（不跨行，排除空格仅包含的情况）
  text = text.replace(/\$([^$\n]{1,300}?)\$/g, (_, expr) => {
    if (!expr.trim()) return _
    maths.push({ display: false, expr: expr })
    return `${token}${maths.length - 1}END`
  })

  // 2. marked 处理剩余 Markdown
  let html = marked.parse(text)

  // 3. 净化。必须在插入 KaTeX 之前做：KaTeX 的输出（大量 span + style + MathML）
  //    是可信的，反倒容易被净化规则误伤。
  //    额外禁掉表单元素：DOMPurify 默认放行 <form>，一个伪造的登录框贴在帖子里
  //    就能钓走密码。Markdown 正文也从来不需要它们。
  html = DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['form', 'input', 'button', 'select', 'option', 'textarea'],
  })

  // 4. 将占位符替换为 KaTeX 渲染结果。
  //    KaTeX 默认 trust:false，会禁掉 \href/\url/\includegraphics，输出可安全内联；
  //    但异常分支里的 expr 仍是原始用户输入，必须转义后再拼进 HTML。
  html = html.replace(new RegExp(`${token}(\\d+)END`, 'g'), (_, i) => {
    const { display, expr } = maths[+i]
    try {
      return katex.renderToString(expr, { displayMode: display, throwOnError: false, strict: false })
    } catch {
      return `<code class="math-err">${escapeHtml(expr)}</code>`
    }
  })

  return html
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
