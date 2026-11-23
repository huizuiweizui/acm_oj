<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProblem, submitCode, runCode } from '@/api/problems'
import { getSubmissions } from '@/api/submissions'
import { getDiscussions } from '@/api/discussions'
import { useUserStore } from '@/stores/user'
import { useSubmissionStore } from '@/stores/submission'
import DifficultyBadge from '@/components/DifficultyBadge.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import CodeEditor from '@/components/CodeEditor.vue'
import JudgeResult from '@/components/JudgeResult.vue'

const route  = useRoute()
const router = useRouter()
const userStore = useUserStore()
const submissionStore = useSubmissionStore()

// ── Problem data ──────────────────────────────────────────────────
const problem = ref(null)
const loading = ref(true)
const prevId  = ref(null)
const nextId  = ref(null)
const contestId = route.query.contest_id || null

const passRate = computed(() => {
  if (!problem.value || problem.value.submit_count === 0) return '0.0%'
  return (problem.value.ac_count / problem.value.submit_count * 100).toFixed(1) + '%'
})

// ── Language / Code ───────────────────────────────────────────────
const DEFAULT_CODE = {
  'C':      '#include <stdio.h>\n\nint main() {\n    \n    return 0;\n}\n',
  'C++':    '#include <iostream>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    \n    return 0;\n}\n',
  'Java':   'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}\n',
  'Python': '# Python solution\nimport sys\ninput = sys.stdin.readline\n\n',
}
const supportedLanguages = computed(() => problem.value?.supported_languages ?? Object.keys(DEFAULT_CODE))
const language = ref('C++')
const code     = ref(DEFAULT_CODE['C++'])

function onLangChange() {
  const isDefault = Object.values(DEFAULT_CODE).includes(code.value) || !code.value.trim()
  if (isDefault) code.value = DEFAULT_CODE[language.value] || ''
}

// ── Editor settings ───────────────────────────────────────────────
const editorRef   = ref(null)
const editorTheme = ref(localStorage.getItem('editor-theme') || 'vs-dark')
const fontSize    = ref(Number(localStorage.getItem('editor-font-size') || 14))
const isFullscreen = ref(false)

watch(fontSize,    v  => localStorage.setItem('editor-font-size', v))
watch(editorTheme, t  => localStorage.setItem('editor-theme', t))

function toggleEditorTheme() {
  editorTheme.value = editorTheme.value === 'vs-dark' ? 'vs' : 'vs-dark'
}
function resetCode() {
  if (confirm('重置为默认模板？')) code.value = DEFAULT_CODE[language.value] || ''
}
function formatCode() { editorRef.value?.format() }
async function copyCode() {
  await navigator.clipboard.writeText(code.value)
  copyCodeTip.value = true
  setTimeout(() => { copyCodeTip.value = false }, 1200)
}
const copyCodeTip = ref(false)
function toggleFullscreen() { isFullscreen.value = !isFullscreen.value }

// ── Submit ────────────────────────────────────────────────────────
const submitting  = ref(false)
const submitError = ref('')

async function handleSubmit() {
  if (!userStore.isLoggedIn) {
    router.push(`/login?next=/problems/${route.params.id}`)
    return
  }
  if (!code.value.trim()) { submitError.value = '代码不能为空'; return }
  submitting.value  = true
  submitError.value = ''
  try {
    const { data } = await submitCode(route.params.id, language.value, code.value, contestId)
    submissionStore.startPolling(data.submission_id)
    showRunPanel.value = false
  } catch (e) {
    submitError.value = e.response?.data?.detail || '提交失败，请重试'
  } finally {
    submitting.value = false
  }
}

// ── Custom run ────────────────────────────────────────────────────
const showRunPanel  = ref(false)
const customInput   = ref('')
const running       = ref(false)
const runResult     = ref(null)

function fillInput(text) {
  customInput.value  = text
  showRunPanel.value = true
  runResult.value    = null
}

