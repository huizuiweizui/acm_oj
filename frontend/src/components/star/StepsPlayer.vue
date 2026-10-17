<script setup>
// 入门层：分步学习。一屏一步，顶部流程条显示进度。
// 题型：选择题、填空题、代码行排序（Parsons 题）、写代码。排序结果和自己写的程序都由平台评测机运行判定。
// 每个任务固定以"排一排 → 自己写"收尾：先把参考解的代码行排好，再在起始代码（注释骨架）上自己写一遍。
// 提示按钮每点一次升一级，最多三级；作答时把用到的最高提示等级一起交给后端记录。
import { computed, nextTick, ref, watch } from 'vue'
import FlowBar from './FlowBar.vue'
import { getHint, submitAttempt } from '@/api/star'
import { starMark } from './starUi'

const props = defineProps({
  taskId: { type: Number, required: true },
  content: { type: Object, required: true },
  doneSteps: { type: Array, default: () => [] },
})
const emit = defineEmits(['step-change', 'done'])

const KNOWLEDGE = { sequence: '顺序', loop: '循环', condition: '条件' }
const steps = computed(() => props.content.steps || [])
const done = ref([...props.doneSteps])
const firstOpen = () => {
  const i = steps.value.findIndex((_, k) => !done.value.includes(k))
  return i === -1 ? 0 : i
}
const current = ref(firstOpen())
const showIntro = ref(done.value.length === 0 && (props.content.intro || []).length > 0)

// 每一步的作答状态
const hintLevel = ref(0)
const hints = ref([])
const selected = ref(null)
const fillText = ref('')
const pool = ref([])
const answer = ref([])
const codeText = ref('')
const errorLine = ref(0)
const codeBox = ref(null)
let tabLeaves = false            // 按过 Esc 后，下一次 Tab 离开编辑框（不把键盘困在里面）
const feedback = ref(null)
const checking = ref(false)
const solvedNow = ref(false)
let startedAt = Date.now()

const step = computed(() => steps.value[current.value])
const isLast = computed(() => current.value === steps.value.length - 1)
const allDone = computed(() => steps.value.length > 0 && steps.value.every((_, k) => done.value.includes(k)))
const fillParts = computed(() => (step.value?.code || '').split('____'))
const canCheck = computed(() => {
  if (!step.value || checking.value) return false
  if (step.value.type === 'choice') return selected.value !== null
  if (step.value.type === 'fill') return fillText.value.trim() !== ''
  if (step.value.type === 'code') return codeText.value.trim() !== ''
  return pool.value.length === 0
})
const codeRows = computed(() => Math.max(codeText.value.split('\n').length, 6))

// 写到一半离开页面，回来时代码还在（只存在这台电脑上）
const draftKey = () => `star:code:${props.taskId}:${current.value}`
function loadDraft() {
  try { return localStorage.getItem(draftKey()) } catch { return null }
}
function saveDraft() {
  try { localStorage.setItem(draftKey(), codeText.value) } catch { /* 存不了就算了 */ }
}

function resetStep() {
  hintLevel.value = 0
  hints.value = []
  selected.value = null
  fillText.value = ''
  pool.value = step.value?.type === 'order' ? step.value.lines.map((_, i) => i) : []
  answer.value = []
  codeText.value = step.value?.type === 'code' ? (loadDraft() ?? step.value.starter ?? '') : ''
  errorLine.value = 0
  feedback.value = null
  solvedNow.value = done.value.includes(current.value)
  startedAt = Date.now()
}

watch(current, () => {
  resetStep()
  emit('step-change', current.value)
}, { immediate: true })

function start() {
  showIntro.value = false
  startedAt = Date.now()
}

function go(i) {
  if (i < 0 || i >= steps.value.length) return
  current.value = i
}

