<script setup>
// 启蒙层：指令卡片闯关。
// 点一下卡片放进下一个空卡槽，也可以拖到指定卡槽；点卡槽里的卡片把它拿走。
// 按「运行」后用与后端同一套规则（maze.js）逐格播放，播完再交给后端判定并记录。
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import LevelBoard from './LevelBoard.vue'
import { clampTimes, firstDiff, REPEAT_MAX, REPEAT_MIN, simulate } from './maze'
import { getHint, submitAttempt } from '@/api/star'

const props = defineProps({
  taskId: { type: Number, required: true },
  level: { type: Object, required: true },
  solved: { type: Boolean, default: false },
})
const emit = defineEmits(['solved'])

const CARD = {
  forward: { icon: '⬆', label: '前进' },
  left: { icon: '↺', label: '左转' },
  right: { icon: '↻', label: '右转' },
  repeat: { icon: '🔁', label: '重复' },
}
const STEP_MS = 650

const program = ref([])
const pos = ref({ ...props.level.start })
const trail = ref([])
const bump = ref(false)
const running = ref(false)
const activeCard = ref(-1)
const activeRep = ref(0)
const feedback = ref(null)
const hintLevel = ref(0)
const hintText = ref('')
const highlightSlot = ref(-1)
const highlightType = ref('')
const submitting = ref(false)
let timer = null
let startedAt = Date.now()

const slots = computed(() => props.level.slots)
const full = computed(() => program.value.length >= slots.value)
const repeatTarget = computed(() => {
  // 正在执行的卡片前面若是一张重复卡，两张一起高亮
  const i = activeCard.value
  return i > 0 && program.value[i - 1]?.type === 'repeat' ? i - 1 : -1
})

watch(() => props.taskId, () => reset(true))
onBeforeUnmount(stopTimer)

function stopTimer() {
  if (timer) { clearInterval(timer); timer = null }
}

function clearRun() {
  stopTimer()
  running.value = false
  pos.value = { ...props.level.start }
  trail.value = []
  bump.value = false
  activeCard.value = -1
  activeRep.value = 0
  feedback.value = null
}

function reset(all = false) {
  clearRun()
  if (all) {
    program.value = []
    hintLevel.value = 0
    hintText.value = ''
    startedAt = Date.now()
  }
  highlightSlot.value = -1
  highlightType.value = ''
}

function edited() {
  clearRun()
  highlightSlot.value = -1
  highlightType.value = ''
}

function addCard(type, at = null) {
  if (running.value || full.value) return
  const card = type === 'repeat' ? { type, times: REPEAT_MIN } : { type }
  if (at === null || at >= program.value.length) program.value.push(card)
  else program.value.splice(at, 0, card)
  edited()
}

function removeCard(i) {
  if (running.value) return
  program.value.splice(i, 1)
  edited()
}

function clearAll() {
  if (running.value) return
  program.value = []
  edited()
}

function changeTimes(i, delta) {
  if (running.value) return
  const c = program.value[i]
  c.times = clampTimes((c.times || REPEAT_MIN) + delta)
  edited()
}

// ── 拖拽 ──
function onPaletteDrag(e, type) {
  e.dataTransfer.setData('text/plain', `new:${type}`)
}
function onSlotDrag(e, i) {
  e.dataTransfer.setData('text/plain', `move:${i}`)
}
function onDrop(e, at) {
  if (running.value) return
  const data = e.dataTransfer.getData('text/plain') || ''
  if (data.startsWith('new:')) {
    addCard(data.slice(4), at)
  } else if (data.startsWith('move:')) {
    const from = Number(data.slice(5))
    if (Number.isNaN(from) || from === at) return
    const [card] = program.value.splice(from, 1)
    program.value.splice(Math.min(at, program.value.length), 0, card)
    edited()
  }
}

// ── 运行 ──
function play(prog) {
  const sim = simulate(props.level, prog)
  running.value = true
  return new Promise((resolve) => {
    let k = 0
    timer = setInterval(() => {
      k += 1
      if (k >= sim.frames.length) {
        stopTimer()
        running.value = false
        resolve(sim)
        return
      }
      const f = sim.frames[k]
      pos.value = { x: f.x, y: f.y, dir: f.dir }
      if (!trail.value.includes(`${f.x},${f.y}`)) trail.value.push(`${f.x},${f.y}`)
      activeCard.value = f.card
      activeRep.value = f.rep
      if (k === sim.frames.length - 1 && (sim.result === 'wall' || sim.result === 'out')) bump.value = true
    }, STEP_MS)
  })
}