async function doRun() {
  if (!userStore.isLoggedIn) {
    router.push(`/login?next=/problems/${route.params.id}`)
    return
  }
  if (!code.value.trim()) return
  running.value   = true
  runResult.value = null
  try {
    const { data } = await runCode(route.params.id, language.value, code.value, customInput.value)
    runResult.value = data
  } catch (e) {
    runResult.value = { status: 'ERR', output: '', error: e.response?.data?.detail || '运行失败' }
  } finally {
    running.value = false
  }
}

// ── My stats ──────────────────────────────────────────────────────
const myStats = ref(null)

async function loadMyStats() {
  if (!userStore.isLoggedIn) return
  try {
    const { data } = await getSubmissions({ problem_id: route.params.id })
    const subs = data.results || []
    if (!subs.length) return
    const acSubs  = subs.filter(s => s.status === 'AC')
    const sorted  = [...subs].sort((a, b) => new Date(a.submitted_at) - new Date(b.submitted_at))
    const bestMs  = acSubs.length ? Math.min(...acSubs.map(s => s.time_used).filter(n => n != null)) : null
    myStats.value = {
      hasAC:    acSubs.length > 0,
      total:    subs.length,
      firstAt:  sorted[0]?.submitted_at ? fmtDate(sorted[0].submitted_at) : '',
      lastAt:   sorted.at(-1)?.submitted_at ? fmtDate(sorted.at(-1).submitted_at) : '',
      bestTime: bestMs != null && isFinite(bestMs) ? bestMs : null,
    }
  } catch {}
}

// ── Discussions ───────────────────────────────────────────────────
const discussions      = ref([])
const discussLoading   = ref(false)
const discussLoaded    = ref(false)

async function loadDiscussions() {
  if (discussLoaded.value) return
  discussLoading.value = true
  try {
    const { data } = await getDiscussions({ problem_id: problem.value.id })
    discussions.value = data.results || []
    discussLoaded.value = true
  } catch {} finally {
    discussLoading.value = false
  }
}

// ── Left panel tabs ───────────────────────────────────────────────
const activeTab = ref('problem')

function switchToDiscuss() {
  activeTab.value = 'discuss'
  loadDiscussions()
}

// ── Drag-split ────────────────────────────────────────────────────
const splitRef  = ref(null)
const leftWidth = ref(Number(localStorage.getItem('prob-split') || 60))
let isDragging = false, dragStartX = 0, dragStartW = 0