function looksLikeCode(s) {
  return /[()=<>%+*"[\]:]/.test(s)
}

// ── 排序题：点一下移过去，也可以拖拽 ──
function toAnswer(lineIdx, at = null) {
  pool.value = pool.value.filter((i) => i !== lineIdx)
  answer.value = answer.value.filter((i) => i !== lineIdx)
  if (at === null || at >= answer.value.length) answer.value.push(lineIdx)
  else answer.value.splice(at, 0, lineIdx)
  feedback.value = null
}
function toPool(lineIdx) {
  answer.value = answer.value.filter((i) => i !== lineIdx)
  pool.value = [...pool.value, lineIdx].sort((a, b) => a - b)
  feedback.value = null
}
function moveUp(pos) {
  if (pos <= 0) return
  const a = [...answer.value];
  [a[pos - 1], a[pos]] = [a[pos], a[pos - 1]]
  answer.value = a
  feedback.value = null
}
function onLineDrag(e, lineIdx) {
  e.dataTransfer.setData('text/plain', String(lineIdx))
}
function onDropAnswer(e, at = null) {
  const v = Number(e.dataTransfer.getData('text/plain'))
  if (!Number.isNaN(v)) toAnswer(v, at)
}
function onDropPool(e) {
  const v = Number(e.dataTransfer.getData('text/plain'))
  if (!Number.isNaN(v) && answer.value.includes(v)) toPool(v)
}

// ── 写代码：Tab 缩进四格，回车保持缩进，冒号结尾的下一行自动多缩进一层 ──
function insertAt(el, text) {
  el.setRangeText(text, el.selectionStart, el.selectionEnd, 'end')
  codeText.value = el.value
}
function onCodeKey(e) {
  const el = e.target
  if (e.key === 'Escape') {
    tabLeaves = true
    return
  }
  if (e.key === 'Tab' && !e.shiftKey && !tabLeaves) {
    e.preventDefault()
    insertAt(el, '    ')
    return
  }
  tabLeaves = false
  if (e.key === 'Enter' && !e.isComposing) {
    e.preventDefault()
    const before = el.value.slice(0, el.selectionStart)
    const line = before.slice(before.lastIndexOf('\n') + 1)
    let indent = line.match(/^ */)[0]
    if (line.trimEnd().endsWith(':')) indent += '    '
    insertAt(el, `\n${indent}`)
  }
}
function restoreStarter() {
  codeText.value = step.value.starter || ''
  errorLine.value = 0
  feedback.value = null
  nextTick(() => codeBox.value?.focus())
}
watch(codeText, () => {
  if (step.value?.type === 'code' && !solvedNow.value) saveDraft()
})

async function askHint() {
  if (hintLevel.value >= 3) return
  const next = hintLevel.value + 1
  try {
    const { data } = await getHint(props.taskId, current.value, next)
    hintLevel.value = next
    hints.value = [...hints.value, data.text]
  } catch {
    feedback.value = { icon: '⚠️', text: '提示没有拿到，请再点一次。', ok: false }
  }
}

async function check() {
  if (!canCheck.value) return
  const t = step.value.type
  const ans = t === 'choice' ? { choice: selected.value }
    : t === 'fill' ? { text: fillText.value }
      : t === 'code' ? { code: codeText.value }
        : { order: [...answer.value] }
  checking.value = true
  feedback.value = null
  try {
    const { data } = await submitAttempt(props.taskId, {
      step: current.value,
      answer: ans,
      hint_level: hintLevel.value,
      duration_ms: Date.now() - startedAt,
    })
    const runs = t === 'order' || t === 'code'
    feedback.value = {
      ...data.feedback,
      ok: data.correct,
      extra: runs && !data.correct && data.total ? `通过了 ${data.passed} / ${data.total} 组测试数据。` : '',
      errorText: data.error_text || '',
      errorRaw: data.error_raw || '',
      fail: data.first_fail || null,
    }
    errorLine.value = data.error_line || 0
    startedAt = Date.now()
    done.value = data.done_steps
    if (data.correct) {
      solvedNow.value = true
      if (data.task_done) emit('done')
    }
  } catch (e) {
    const busy = e.response?.status === 503
    feedback.value = {
      icon: '⚠️',
      text: busy ? '电脑有点忙，请等一下再按检查。' : (e.response?.data?.detail || '没有连上，请再按一次检查。'),
      ok: false,
    }
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div class="steps">
    <FlowBar :total="steps.length" :current="current" :done="done" />

    <!-- 开场说明：一屏只说这件事 -->
    <section v-if="showIntro" class="s-card step-card">
      <p class="s-muted">今天的任务</p>
      <h2 class="s-title">{{ content.title }}</h2>
      <p v-for="(s, i) in content.intro" :key="i" class="intro-line">{{ s }}</p>
      <div class="s-btn-row">
        <button type="button" class="s-btn s-btn-primary" @click="start">开始第 1 步 →</button>
      </div>
    </section>

    <section v-else-if="step" class="s-card step-card" :aria-label="`第 ${current + 1} 步`">
      <p class="s-muted">
        第 {{ current + 1 }} 步 · {{ KNOWLEDGE[step.knowledge] || '' }}
        · {{ { choice: '选一选', fill: '填一填', order: '排一排', code: '写一写' }[step.type] }}
      </p>
      <h2 class="s-title">{{ step.prompt }}</h2>

      <!-- 选择题 -->
      <div v-if="step.type === 'choice'" class="options" role="radiogroup" :aria-label="step.prompt">
        <button
          v-for="(opt, i) in step.options"
          :key="i"
          type="button"
          role="radio"
          :aria-checked="selected === i"
          class="s-option"
          :class="{ 'is-selected': selected === i, mono: looksLikeCode(opt) }"
          :disabled="solvedNow"
          @click="selected = i; feedback = null"
        >
          <span class="opt-letter" aria-hidden="true">{{ 'ABCD'[i] }}</span>
          <span>{{ opt }}</span>
          <span v-if="selected === i" class="s-check" aria-hidden="true">{{ starMark }}</span>
        </button>
      </div>

      <!-- 填空题 -->
      <div v-else-if="step.type === 'fill'" class="s-code fill-line">
        <span>{{ fillParts[0] }}</span><input
          v-model="fillText"
          class="fill-input"
          :disabled="solvedNow"
          aria-label="填在空里的内容"
          autocomplete="off"
          spellcheck="false"
          @keydown.enter="check"
        ><span>{{ fillParts.slice(1).join('____') }}</span>
      </div>

      <!-- 写代码：注释是起始代码给的骨架，照着一块一块写 -->
      <div v-else-if="step.type === 'code'" class="code-step">
        <div class="editor" :class="{ 'is-done': solvedNow }">
          <ol class="gutter" aria-hidden="true">
            <li v-for="n in codeRows" :key="n" :class="{ 'is-err': n === errorLine }">{{ n }}</li>
          </ol>
          <textarea
            ref="codeBox"
            v-model="codeText"
            class="code-input"
            :rows="codeRows"
            :readonly="solvedNow"
            aria-label="在这里写程序"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            wrap="off"
            @keydown="onCodeKey"
          ></textarea>
        </div>
        <p class="s-muted code-tip">
          Tab 键空四格；冒号后面换行会自动空四格。
          <button v-if="!solvedNow" type="button" class="link-btn" @click="restoreStarter">恢复起始代码</button>
        </p>
      </div>

      <!-- 排序题 -->
      <div v-else class="parsons">
        <div class="parsons-col">
          <h3 class="col-title">代码块（点一下放进右边）</h3>
          <ul class="line-list pool" @dragover.prevent @drop.prevent="onDropPool">
            <li v-for="i in pool" :key="`p${i}`">
              <button
                type="button"
                class="line"
                draggable="true"
                :disabled="solvedNow"
                @dragstart="onLineDrag($event, i)"
                @click="toAnswer(i)"
              >{{ step.lines[i] }}</button>
            </li>
            <li v-if="!pool.length" class="s-muted empty">都放好了</li>
          </ul>
        </div>
        <div class="parsons-col">
          <h3 class="col-title">我的程序（点一下拿回去）</h3>
          <ol class="line-list answer" @dragover.prevent @drop.prevent="onDropAnswer($event)">
            <li
              v-for="(i, pos) in answer"
              :key="`a${i}`"
              class="answer-row"
              @dragover.prevent
              @drop.prevent.stop="onDropAnswer($event, pos)"
            >
              <span class="line-no">{{ pos + 1 }}</span>
              <button
                type="button"
                class="line"
                draggable="true"
                :disabled="solvedNow"
                @dragstart="onLineDrag($event, i)"
                @click="toPool(i)"
              >{{ step.lines[i] }}</button>
              <button
                v-if="pos > 0 && !solvedNow"
                type="button"
                class="up-btn"
                :aria-label="`把第 ${pos + 1} 行往上移`"
                @click="moveUp(pos)"
              >↑</button>
            </li>
            <li v-if="!answer.length" class="s-muted empty">从左边点代码，放到这里</li>
          </ol>
          <p v-if="pool.length && answer.length" class="s-muted">还有 {{ pool.length }} 行没有放。</p>
        </div>
      </div>

      <ol v-if="hints.length" class="hint-list">
        <li v-for="(h, i) in hints" :key="i" class="s-hint">💡 提示 {{ i + 1 }}：{{ h }}</li>
      </ol>

      <div v-if="checking" class="s-feedback" role="status">
        <span class="s-fb-icon" aria-hidden="true">⏳</span>
        {{ step.type === 'order' || step.type === 'code' ? '正在运行你的程序……' : '正在检查……' }}
      </div>
      <div v-else-if="feedback" class="s-feedback" :class="feedback.ok ? 'is-ok' : 'is-bad'" role="status">
        <span class="s-fb-icon" aria-hidden="true">{{ feedback.icon }}</span>
        <div class="fb-body">
          <span>{{ feedback.text }}</span>
          <b v-if="feedback.errorText" class="fb-err">{{ feedback.errorText }}</b>
          <code v-if="feedback.errorRaw" class="fb-raw">{{ feedback.errorRaw }}</code>
          <table v-if="feedback.fail" class="fail-table">
            <tbody>
              <tr><th>输入</th><td><pre>{{ feedback.fail.input }}</pre></td></tr>
              <tr><th>应该输出</th><td><pre>{{ feedback.fail.expected }}</pre></td></tr>
              <tr><th>你的程序输出</th><td><pre>{{ feedback.fail.output || '（什么也没输出）' }}</pre></td></tr>
            </tbody>
          </table>
          <small v-if="feedback.extra">{{ feedback.extra }}</small>
        </div>
      </div>
      <div v-else-if="solvedNow" class="s-feedback is-ok" role="status">
        <span class="s-fb-icon" aria-hidden="true">✅</span>这一步已经做对了。
      </div>

      <div class="s-btn-row actions">
        <template v-if="!solvedNow">
          <button type="button" class="s-btn s-btn-primary" :disabled="!canCheck" @click="check">检查</button>
          <button type="button" class="s-btn" :disabled="hintLevel >= 3" @click="askHint">
            💡 提示（{{ hintLevel }} / 3）
          </button>
        </template>
        <template v-else>
          <button v-if="!isLast" type="button" class="s-btn s-btn-primary" @click="go(current + 1)">下一步 →</button>
          <button v-else-if="allDone" type="button" class="s-btn s-btn-primary" @click="emit('done')">完成任务 ✓</button>
        </template>
        <button v-if="current > 0" type="button" class="s-btn back-btn" @click="go(current - 1)">← 上一步</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.steps { display: flex; flex-direction: column; gap: 20px; }
.step-card { display: flex; flex-direction: column; gap: 18px; }
.step-card .s-title { margin: 0; }
.intro-line { margin: 0; font-size: 24px; }
.options { display: flex; flex-direction: column; gap: 12px; max-width: 640px; }
.opt-letter {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  border: 2px solid var(--s-border-strong);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.s-option.mono span:nth-child(2) { font-family: var(--font-mono); }
.fill-line { display: inline-flex; align-items: center; flex-wrap: wrap; width: max-content; max-width: 100%; }
.fill-input {
  font: inherit;
  width: 7em;
  min-height: 44px;
  margin: 0 6px;
  padding: 4px 8px;
  border: 2px solid var(--s-accent);
  border-radius: 6px;
  background: #fff;
}
.parsons { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 800px) { .parsons { grid-template-columns: 1fr; } }
.col-title { font-size: 17px; margin: 0 0 8px; color: var(--s-text-2); }
.line-list {
  list-style: none;
  margin: 0;
  padding: 10px;
  min-height: 120px;
  border: 2px dashed var(--s-border-strong);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fbfaf6;
}
.line-list.answer { border-style: solid; border-color: var(--s-accent-ink, var(--s-accent)); background: var(--s-card); }
.answer-row { display: flex; align-items: center; gap: 8px; }
.line-no { width: 24px; text-align: right; font-family: var(--font-mono); font-size: 15px; color: var(--s-text-2); }
.line {
  flex: 1;
  text-align: left;
  font-family: var(--font-mono);
  font-size: 18px;
  white-space: pre;
  min-height: 48px;
  padding: 8px 12px;
  border-radius: 6px;
  border: 2px solid var(--s-border-strong);
  background: var(--s-code-bg);
  color: var(--s-text);
  cursor: pointer;
  width: 100%;
}
.line:disabled { cursor: default; }
.up-btn {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  border: 2px solid var(--s-border-strong);
  background: var(--s-card);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.empty { padding: 8px; }
.hint-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.hint-list .s-hint { margin: 0; }
.actions .back-btn { margin-left: auto; }
.s-feedback small { font-weight: 400; color: var(--s-text-2); }

.code-step { display: flex; flex-direction: column; gap: 8px; }
.editor {
  display: flex;
  border: 2px solid var(--s-accent);
  border-radius: 8px;
  background: var(--s-code-bg);
  overflow: hidden;
}
.editor.is-done { border-color: var(--s-border-strong); }
.gutter {
  list-style: none;
  margin: 0;
  padding: 12px 0;
  min-width: 48px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 18px;
  line-height: 1.6;
  color: var(--s-text-2);
  background: var(--s-card);
  border-right: 1px solid var(--s-border);
  user-select: none;
}
.gutter li { padding: 0 10px 0 6px; }
.gutter li.is-err { background: var(--s-bad-soft); color: var(--s-bad); font-weight: 700; }
.code-input {
  flex: 1;
  min-width: 0;
  margin: 0;
  padding: 12px 14px;
  border: 0;
  outline: none;
  resize: none;
  overflow-x: auto;
  overflow-y: hidden;
  white-space: pre;
  font-family: var(--font-mono);
  font-size: 18px;
  line-height: 1.6;
  tab-size: 4;
  background: transparent;
  color: var(--s-text);
}
.editor:focus-within { outline: 3px solid var(--s-accent); outline-offset: 2px; }
.code-tip { margin: 0; font-size: 16px; display: flex; gap: 16px; flex-wrap: wrap; align-items: baseline; }
.link-btn {
  font: inherit;
  background: none;
  border: 0;
  padding: 0;
  color: var(--s-accent);
  text-decoration: underline;
  cursor: pointer;
}
.fb-body { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.fb-err { font-weight: 700; }
.fb-raw {
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 400;
  color: var(--s-text-2);
  word-break: break-all;
}
.fail-table { border-collapse: collapse; font-size: 17px; font-weight: 400; }
.fail-table th {
  text-align: left;
  padding: 4px 14px 4px 0;
  vertical-align: top;
  white-space: nowrap;
  color: var(--s-text-2);
  font-weight: 600;
}
.fail-table td { padding: 4px 0; }
.fail-table pre {
  margin: 0;
  padding: 4px 10px;
  font-family: var(--font-mono);
  font-size: 16px;
  background: var(--s-card);
  border: 1px solid var(--s-border);
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