async function run() {
  if (running.value || submitting.value || !program.value.length) return
  clearRun()
  const prog = program.value.map((c) => ({ ...c }))
  await play(prog)
  submitting.value = true
  try {
    const { data } = await submitAttempt(props.taskId, {
      step: 0,
      answer: { program: prog },
      hint_level: hintLevel.value,
      duration_ms: Date.now() - startedAt,
    })
    feedback.value = {
      ...data.feedback,
      ok: data.correct,
      extra: data.correct && data.shortest && data.cards_used > data.shortest
        ? `用了 ${data.cards_used} 张卡片，最少要 ${data.shortest} 张。` : '',
    }
    startedAt = Date.now()
    if (data.correct) emit('solved', data)
  } catch (e) {
    feedback.value = { icon: '⚠️', text: e.response?.data?.detail || '没有连上，请再按一次运行。', ok: false }
  } finally {
    submitting.value = false
  }
}

// ── 三级提示：高亮下一张卡片 → 代为放置前半段 → 完整示范 ──
async function askHint() {
  if (hintLevel.value >= 3 || running.value) return
  const next = hintLevel.value + 1
  let data
  try {
    ({ data } = await getHint(props.taskId, 0, next))
  } catch {
    hintText.value = '提示没有拿到，请再点一次。'
    return
  }
  hintLevel.value = next
  hintText.value = data.text
  const sol = data.solution || []
  clearRun()
  if (data.action === 'highlight') {
    const i = firstDiff(program.value, sol)
    if (i >= 0) {
      highlightSlot.value = i
      highlightType.value = sol[i].type
    } else {
      hintText.value = '卡片都对了，按「运行」。'
    }
  } else if (data.action === 'place') {
    program.value = sol.slice(0, data.place_count).map((c) => ({ ...c }))
    highlightSlot.value = program.value.length < sol.length ? program.value.length : -1
    highlightType.value = ''
  } else if (data.action === 'demo') {
    program.value = sol.map((c) => ({ ...c }))
    highlightSlot.value = -1
    highlightType.value = ''
    await play(program.value.map((c) => ({ ...c })))
    hintText.value = '这是完整的走法。现在按「运行」试一试。'
    pos.value = { ...props.level.start }
    trail.value = []
    activeCard.value = -1
  }
}
</script>