function startDrag(e) {
  isDragging = true
  dragStartX = e.clientX
  dragStartW = leftWidth.value
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', endDrag)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}
function onDrag(e) {
  if (!isDragging) return
  const cw = splitRef.value?.offsetWidth || window.innerWidth
  const delta = ((e.clientX - dragStartX) / cw) * 100
  leftWidth.value = Math.min(78, Math.max(40, dragStartW + delta))
}
function endDrag() {
  isDragging = false
  localStorage.setItem('prob-split', leftWidth.value.toFixed(1))
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', endDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// ── Navigation ────────────────────────────────────────────────────
function goPrev()   { router.push(`/problems/${prevId.value}`) }
function goNext()   { router.push(`/problems/${nextId.value}`) }

// ── Helpers ───────────────────────────────────────────────────────
function fmtDate(dt) {
  return dt ? new Date(dt).toLocaleDateString('zh-CN') : ''
}
async function copySample(text) {
  await navigator.clipboard.writeText(text)
}

function probNum(id) {
  return 'P' + String(id).padStart(4, '0')
}

// ── Keyboard shortcut ─────────────────────────────────────────────
function onKeyDown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    handleSubmit()
  }
  if (e.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────
onMounted(async () => {
  loading.value = true
  try {
    const { data } = await getProblem(route.params.id)
    problem.value = data
    prevId.value  = data.prev_id
    nextId.value  = data.next_id
    language.value = supportedLanguages.value.includes('C++') ? 'C++' : supportedLanguages.value[0]
    code.value = DEFAULT_CODE[language.value] || ''
  } finally {
    loading.value = false
  }
  loadMyStats()
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  submissionStore.stopPolling()
  endDrag()
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div v-if="loading" class="page-loading">加载中...</div>

  <div v-else-if="problem" class="problem-page">

    <!-- ── Top bar ─────────────────────────────────────────────── -->
    <div class="top-bar">
      <div class="tb-left">
        <button class="btn-back" @click="router.push('/problems')">← 题库</button>
        <span class="prob-num">{{ probNum(problem.id) }}</span>
        <span class="prob-title-text">{{ problem.title }}</span>
        <DifficultyBadge :difficulty="problem.difficulty" />
      </div>
      <div class="tb-meta">
        <span class="meta-chip">通过率 {{ passRate }}</span>
        <span class="meta-chip">AC {{ problem.ac_count }}</span>
        <span class="meta-chip">提交 {{ problem.submit_count }}</span>
        <span class="meta-chip">⏱ {{ problem.time_limit }} ms</span>
        <span class="meta-chip">💾 {{ problem.memory_limit }} MB</span>
      </div>
      <div class="tb-nav">
        <button v-if="prevId" class="btn-nav" @click="goPrev">‹ 上题</button>
        <button v-if="nextId" class="btn-nav" @click="goNext">下题 ›</button>
      </div>
    </div>

    <!-- ── Split layout ────────────────────────────────────────── -->
    <div
      class="split-layout"
      ref="splitRef"
      :style="`grid-template-columns: ${leftWidth}% 5px 1fr`"
    >

      <!-- LEFT PANEL -->
      <div class="left-panel">
        <div class="panel-tabs">
          <button :class="['ptab', activeTab==='problem' && 'ptab-active']" @click="activeTab='problem'">题目</button>
          <button :class="['ptab', activeTab==='discuss' && 'ptab-active']" @click="switchToDiscuss">讨论</button>
        </div>

        <!-- Problem content -->
        <div v-show="activeTab==='problem'" class="prob-scroll">

          <!-- Title block -->
          <div class="prob-title-block">
            <h1 class="prob-h1">
              <span class="prob-h1-num">{{ probNum(problem.id) }}</span>
              {{ problem.title }}
            </h1>
            <div class="prob-limits">
              <span>时间限制：{{ problem.time_limit }} ms</span>
              <span>内存限制：{{ problem.memory_limit }} MB</span>
              <span v-if="problem.source">来源：{{ problem.source }}</span>
            </div>
          </div>

          <!-- Tags -->
          <div v-if="problem.tags?.length" class="tags">
            <span v-for="t in problem.tags" :key="t.id" class="tag">{{ t.name }}</span>
          </div>

          <section class="prob-section">
            <h3 class="sec-head">题目描述</h3>
            <MarkdownRenderer :content="problem.description" />
          </section>

          <section class="prob-section">
            <h3 class="sec-head">输入格式</h3>
            <MarkdownRenderer :content="problem.input_desc" />
          </section>

          <section class="prob-section">
            <h3 class="sec-head">输出格式</h3>
            <MarkdownRenderer :content="problem.output_desc" />
          </section>

          <!-- Samples -->
          <section class="prob-section">
            <h3 class="sec-head">样例</h3>
            <div class="samples">
              <div class="sample-block">
                <div class="sample-head">
                  <span class="sample-label">输入</span>
                  <div class="sample-actions">
                    <button class="sa-btn" @click="fillInput(problem.sample_input)" title="填入并运行">▶ 运行</button>
                    <button class="sa-btn" @click="copySample(problem.sample_input)">复制</button>
                  </div>
                </div>
                <pre class="sample-pre">{{ problem.sample_input }}</pre>
              </div>
              <div class="sample-block">
                <div class="sample-head">
                  <span class="sample-label">输出</span>
                  <button class="sa-btn" @click="copySample(problem.sample_output)">复制</button>
                </div>
                <pre class="sample-pre">{{ problem.sample_output }}</pre>
              </div>
            </div>
          </section>

          <section v-if="problem.hint" class="prob-section">
            <h3 class="sec-head">提示</h3>
            <MarkdownRenderer :content="problem.hint" />
          </section>

          <!-- My stats card -->
          <div v-if="myStats" class="my-stats">
            <div class="ms-title">我的记录</div>
            <div class="ms-grid">
              <div class="ms-item">
                <span class="ms-label">状态</span>
                <span :class="['ms-val', myStats.hasAC ? 'ms-ac' : 'ms-try']">
                  {{ myStats.hasAC ? '✓ 已通过' : '尝试中' }}
                </span>
              </div>
              <div class="ms-item">
                <span class="ms-label">提交次数</span>
                <span class="ms-val">{{ myStats.total }}</span>
              </div>
              <div v-if="myStats.firstAt" class="ms-item">
                <span class="ms-label">首次提交</span>
                <span class="ms-val">{{ myStats.firstAt }}</span>
              </div>
              <div v-if="myStats.lastAt" class="ms-item">
                <span class="ms-label">最近提交</span>
                <span class="ms-val">{{ myStats.lastAt }}</span>
              </div>
              <div v-if="myStats.bestTime != null" class="ms-item">
                <span class="ms-label">最佳耗时</span>
                <span class="ms-val mono">{{ myStats.bestTime }} ms</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Discussion tab -->
        <div v-show="activeTab==='discuss'" class="discuss-scroll">
          <div v-if="discussLoading" class="loading-tip">加载中…</div>
          <div v-else>
            <div v-if="discussions.length === 0" class="empty-tip">暂无讨论</div>
            <div v-else class="disc-list">
              <div
                v-for="d in discussions" :key="d.id"
                class="disc-row"
                @click="router.push(`/discussions/${d.id}`)"
              >
                <div class="disc-title">{{ d.title }}</div>
                <div class="disc-meta">{{ d.username }} · {{ d.reply_count }} 回复 · {{ fmtDate(d.created_at) }}</div>
              </div>
            </div>
            <button class="btn-new-disc" @click="router.push(`/discussions/create?problem=${problem.id}`)">
              + 发帖讨论
            </button>
          </div>
        </div>
      </div>

      <!-- DRAG HANDLE -->
      <div class="drag-handle" @mousedown.prevent="startDrag"></div>

      <!-- RIGHT PANEL -->
      <div :class="['right-panel', isFullscreen && 'right-fullscreen']">

        <!-- Editor toolbar -->
        <div class="editor-toolbar">
          <select class="lang-select" v-model="language" @change="onLangChange">
            <option v-for="lang in supportedLanguages" :key="lang" :value="lang">{{ lang }}</option>
          </select>
          <div class="tb-right">
            <button class="tbtn" @click="fontSize = Math.max(12, fontSize - 1)">A−</button>
            <span class="font-sz">{{ fontSize }}</span>
            <button class="tbtn" @click="fontSize = Math.min(22, fontSize + 1)">A+</button>
            <div class="tb-sep"></div>
            <button class="tbtn" @click="toggleEditorTheme" :title="editorTheme === 'vs-dark' ? '切换浅色主题' : '切换深色主题'">
              {{ editorTheme === 'vs-dark' ? '☀' : '🌙' }}
            </button>
            <button class="tbtn" @click="resetCode" title="重置代码">↺</button>
            <button class="tbtn" @click="formatCode" title="格式化代码">格式化</button>
            <button class="tbtn" :class="copyCodeTip && 'tbtn-ok'" @click="copyCode" title="复制代码">
              {{ copyCodeTip ? '✓' : '复制' }}
            </button>
            <button class="tbtn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏编辑器'">
              {{ isFullscreen ? '⊠' : '⤢' }}
            </button>
          </div>
        </div>

        <!-- Monaco editor -->
        <div class="editor-container">
          <CodeEditor
            ref="editorRef"
            v-model="code"
            :language="language"
            :theme="editorTheme"
            :font-size="fontSize"
          />
        </div>

        <!-- Action bar -->
        <div class="action-bar">
          <button
            :class="['btn-run-code', showRunPanel && 'btn-run-active']"
            @click="showRunPanel = !showRunPanel"
          >
            ▶ 运行代码
          </button>
          <div class="action-right">
            <span v-if="submitError" class="submit-err">{{ submitError }}</span>
            <span class="shortcut-hint">Ctrl+Enter</span>
            <button
              class="btn-submit-code"
              :disabled="submitting || submissionStore.polling"
              @click="handleSubmit"
            >
              {{ submitting ? '提交中...' : submissionStore.polling ? '评测中...' : '提交评测' }}
            </button>
          </div>
        </div>

        <!-- Run panel -->
        <div v-if="showRunPanel" class="run-panel">
          <div class="rp-section">
            <div class="rp-label">
              自定义输入
              <button class="tbtn-xs" @click="showRunPanel = false">✕</button>
            </div>
            <textarea
              class="run-input"
              v-model="customInput"
              placeholder="在此输入测试数据，可从题目样例复制…"
              rows="4"
            ></textarea>
          </div>
          <button class="btn-run-exec" :disabled="running" @click="doRun">
            {{ running ? '运行中…' : '▶ 执行' }}
          </button>
          <div v-if="runResult" class="rp-section">
            <div class="rp-label">
              运行结果
              <span :class="['rp-status', runResult.status === 'OK' ? 'rp-ok' : 'rp-err']">
                {{ runResult.status }}
              </span>
            </div>
            <pre class="run-output">{{ runResult.status === 'OK' ? (runResult.output || '（无输出）') : runResult.error }}</pre>
          </div>
        </div>

        <!-- Judge result -->
        <div class="result-area" v-if="submissionStore.current">
          <JudgeResult
            :submission="submissionStore.current"
            :polling="submissionStore.polling"
          />
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Page shell ──────────────────────────────────────────────────── */
.page-loading {
  text-align: center; padding: 4rem; color: var(--text-muted);
}

.problem-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 57px);
  overflow: hidden;
}

/* ── Top bar ──────────────────────────────────────────────────────── */
.top-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0 1rem;
  height: 44px;
  flex-shrink: 0;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  overflow: hidden;
}

.tb-left {
  display: flex; align-items: center; gap: 0.6rem; min-width: 0;
}
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.8rem;
  white-space: nowrap; flex-shrink: 0; transition: border-color 0.15s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.prob-num {
  font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700;
  color: var(--accent); white-space: nowrap; flex-shrink: 0;
}
.prob-title-text {
  font-weight: 600; font-size: 0.9rem; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px;
}

.tb-meta {
  display: flex; align-items: center; gap: 0.4rem;
  flex-shrink: 0; margin-left: auto;
}
.meta-chip {
  font-size: 0.75rem; color: var(--text-muted);
  background: var(--bg-secondary); padding: 0.15rem 0.5rem;
  border-radius: 4px; white-space: nowrap;
}

.tb-nav {
  display: flex; gap: 0.3rem; flex-shrink: 0;
}
.btn-nav {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.8rem;
  white-space: nowrap; transition: all 0.15s;
}
.btn-nav:hover { border-color: var(--accent); color: var(--accent); }

/* ── Split layout ─────────────────────────────────────────────────── */
.split-layout {
  flex: 1;
  display: grid;
  overflow: hidden;
  min-height: 0;
}

.drag-handle {
  background: var(--border);
  cursor: col-resize;
  transition: background 0.15s;
}
.drag-handle:hover { background: var(--accent); }

/* ── Left panel ───────────────────────────────────────────────────── */
.left-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  border-right: none;
}

