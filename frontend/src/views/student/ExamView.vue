<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { enterExam, getPaper, submitAnswer, submitExam, reportFocusLoss } from '@/api/exam'

const route = useRoute()
const router = useRouter()
const aid = Number(route.params.aid)

const loading = ref(true)
const errorMsg = ref('')
const paper = ref(null)
const participation = ref(null)
const answers = reactive({})    // qid -> 当前作答
const saveState = reactive({})  // qid -> 'saving' | 'saved' | ''
const feedback = reactive({})   // qid -> { correct, got_score, explanation }
const submitting = ref(false)
const result = ref(null)
const focusCount = ref(0)
const focusWarn = ref(false)

const CAT_LABEL = { practice: '练习', homework: '作业', exam: '考试' }
const isExam = computed(() => paper.value?.category === 'exam')
const submitted = computed(() =>
  !!result.value || ['submitted', 'graded'].includes(participation.value?.status))

// ── 倒计时 ──────────────────────────────────────────────────────────
const remainingMs = ref(0)
let timer = null, clientStart = 0, serverStart = 0, deadlineMs = 0

function setupTimer() {
  const pd = participation.value?.personal_deadline
  if (!isExam.value || !pd || submitted.value) return
  deadlineMs = new Date(pd).getTime()
  serverStart = new Date(participation.value.server_now).getTime()
  clientStart = Date.now()
  tick()
  timer = setInterval(tick, 1000)
}
function tick() {
  const serverNow = serverStart + (Date.now() - clientStart)
  remainingMs.value = Math.max(0, deadlineMs - serverNow)
  if (remainingMs.value <= 0) {
    clearInterval(timer); timer = null
    if (!submitted.value) doSubmit(true)
  }
}
const remainingText = computed(() => {
  const t = Math.floor(remainingMs.value / 1000)
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60
  const pad = (n) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
})
const timeLow = computed(() => remainingMs.value > 0 && remainingMs.value < 5 * 60 * 1000)