<template>
  <div class="level">
    <div class="level-left">
      <div class="story">
        <p v-for="(s, i) in level.story" :key="i">{{ s }}</p>
      </div>
      <LevelBoard :level="level" :pos="pos" :trail="trail" :bump="bump" />
      <p class="s-muted legend">
        <span>{{ level.theme?.hero }} 是你</span>
        <span>{{ level.theme?.goal }} 是终点</span>
        <span v-if="level.walls?.length">{{ level.theme?.wall }} 不能走</span>
      </p>
    </div>

    <div class="level-right">
      <section aria-labelledby="palette-title">
        <h3 id="palette-title" class="sec-title">卡片</h3>
        <div class="palette">
          <button
            v-for="type in level.cards"
            :key="type"
            type="button"
            class="card-btn"
            :class="{ 'is-hint': highlightType === type }"
            :disabled="running || full"
            draggable="true"
            @dragstart="onPaletteDrag($event, type)"
            @click="addCard(type)"
          >
            <span class="card-icon" aria-hidden="true">{{ CARD[type].icon }}</span>
            {{ CARD[type].label }}
          </button>
        </div>
        <p v-if="level.cards.includes('repeat')" class="s-muted">
          🔁 重复卡：让它<b>后面的那一张</b>卡片做好几次。
        </p>
      </section>

      <section aria-labelledby="slots-title">
        <h3 id="slots-title" class="sec-title">我的卡槽（{{ program.length }} / {{ slots }}）</h3>
        <ol class="slots">
          <li
            v-for="i in slots"
            :key="i"
            class="slot"
            :class="{
              'is-filled': program[i - 1],
              'is-active': activeCard === i - 1 || repeatTarget === i - 1,
              'is-hint': highlightSlot === i - 1,
            }"
            @dragover.prevent
            @drop.prevent="onDrop($event, i - 1)"
          >
            <span class="slot-no">{{ i }}</span>
            <template v-if="program[i - 1]">
              <button
                type="button"
                class="slot-card"
                draggable="true"
                :disabled="running"
                :aria-label="`第 ${i} 张：${CARD[program[i - 1].type].label}，点一下拿走`"
                @dragstart="onSlotDrag($event, i - 1)"
                @click="removeCard(i - 1)"
              >
                <span aria-hidden="true">{{ CARD[program[i - 1].type].icon }}</span>
                {{ CARD[program[i - 1].type].label }}
              </button>
              <span v-if="program[i - 1].type === 'repeat'" class="times">
                <button type="button" class="times-btn" :disabled="running || program[i - 1].times <= 2"
                        aria-label="少重复一次" @click="changeTimes(i - 1, -1)">−</button>
                <b>{{ program[i - 1].times }} 次</b>
                <button type="button" class="times-btn" :disabled="running || program[i - 1].times >= REPEAT_MAX"
                        aria-label="多重复一次" @click="changeTimes(i - 1, 1)">+</button>
              </span>
              <span v-if="activeCard === i - 1 && activeRep" class="rep-badge">第 {{ activeRep }} 次</span>
            </template>
            <span v-else class="slot-empty">空</span>
          </li>
        </ol>
      </section>

      <div class="s-btn-row">
        <button type="button" class="s-btn s-btn-primary" :disabled="running || submitting || !program.length" @click="run">
          ▶ 运行
        </button>
        <button type="button" class="s-btn" :disabled="running || !program.length" @click="clearAll">
          清空
        </button>
        <button type="button" class="s-btn" :disabled="running || hintLevel >= 3" @click="askHint">
          💡 提示（{{ hintLevel }} / 3）
        </button>
      </div>

      <p v-if="solved && !feedback" class="s-muted">✅ 这一关已经通过了，可以再玩一次。</p>
      <p v-if="hintText" class="s-hint">💡 {{ hintText }}</p>

      <div v-if="running" class="s-feedback" role="status">
        <span class="s-fb-icon" aria-hidden="true">👀</span>正在走……
      </div>
      <div v-else-if="feedback" class="s-feedback" :class="feedback.ok ? 'is-ok' : 'is-bad'" role="status">
        <span class="s-fb-icon" aria-hidden="true">{{ feedback.icon }}</span>
        <span>{{ feedback.text }}<br v-if="feedback.extra"><small v-if="feedback.extra">{{ feedback.extra }}</small></span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.level {
  display: grid;
  grid-template-columns: minmax(0, auto) minmax(320px, 1fr);
  gap: 32px;
  align-items: start;
}
@media (max-width: 900px) {
  .level { grid-template-columns: 1fr; }
}
.level-left { display: flex; flex-direction: column; gap: 14px; }
.level-right { display: flex; flex-direction: column; gap: 20px; }
.story p { margin: 0; font-size: 22px; font-weight: 600; }
.legend { display: flex; gap: 18px; flex-wrap: wrap; margin: 0; }
.sec-title { font-size: 18px; margin: 0 0 10px; color: var(--s-text-2); }

.palette { display: flex; gap: 12px; flex-wrap: wrap; }
.card-btn {
  min-width: 112px;
  min-height: 64px;
  border: 2px solid var(--s-border-strong);
  border-radius: 8px;
  background: var(--s-card);
  font: inherit;
  font-weight: 700;
  cursor: grab;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 14px;
  color: var(--s-text);
}
.card-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.card-btn.is-hint, .slot.is-hint { outline: 4px solid var(--s-warn); outline-offset: 2px; }
.card-icon { font-size: 26px; }

.slots {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.slot {
  min-height: 60px;
  border: 2px dashed var(--s-border-strong);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: #fbfaf6;
}
.slot.is-filled { border-style: solid; background: var(--s-card); }
.slot.is-active { border-color: var(--s-accent-ink, var(--s-accent)); background: var(--s-accent-soft); }
.slot-no {
  width: 28px;
  font-family: var(--font-mono);
  font-size: 16px;
  color: var(--s-text-2);
  text-align: right;
}
.slot-empty { color: var(--s-text-2); font-size: 16px; }
.slot-card {
  border: none;
  background: transparent;
  font: inherit;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--s-text);
  padding: 6px 4px;
}
.times { display: inline-flex; align-items: center; gap: 8px; margin-left: auto; }
.times-btn {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  border: 2px solid var(--s-border-strong);
  background: var(--s-card);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.times-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.rep-badge {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  background: var(--s-accent);
  border-radius: 6px;
  padding: 2px 8px;
}
.s-feedback small { font-weight: 400; color: var(--s-text-2); }
</style>
