<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSubmission } from '@/api/submissions'
import StatusBadge from '@/components/StatusBadge.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const route = useRoute()
const router = useRouter()

const sub = ref(null)
const loading = ref(true)
const error = ref('')
const copied = ref(false)
let timer = null

const pending = computed(() => ['Pending', 'Judging'].includes(sub.value?.status))
const codeLines = computed(() => (sub.value?.code || '').split('\n'))

async function load() {
  clearTimeout(timer)
  try {
    const { data } = await getSubmission(route.params.id)
    sub.value = data
    error.value = ''
    // 评测未完成时继续轮询
    if (pending.value) timer = setTimeout(load, 2000)
  } catch (e) {
    error.value = e.response?.status === 404 ? '提交记录不存在' : '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(sub.value.code)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch { /* 剪贴板不可用时静默失败 */ }
}

function fmtTime(iso) {
  return iso ? new Date(iso).toLocaleString('zh-CN', { hour12: false }) : ''
}

const TC_CLASS = { AC: 'tc-ac', WA: 'tc-wa', RE: 'tc-wa', TLE: 'tc-tle', MLE: 'tc-tle' }

watch(() => route.params.id, () => { loading.value = true; load() })
onMounted(load)
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="sd-page">
    <div v-if="loading" class="tip">加载中…</div>
    <div v-else-if="error" class="tip tip-err">
      {{ error }}
      <button class="btn-ghost" @click="router.back()">← 返回</button>
    </div>

    <template v-else-if="sub">
      <div class="sd-head">
        <button class="btn-ghost" @click="router.back()">← 返回</button>
        <h1 class="sd-title">提交 #{{ sub.id }}</h1>
        <StatusBadge :status="sub.status" />
      </div>

      <div class="meta-card">
        <div class="meta-item">
          <span class="meta-label">题目</span>
          <RouterLink :to="`/problems/${sub.problem_id}`" class="meta-link">#{{ sub.problem_id }} {{ sub.problem_title }}</RouterLink>
        </div>
        <div class="meta-item">
          <span class="meta-label">用户</span>
          <RouterLink :to="`/users/${sub.user_id}`" class="meta-link">{{ sub.username }}</RouterLink>
        </div>
        <div class="meta-item"><span class="meta-label">语言</span><span class="mono">{{ sub.language }}</span></div>
        <div class="meta-item">
          <span class="meta-label">耗时</span>
          <span class="mono">{{ sub.time_used != null ? sub.time_used + ' ms' : '—' }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">内存</span>
          <span class="mono">{{ sub.memory_used != null ? (sub.memory_used / 1024).toFixed(1) + ' MB' : '—' }}</span>
        </div>
        <div class="meta-item"><span class="meta-label">提交时间</span><span>{{ fmtTime(sub.submitted_at) }}</span></div>
      </div>

      <div v-if="pending" class="section judging"><span class="spinner"></span> 评测中，结果将自动刷新…</div>

      <!-- 测试点 -->
      <div v-if="sub.test_results?.length" class="section">
        <h2 class="sec-title">测试点（{{ sub.test_results.filter(t => t.status === 'AC').length }} / {{ sub.test_results.length }}）</h2>
        <div class="tc-grid">
          <div v-for="tc in sub.test_results" :key="tc.idx" :class="['tc-cell', TC_CLASS[tc.status] || 'tc-muted']">
            <span class="tc-idx">#{{ tc.idx }}</span>
            <span class="tc-status">{{ tc.status }}</span>
            <span class="tc-time">{{ tc.time_ms }}ms</span>
          </div>
        </div>
      </div>

      <template v-if="sub.can_view_code">
        <div v-if="sub.error_info" class="section">
          <h2 class="sec-title">{{ sub.status === 'CE' ? '编译信息' : '错误信息' }}</h2>
          <pre class="err-block">{{ sub.error_info }}</pre>
        </div>

        <div class="section">
          <div class="sec-head">
            <h2 class="sec-title">源代码</h2>
            <button class="btn-ghost btn-sm" @click="copyCode">{{ copied ? '已复制 ✓' : '复制' }}</button>
          </div>
          <div class="code-block">
            <pre><code><span v-for="(line, i) in codeLines" :key="i" class="code-line"><span class="ln">{{ i + 1 }}</span>{{ line }}
</span></code></pre>
          </div>
        </div>

        <div v-if="sub.ai_feedback" class="section ai-block">
          <h2 class="sec-title">🤖 AI 反馈</h2>
          <MarkdownRenderer :content="sub.ai_feedback" />
        </div>
      </template>
      <div v-else class="section locked">
        🔒 源代码仅提交者本人、所在团队教师和管理员可见
      </div>
    </template>
  </div>
</template>

<style scoped>
.sd-page { max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 1rem; }
.tip { text-align: center; padding: 4rem 1rem; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 1rem; }
.tip-err { color: var(--status-wa-text); }

.sd-head { display: flex; align-items: center; gap: 0.9rem; }
.sd-title { font-size: 1.35rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.btn-ghost {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.35rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem;
}
.btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm { padding: 0.2rem 0.6rem; font-size: 0.78rem; }

.meta-card {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.9rem 1.5rem;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem;
}
.meta-item { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.9rem; color: var(--text-primary); min-width: 0; }
.meta-label { font-size: 0.75rem; color: var(--text-muted); }
.meta-link { color: var(--text-primary); text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta-link:hover { color: var(--accent-text); }
.mono { font-family: var(--font-mono); }

.section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; }
.sec-head { display: flex; align-items: center; justify-content: space-between; }
.sec-title { font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin: 0 0 0.75rem; }
.sec-head .sec-title { margin: 0; }
.sec-head + .code-block { margin-top: 0.75rem; }

.judging { display: flex; align-items: center; gap: 0.5rem; color: var(--accent); font-size: 0.9rem; }
.spinner {
  width: 14px; height: 14px; border: 2px solid var(--accent); border-top-color: transparent;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.tc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 0.5rem; }
.tc-cell {
  display: flex; flex-direction: column; align-items: center; gap: 0.1rem;
  padding: 0.5rem 0.25rem; border-radius: 6px; font-family: var(--font-mono);
}
.tc-idx { font-size: 0.7rem; opacity: 0.75; }
.tc-status { font-size: 0.95rem; font-weight: 700; }
.tc-time { font-size: 0.7rem; opacity: 0.8; }
.tc-ac  { background: var(--status-ac-bg);  color: var(--status-ac-text); }
.tc-wa  { background: var(--status-wa-bg);  color: var(--status-wa-text); }
.tc-tle { background: var(--status-tle-bg); color: var(--status-tle-text); }
.tc-muted { background: var(--status-nt-bg); color: var(--status-nt-text); }

.err-block {
  margin: 0; background: var(--status-wa-bg); color: var(--status-wa-text);
  border-radius: 6px; padding: 0.75rem; font-size: 0.8rem; font-family: var(--font-mono);
  white-space: pre-wrap; word-break: break-all; max-height: 280px; overflow: auto;
}

.code-block { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; overflow: auto; max-height: 640px; }
.code-block pre { margin: 0; padding: 0.75rem 0; font-family: var(--font-mono); font-size: 13px; line-height: 1.6; color: var(--text-primary); }
.code-line { display: block; padding-right: 1rem; white-space: pre; }
.ln {
  display: inline-block; width: 3rem; padding-right: 1rem; text-align: right;
  color: var(--text-muted); user-select: none;
}

.ai-block { border-color: rgba(59,130,246,0.25); }
.locked { color: var(--text-muted); font-size: 0.875rem; text-align: center; }
</style>