.panel-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;
}
.ptab {
  padding: 0.55rem 1.1rem; font-size: 0.875rem;
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-secondary); cursor: pointer; transition: color 0.15s, border-color 0.15s;
}
.ptab:hover { color: var(--text-primary); }
.ptab-active { color: var(--accent); border-bottom-color: var(--accent); }

.prob-scroll, .discuss-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem;
  background: var(--bg-page);
}

/* Title block */
.prob-title-block { margin-bottom: 1.25rem; }
.prob-h1 {
  font-size: 1.5rem; font-weight: 700; color: var(--text-primary);
  line-height: 1.35; margin: 0 0 0.4rem; display: flex; align-items: baseline; gap: 0.5rem;
  flex-wrap: wrap;
}
.prob-h1-num {
  font-family: var(--font-mono); font-size: 1.3rem; color: var(--accent); flex-shrink: 0;
}
.prob-limits {
  display: flex; gap: 1.25rem; flex-wrap: wrap;
  font-size: 0.82rem; color: var(--text-muted);
}

/* Tags */
.tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 1.25rem; }
.tag {
  background: var(--bg-secondary); color: var(--text-secondary);
  font-size: 12px; padding: 2px 8px; border-radius: 4px;
  border: 1px solid var(--border);
}

/* Problem sections */
.prob-section {
  margin-bottom: 1.75rem; max-width: 860px;
}
.sec-head {
  font-size: 1.05rem; font-weight: 700; color: var(--text-primary);
  margin: 0 0 0.75rem; padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--border);
}