// ── 初始化 ──────────────────────────────────────────────────────────
async function init() {
  loading.value = true
  errorMsg.value = ''
  try {
    try {
      const { data } = await enterExam(aid)
      participation.value = data
      focusCount.value = data.focus_loss_count || 0
    } catch (e) {
      errorMsg.value = e.response?.data?.detail || '无法进入该作业'
      return
    }
    const { data } = await getPaper(aid)
    paper.value = data
    if (data.participation) {
      participation.value = data.participation
      focusCount.value = data.participation.focus_loss_count || 0
    }
    initAnswers()
    setupTimer()
    setupFocus()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

function initAnswers() {
  for (const q of paper.value.questions) {
    const my = q.my_answer
    if (q.qtype === 'single' || q.qtype === 'judge') {
      answers[q.id] = my && my.length ? String(my[0]) : ''
    } else if (q.qtype === 'multiple') {
      answers[q.id] = my ? [...my] : []
    } else if (q.qtype === 'fill') {
      const n = q.blank_count || (my ? my.length : 1) || 1
      const arr = Array(n).fill('')
      if (my) my.forEach((v, i) => { if (i < n) arr[i] = v })
      answers[q.id] = arr
    }
    if (q.correct !== undefined) {
      feedback[q.id] = { correct: q.correct, got_score: q.got_score, explanation: q.explanation }
    }
  }
}

async function save(q) {
  if (submitted.value) return
  saveState[q.id] = 'saving'
  try {
    const { data } = await submitAnswer(aid, q.id, answers[q.id])
    saveState[q.id] = 'saved'
    if (data.correct !== undefined) {
      feedback[q.id] = { correct: data.correct, got_score: data.got_score, explanation: data.explanation }
    }
  } catch {
    saveState[q.id] = ''
  }
}

function toggleMulti(q, key) {
  const arr = answers[q.id]
  const i = arr.indexOf(key)
  i >= 0 ? arr.splice(i, 1) : arr.push(key)
  save(q)
}

// ── 切屏监测 ────────────────────────────────────────────────────────
function onLeave() {
  if (!paper.value?.track_focus || !isExam.value || submitted.value) return
  reportFocusLoss(aid).then(({ data }) => { focusCount.value = data.focus_loss_count }).catch(() => {})
  focusWarn.value = true
  setTimeout(() => { focusWarn.value = false }, 4000)
}
function onVis() { if (document.hidden) onLeave() }
function setupFocus() {
  if (!paper.value?.track_focus || !isExam.value) return
  window.addEventListener('blur', onLeave)
  document.addEventListener('visibilitychange', onVis)
}
function teardownFocus() {
  window.removeEventListener('blur', onLeave)
  document.removeEventListener('visibilitychange', onVis)
}

// ── 交卷 ────────────────────────────────────────────────────────────
async function doSubmit(auto = false) {
  if (submitted.value || submitting.value) return
  if (!auto && !confirm(isExam.value ? '确认交卷？交卷后不能再修改。' : '提交并查看得分？')) return
  submitting.value = true
  try {
    const { data } = await submitExam(aid)
    result.value = data
    if (participation.value) participation.value.status = 'submitted'
    for (const q of data.questions) {
      feedback[q.id] = { correct: q.correct, got_score: q.got_score, explanation: q.explanation }
    }
    if (timer) { clearInterval(timer); timer = null }
    teardownFocus()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    alert(e.response?.data?.detail || '交卷失败')
  } finally {
    submitting.value = false
  }
}

function probHref(pid) { return `/problems/${pid}?assignment=${aid}` }
function fb(qid) { return feedback[qid] }

onMounted(init)
onUnmounted(() => { if (timer) clearInterval(timer); teardownFocus() })
</script>

<template>
  <div class="exam-page">
    <div v-if="loading" class="state-tip">加载中…</div>

    <div v-else-if="errorMsg" class="state-box">
      <p class="state-msg">{{ errorMsg }}</p>
      <button class="btn-secondary" @click="router.back()">← 返回</button>
    </div>

    <template v-else-if="paper">
      <!-- 顶栏 -->
      <div class="exam-bar">
        <button class="btn-back" @click="router.back()">←</button>
        <div class="bar-mid">
          <div class="bar-title">
            <span :class="['cat-tag', 'cat-' + paper.category]">{{ CAT_LABEL[paper.category] }}</span>
            {{ paper.title }}
          </div>
          <div class="bar-sub">
            满分 {{ paper.total_score }} · {{ paper.problems.length }} 编程 · {{ paper.questions.length }} 客观
          </div>
        </div>
        <div class="bar-right">
          <div v-if="isExam && paper.track_focus" class="focus-chip" :class="{ hot: focusCount > 0 }" title="切屏次数">
            👁 {{ focusCount }}
          </div>
          <div v-if="isExam && !submitted && remainingMs > 0" class="timer" :class="{ low: timeLow }">
            ⏱ {{ remainingText }}
          </div>
          <button v-if="!submitted" class="btn-submit" :disabled="submitting" @click="doSubmit(false)">
            {{ submitting ? '提交中…' : (isExam ? '交卷' : '提交') }}
          </button>
          <span v-else class="done-tag">已交卷</span>
        </div>
      </div>

      <Transition name="fade">
        <div v-if="focusWarn" class="focus-banner">⚠ 检测到切屏，已记录（第 {{ focusCount }} 次）</div>
      </Transition>

      <!-- 结果卡 -->
      <div v-if="result" class="result-card">
        <div class="rc-total">{{ result.total_score }}<span class="rc-max"> / {{ result.max_score }}</span></div>
        <div class="rc-break">客观 {{ result.objective_score }} · 编程 {{ result.programming_score }}</div>
      </div>
      <div v-else-if="submitted" class="result-card muted">已交卷，下方为你的作答</div>

      <!-- 客观题 -->
      <div v-if="paper.questions.length" class="sec">
        <div class="sec-title">客观题</div>
        <div v-for="(q, idx) in paper.questions" :key="q.id" class="q-card">
          <div class="q-head">
            <span class="q-idx">{{ idx + 1 }}</span>
            <span :class="['qt-tag', 'qt-' + q.qtype]">{{ q.qtype_display }}</span>
            <span class="q-title">{{ q.title }}</span>
            <span class="q-score">{{ q.score }} 分</span>
            <span v-if="saveState[q.id] === 'saved'" class="save-tag">已保存</span>
            <span v-else-if="saveState[q.id] === 'saving'" class="save-tag saving">保存中…</span>
          </div>
          <p v-if="q.content" class="q-content">{{ q.content }}</p>

          <!-- 单选 -->
          <div v-if="q.qtype === 'single'" class="opts">
            <label v-for="opt in q.options" :key="opt.key" class="opt-line" :class="{ chosen: answers[q.id] === opt.key }">
              <input type="radio" :name="'q' + q.id" :value="opt.key" v-model="answers[q.id]" :disabled="submitted" @change="save(q)" />
              <span class="ok">{{ opt.key }}</span><span>{{ opt.text }}</span>
            </label>
          </div>

          <!-- 多选 -->
          <div v-else-if="q.qtype === 'multiple'" class="opts">
            <label v-for="opt in q.options" :key="opt.key" class="opt-line" :class="{ chosen: answers[q.id].includes(opt.key) }">
              <input type="checkbox" :checked="answers[q.id].includes(opt.key)" :disabled="submitted" @change="toggleMulti(q, opt.key)" />
              <span class="ok">{{ opt.key }}</span><span>{{ opt.text }}</span>
            </label>
          </div>

          <!-- 判断 -->
          <div v-else-if="q.qtype === 'judge'" class="opts">
            <label class="opt-line" :class="{ chosen: answers[q.id] === 'T' }">
              <input type="radio" :name="'q' + q.id" value="T" v-model="answers[q.id]" :disabled="submitted" @change="save(q)" /> 正确（T）
            </label>
            <label class="opt-line" :class="{ chosen: answers[q.id] === 'F' }">
              <input type="radio" :name="'q' + q.id" value="F" v-model="answers[q.id]" :disabled="submitted" @change="save(q)" /> 错误（F）
            </label>
          </div>

          <!-- 填空 -->
          <div v-else-if="q.qtype === 'fill'" class="fills">
            <div v-for="(b, i) in answers[q.id]" :key="i" class="fill-row">
              <span class="fill-label">空 {{ i + 1 }}</span>
              <input v-model="answers[q.id][i]" class="fill-input" :disabled="submitted" @change="save(q)" placeholder="作答…" />
            </div>
          </div>

          <!-- 反馈（练习/作业即时，考试交卷后） -->
          <div v-if="fb(q.id)" class="q-fb" :class="fb(q.id).correct ? 'ok' : 'no'">
            {{ fb(q.id).correct ? '✓ 正确' : '✗ 错误' }} · 得 {{ fb(q.id).got_score }} / {{ q.score }}
            <span v-if="fb(q.id).explanation" class="fb-exp">　解析：{{ fb(q.id).explanation }}</span>
          </div>
        </div>
      </div>

      <!-- 编程题 -->
      <div v-if="paper.problems.length" class="sec">
        <div class="sec-title">编程题<span class="sec-hint">（点击进入做题页提交，提交自动计入本{{ CAT_LABEL[paper.category] }}）</span></div>
        <a v-for="p in paper.problems" :key="p.id" class="p-card" :class="{ ac: p.ac }" :href="probHref(p.id)" target="_blank">
          <span class="p-check">{{ p.ac ? '✓' : '○' }}</span>
          <span class="p-title">#{{ p.id }} {{ p.title }}</span>
          <span class="p-diff">{{ p.difficulty }}</span>
          <span class="p-score">{{ p.score }} 分</span>
          <span class="p-go">去做题 →</span>
        </a>
      </div>

      <!-- 底部交卷 -->
      <div v-if="!submitted" class="foot">
        <button class="btn-submit big" :disabled="submitting" @click="doSubmit(false)">
          {{ submitting ? '提交中…' : (isExam ? '交卷' : '提交并查看得分') }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.exam-page { max-width: 820px; margin: 0 auto; display: flex; flex-direction: column; gap: 1rem; padding-bottom: 3rem; }
.state-tip { text-align: center; padding: 4rem; color: var(--text-muted); }
.state-box { text-align: center; padding: 3rem; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
.state-msg { color: var(--text-secondary); font-size: 1rem; }

/* 顶栏 */
.exam-bar {
  position: sticky; top: 0; z-index: 50;
  display: flex; align-items: center; gap: 0.85rem;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 0.7rem 1rem; backdrop-filter: blur(6px);
}
.btn-back { background: none; border: 1px solid var(--border); color: var(--text-secondary); width: 2rem; height: 2rem; border-radius: 6px; cursor: pointer; flex-shrink: 0; }
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.bar-mid { flex: 1; min-width: 0; }
.bar-title { font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem; }
.bar-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.15rem; }
.bar-right { display: flex; align-items: center; gap: 0.6rem; flex-shrink: 0; }
.cat-tag { font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 4px; }
.cat-practice { background: rgba(100,100,100,0.12); color: var(--text-muted); border: 1px solid var(--border); }
.cat-homework { background: rgba(99,102,241,0.12); color: var(--accent); border: 1px solid rgba(99,102,241,0.3); }
.cat-exam { background: #ef444422; color: #f87171; border: 1px solid #ef444444; }
.timer { font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 700; color: var(--accent); padding: 0.2rem 0.6rem; border: 1px solid var(--border); border-radius: 6px; }
.timer.low { color: #f87171; border-color: #ef444466; animation: pulse 1s infinite; }
@keyframes pulse { 50% { opacity: 0.55; } }
.focus-chip { font-size: 0.8rem; color: var(--text-muted); }
.focus-chip.hot { color: #f87171; font-weight: 600; }
.btn-submit { background: var(--accent); color: #fff; border: none; padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: 0.5; cursor: default; }
.btn-submit.big { padding: 0.6rem 2.5rem; font-size: 0.95rem; }
.done-tag { font-size: 0.85rem; color: #10b981; font-weight: 600; }

.focus-banner { background: #ef444418; border: 1px solid #ef444455; color: #f87171; border-radius: 8px; padding: 0.6rem 1rem; font-size: 0.875rem; text-align: center; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 结果卡 */
.result-card { background: var(--bg-card); border: 1px solid var(--accent); border-radius: 10px; padding: 1.1rem 1.25rem; text-align: center; }
.result-card.muted { border-color: var(--border); color: var(--text-muted); font-size: 0.9rem; }
.rc-total { font-size: 2rem; font-weight: 800; color: var(--accent); line-height: 1.1; }
.rc-max { font-size: 1rem; color: var(--text-muted); font-weight: 500; }
.rc-break { font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem; }

/* 区块 */
.sec { display: flex; flex-direction: column; gap: 0.75rem; }
.sec-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
.sec-hint { font-size: 0.78rem; color: var(--text-muted); font-weight: 400; }

/* 客观题卡 */
.q-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; gap: 0.6rem; }
.q-head { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.q-idx { width: 1.5rem; height: 1.5rem; border-radius: 50%; background: var(--accent); color: #fff; font-size: 0.75rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.qt-tag { font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 10px; }
.qt-single { background: rgba(99,102,241,0.12); color: var(--accent); }
.qt-multiple { background: #8b5cf622; color: #a78bfa; }
.qt-judge { background: #10b98122; color: #10b981; }
.qt-fill { background: #f59e0b22; color: #f59e0b; }
.q-title { flex: 1; color: var(--text-primary); font-weight: 500; min-width: 8rem; }
.q-score { font-size: 0.8rem; color: var(--text-muted); }
.save-tag { font-size: 0.72rem; color: #10b981; }
.save-tag.saving { color: var(--text-muted); }
.q-content { font-size: 0.875rem; color: var(--text-secondary); white-space: pre-wrap; margin: 0; line-height: 1.6; }

.opts { display: flex; flex-direction: column; gap: 0.4rem; }
.opt-line { display: flex; align-items: center; gap: 0.5rem; padding: 0.45rem 0.6rem; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; font-size: 0.9rem; color: var(--text-secondary); }
.opt-line:hover { border-color: var(--accent); }
.opt-line.chosen { border-color: var(--accent); background: rgba(99,102,241,0.06); color: var(--text-primary); }
.opt-line input { accent-color: var(--accent); }
.ok { font-family: monospace; font-weight: 700; color: var(--accent); }

.fills { display: flex; flex-direction: column; gap: 0.5rem; }
.fill-row { display: flex; align-items: center; gap: 0.6rem; }
.fill-label { font-size: 0.8rem; color: var(--text-muted); width: 3rem; flex-shrink: 0; }
.fill-input { flex: 1; background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px; padding: 0.45rem 0.7rem; color: var(--text-primary); font-size: 0.9rem; }
.fill-input:focus { outline: none; border-color: var(--accent); }

.q-fb { font-size: 0.82rem; padding: 0.4rem 0.6rem; border-radius: 6px; }
.q-fb.ok { background: #10b98118; color: #10b981; }
.q-fb.no { background: #ef444418; color: #f87171; }
.fb-exp { color: var(--text-muted); }

/* 编程题卡 */
.p-card { display: flex; align-items: center; gap: 0.7rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 0.7rem 1rem; text-decoration: none; transition: border-color 0.15s; }
.p-card:hover { border-color: var(--accent); }
.p-check { width: 1.2rem; text-align: center; color: var(--text-muted); }
.p-card.ac .p-check { color: #10b981; }
.p-title { flex: 1; color: var(--text-primary); font-size: 0.9rem; }
.p-diff { font-size: 0.78rem; color: var(--text-muted); }
.p-score { font-size: 0.8rem; color: var(--text-muted); }
.p-go { font-size: 0.8rem; color: var(--accent); white-space: nowrap; }

.foot { display: flex; justify-content: center; padding-top: 0.5rem; }
</style>
