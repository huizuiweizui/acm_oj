<script setup>
// 入门层：分步学习。一屏一步，顶部流程条显示进度。
// 题型：选择题、填空题、代码行排序（Parsons 题）。排序结果拼成完整程序，由平台评测机运行判定。
// 提示按钮每点一次升一级，最多三级；作答时把用到的最高提示等级一起交给后端记录。
import { computed, ref, watch } from 'vue'
import FlowBar from './FlowBar.vue'
import { getHint, submitAttempt } from '@/api/star'

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
  return pool.value.length === 0
})

function resetStep() {
  hintLevel.value = 0
  hints.value = []
  selected.value = null
  fillText.value = ''
  pool.value = step.value?.type === 'order' ? step.value.lines.map((_, i) => i) : []
  answer.value = []
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
    feedback.value = {
      ...data.feedback,
      ok: data.correct,
      extra: t === 'order' && !data.correct && data.total ? `通过了 ${data.passed} / ${data.total} 组测试数据。` : '',
    }
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
        · {{ step.type === 'choice' ? '选一选' : step.type === 'fill' ? '填一填' : '排一排' }}
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
          <span v-if="selected === i" class="s-check" aria-hidden="true">✓</span>
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
        {{ step.type === 'order' ? '正在运行你的程序……' : '正在检查……' }}
      </div>
      <div v-else-if="feedback" class="s-feedback" :class="feedback.ok ? 'is-ok' : 'is-bad'" role="status">
        <span class="s-fb-icon" aria-hidden="true">{{ feedback.icon }}</span>
        <span>{{ feedback.text }}<br v-if="feedback.extra"><small v-if="feedback.extra">{{ feedback.extra }}</small></span>
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
.line-list.answer { border-style: solid; border-color: var(--s-accent); background: var(--s-card); }
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
</style>