/* Samples */
.samples { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
@media (max-width: 600px) { .samples { grid-template-columns: 1fr; } }

.sample-block {
  background: var(--bg-hover); border: 1px solid var(--border);
  border-radius: 6px; overflow: hidden;
}
.sample-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.3rem 0.6rem; background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}
.sample-label { font-size: 0.75rem; font-weight: 500; color: var(--text-muted); }
.sample-actions { display: flex; gap: 0.3rem; }
.sa-btn {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.1rem 0.45rem; border-radius: 3px; cursor: pointer; font-size: 0.7rem;
  transition: all 0.1s;
}
.sa-btn:hover { border-color: var(--accent); color: var(--accent); }
.sample-pre {
  margin: 0; padding: 0.6rem 0.75rem;
  font-family: var(--font-mono); font-size: 13px; color: var(--text-secondary);
  white-space: pre-wrap; word-break: break-all; line-height: 1.6;
  min-height: 52px;
}

/* My stats card */
.my-stats {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.9rem 1rem; margin-top: 1rem;
}
.ms-title {
  font-size: 0.78rem; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.6rem;
}
.ms-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.ms-item { display: flex; flex-direction: column; gap: 0.1rem; }
.ms-label { font-size: 0.72rem; color: var(--text-muted); }
.ms-val { font-size: 0.85rem; font-weight: 500; color: var(--text-primary); }
.ms-ac  { color: #10b981; }
.ms-try { color: #f59e0b; }
.mono   { font-family: var(--font-mono); }

/* Discussion tab */
.loading-tip, .empty-tip { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }
.disc-list { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.disc-row {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.7rem 0.9rem; cursor: pointer;
  transition: border-color 0.1s;
}
.disc-row:hover { border-color: var(--accent); }
.disc-title { font-size: 0.9rem; font-weight: 500; color: var(--text-primary); margin-bottom: 0.2rem; }
.disc-meta  { font-size: 0.75rem; color: var(--text-muted); }
.btn-new-disc {
  background: none; border: 1px dashed var(--border); color: var(--accent);
  width: 100%; padding: 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem;
  transition: all 0.15s;
}
.btn-new-disc:hover { border-color: var(--accent); background: var(--accent-light); }

/* ── Right panel ──────────────────────────────────────────────────── */
.right-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background: var(--bg-page);
}

.right-fullscreen {
  position: fixed;
  inset: 57px 0 0 0;
  z-index: 200;
  background: var(--bg-page);
}

/* Editor toolbar */
.editor-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.4rem 0.75rem; background: var(--bg-card);
  border-bottom: 1px solid var(--border); flex-shrink: 0; gap: 0.5rem;
}
.lang-select {
  background: var(--bg-secondary); border: 1px solid var(--border);
  color: var(--text-primary); padding: 0.25rem 0.6rem;
  border-radius: 5px; font-size: 0.85rem; cursor: pointer; outline: none;
  font-weight: 500;
}
.tb-right {
  display: flex; align-items: center; gap: 0.3rem;
}
.tbtn {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.75rem;
  transition: all 0.1s; white-space: nowrap;
}
.tbtn:hover { border-color: var(--accent); color: var(--accent); }
.tbtn-ok { border-color: #10b981; color: #10b981; }
.font-sz { font-size: 0.75rem; color: var(--text-muted); min-width: 1.5rem; text-align: center; }
.tb-sep { width: 1px; height: 14px; background: var(--border); margin: 0 0.15rem; }

/* Editor */
.editor-container {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* Action bar */
.action-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.5rem 0.75rem; background: var(--bg-card);
  border-top: 1px solid var(--border); flex-shrink: 0; gap: 0.75rem;
}
.btn-run-code {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem;
  transition: all 0.15s; white-space: nowrap;
}
.btn-run-code:hover, .btn-run-active {
  border-color: var(--accent); color: var(--accent); background: var(--accent-light);
}
.action-right { display: flex; align-items: center; gap: 0.6rem; }
.submit-err { font-size: 0.78rem; color: var(--status-wa-text); }
.shortcut-hint { font-size: 0.72rem; color: var(--text-muted); }
.btn-submit-code {
  padding: 0.4rem 1.4rem; background: var(--accent); color: #fff;
  border: none; border-radius: 6px; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; transition: background 0.15s; white-space: nowrap;
}
.btn-submit-code:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit-code:disabled { opacity: 0.55; cursor: not-allowed; }

/* Run panel */
.run-panel {
  flex-shrink: 0;
  background: var(--bg-card); border-top: 1px solid var(--border);
  padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;
  max-height: 320px; overflow-y: auto;
}
.rp-section { display: flex; flex-direction: column; gap: 0.3rem; }
.rp-label {
  font-size: 0.75rem; font-weight: 500; color: var(--text-muted);
  display: flex; align-items: center; gap: 0.5rem;
}
.tbtn-xs {
  margin-left: auto; background: none; border: none; color: var(--text-muted);
  cursor: pointer; padding: 0.1rem 0.3rem; font-size: 0.8rem;
}
.tbtn-xs:hover { color: var(--text-primary); }
.run-input {
  width: 100%; background: var(--bg-secondary); border: 1px solid var(--border);
  color: var(--text-primary); border-radius: 5px; padding: 0.5rem;
  font-family: var(--font-mono); font-size: 0.82rem; resize: vertical;
  outline: none; line-height: 1.5; box-sizing: border-box;
}
.run-input:focus { border-color: var(--accent); }
.btn-run-exec {
  align-self: flex-start; background: none; border: 1px solid var(--accent);
  color: var(--accent); padding: 0.3rem 1rem; border-radius: 5px;
  cursor: pointer; font-size: 0.82rem; transition: all 0.15s;
}
.btn-run-exec:hover:not(:disabled) { background: var(--accent); color: #fff; }
.btn-run-exec:disabled { opacity: 0.5; cursor: not-allowed; }
.rp-status { font-size: 0.72rem; font-weight: 600; padding: 0.1rem 0.35rem; border-radius: 3px; }
.rp-ok  { background: rgba(16,185,129,0.1); color: #10b981; }
.rp-err { background: rgba(239,68,68,0.08); color: var(--status-wa-text); }
.run-output {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 5px; padding: 0.5rem 0.75rem;
  font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-primary);
  white-space: pre-wrap; word-break: break-all; line-height: 1.6; margin: 0;
  max-height: 160px; overflow-y: auto;
}

/* Result area */
.result-area {
  flex-shrink: 0; padding: 0.6rem;
  background: var(--bg-page);
}

/* Responsive */
@media (max-width: 1100px) {
  .split-layout { grid-template-columns: 1fr !important; grid-template-rows: 1fr 1fr; }
  .drag-handle { display: none; }
  .left-panel { border-right: none; border-bottom: 1px solid var(--border); }
  .problem-page { height: auto; overflow: visible; }
  .left-panel, .right-panel { min-height: 50vh; }
}
@media (max-width: 768px) {
  .tb-meta { display: none; }
  .prob-title-text { max-width: 160px; }
  .samples { grid-template-columns: 1fr; }
}
</style>
