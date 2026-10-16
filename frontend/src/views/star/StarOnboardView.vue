<script setup>
// 画像采集：图形化问卷（一屏一题、图片选项）→ 引导对话（以选项为主，也可以自己打字）。
// 题型：single 单选 / multi 多选 / scale 打分表（色块、形状配 1–5 档表情）；带 other 的选项可以自己写几个字。
// 交上问卷后立刻换成学生自己选的界面颜色（见 starUi.js）。
import '@/assets/star.css'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StarHeader from '@/components/star/StarHeader.vue'
import FlowBar from '@/components/star/FlowBar.vue'
import { setStarUi, starMark, useStarTheme } from '@/components/star/starUi'
import { answerDialogue, getStarMe, submitSurvey } from '@/api/star'

const router = useRouter()
const { style: themeStyle } = useStarTheme()
const phase = ref('loading')     // loading | survey | dialogue | done
const nickname = ref('')
const questions = ref([])
const answers = ref({})
const qi = ref(0)
const dialogue = ref(null)
const history = ref([])
const input = ref('')
const busy = ref(false)
const error = ref('')

const q = computed(() => questions.value[qi.value])
const kind = (x) => x?.type || 'single'

// 形状题用的简单图形（线条 + 填色，和色块一样不靠文字也能认）
const SHAPE_SVG = {
  circle: '<circle cx="20" cy="20" r="15"/>',
  square: '<rect x="6" y="6" width="28" height="28"/>',
  rect: '<rect x="2" y="12" width="36" height="16" rx="3"/>',
  star: '<polygon points="20,3 25,15 38,15 27.5,23 31.5,36 20,28 8.5,36 12.5,23 2,15 15,15"/>',
  heart: '<path d="M20 35 C 6 25 2 17 6 10 C 10 4 17 5 20 11 C 23 5 30 4 34 10 C 38 17 34 25 20 35 Z"/>',
  triangle: '<polygon points="20,4 37,35 3,35"/>',
}

function isAnswered(x) {
  const v = answers.value[x.key]
  if (kind(x) === 'multi') return Array.isArray(v) && v.length > 0
  if (kind(x) === 'scale') return !!v && x.rows.every((r) => v[r.key] != null)
  return v != null && v !== ''
}

const answeredIdx = computed(() => questions.value.map((x, i) => (isAnswered(x) ? i : -1)).filter((i) => i >= 0))
const scaleLeft = computed(() => (kind(q.value) === 'scale'
  ? q.value.rows.filter((r) => answers.value[q.value.key]?.[r.key] == null).length : 0))

onMounted(async () => {
  try {
    const { data } = await getStarMe()
    nickname.value = data.nickname
    setStarUi(data.ui)
    if (data.status === 'pending' || data.status === 'confirmed') {
      router.replace({ name: 'star-home' })
      return
    }
    questions.value = data.survey || []
    if (data.survey_done && data.dialogue) {
      dialogue.value = data.dialogue
      phase.value = 'dialogue'
    } else {
      phase.value = 'survey'
    }
  } catch {
    error.value = '没有连上，请刷新一下。'
  }
})

function isOn(o) {
  const v = answers.value[q.value.key]
  return kind(q.value) === 'multi' ? (v || []).includes(o.value) : v === o.value
}

function choose(o) {
  const key = q.value.key
  if (kind(q.value) === 'multi') {
    const cur = answers.value[key] || []
    answers.value = { ...answers.value, [key]: cur.includes(o.value) ? cur.filter((x) => x !== o.value) : [...cur, o.value] }
  } else {
    answers.value = { ...answers.value, [key]: o.value }
  }
  error.value = ''
}

function rate(row, level) {
  const key = q.value.key
  answers.value = { ...answers.value, [key]: { ...answers.value[key], [row.key]: level.value } }
  error.value = ''
}

const otherChosen = computed(() => q.value?.options?.some((o) => o.other && isOn(o)))
const otherKey = computed(() => `${q.value.key}_other`)

async function next() {
  if (!isAnswered(q.value)) return
  if (qi.value < questions.value.length - 1) {
    qi.value += 1
    window.scrollTo(0, 0)
    return
  }
  busy.value = true
  try {
    const { data } = await submitSurvey(answers.value)
    setStarUi(data.ui)   // 立刻换成自己选的颜色和按钮
    dialogue.value = data.dialogue
    phase.value = 'dialogue'
  } catch (e) {
    error.value = e.response?.data?.detail || '没有提交上，请再按一次。'
  } finally {
    busy.value = false
  }
}

async function reply(text, via = 'text') {
  const t = (text ?? input.value).trim()
  if (!t || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const { data } = await answerDialogue(t, via)
    history.value.push({ ask: dialogue.value.ask, answer: t })
    input.value = ''
    if (data.done) {
      nickname.value = data.nickname || nickname.value
      phase.value = 'done'
    } else {
      dialogue.value = data.dialogue
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '没有发出去，请再试一次。'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="star-app" :style="themeStyle">
    <StarHeader :nickname="nickname" title="认识你" />
    <main class="star-main narrow">
      <p v-if="phase === 'loading' && !error" class="s-muted">正在打开……</p>

      <!-- 问卷：一屏一题 -->
      <template v-if="phase === 'survey' && q">
        <FlowBar :total="questions.length" :current="qi" :done="answeredIdx" unit="题" />
        <section class="s-card stack" :aria-label="q.title">
          <h1 class="s-title">{{ q.title }}</h1>
          <p v-if="kind(q) === 'multi'" class="s-sub">可以选好几个。</p>
          <p v-else-if="kind(q) === 'scale'" class="s-sub">每一行选一个。</p>

          <!-- 单选 / 多选 -->
          <div
            v-if="kind(q) !== 'scale'"
            class="grid-options"
            :role="kind(q) === 'multi' ? 'group' : 'radiogroup'"
            :aria-label="q.title"
          >
            <button
              v-for="o in q.options"
              :key="o.value"
              type="button"
              :role="kind(q) === 'multi' ? 'checkbox' : 'radio'"
              class="pic-option"
              :class="{ 'is-selected': isOn(o) }"
              :aria-checked="isOn(o)"
              @click="choose(o)"
            >
              <span v-if="o.swatch" class="swatch big" :style="{ background: o.swatch }" aria-hidden="true"></span>
              <span v-else class="pic" aria-hidden="true">{{ o.icon }}</span>
              <span class="pic-label">{{ o.label }}</span>
              <span v-if="isOn(o)" class="pic-check" aria-hidden="true">{{ starMark }}</span>
            </button>
          </div>
          <label v-if="otherChosen" class="other">
            <span>我想写：</span>
            <input
              v-model="answers[otherKey]"
              class="say-input"
              maxlength="20"
              placeholder="写几个字（可以不写）"
            >
          </label>

          <!-- 打分表：一行一个色块 / 形状 / 说法，每行选一档 -->
          <div v-else-if="kind(q) === 'scale'" class="scale">
            <div
              v-for="row in q.rows"
              :key="row.key"
              class="scale-row"
              :class="{ 'is-done': answers[q.key]?.[row.key] != null }"
              role="radiogroup"
              :aria-label="row.label"
            >
              <div class="scale-item">
                <span v-if="row.swatch" class="swatch" :style="{ background: row.swatch }" aria-hidden="true"></span>
                <svg
                  v-else-if="row.shape"
                  class="shape"
                  viewBox="0 0 40 40"
                  aria-hidden="true"
                  v-html="SHAPE_SVG[row.shape]"
                ></svg>
                <span v-else class="row-icon" aria-hidden="true">{{ row.icon }}</span>
                <span class="row-text">
                  <b>{{ row.label }}</b>
                  <small v-if="row.hint">{{ row.hint }}</small>
                </span>
              </div>
              <div class="levels">
                <button
                  v-for="lv in q.levels"
                  :key="lv.value"
                  type="button"
                  role="radio"
                  class="level"
                  :class="{ 'is-selected': answers[q.key]?.[row.key] === lv.value }"
                  :aria-checked="answers[q.key]?.[row.key] === lv.value"
                  :aria-label="`${row.label}：${lv.label}`"
                  @click="rate(row, lv)"
                >
                  <span class="face" aria-hidden="true">{{ lv.icon }}</span>
                  <span class="level-label">{{ lv.label }}</span>
                </button>
              </div>
            </div>
          </div>

          <div class="s-btn-row">
            <button type="button" class="s-btn s-btn-primary" :disabled="!isAnswered(q) || busy" @click="next">
              {{ qi < questions.length - 1 ? '下一题 →' : '完成问卷 ✓' }}
            </button>
            <button v-if="qi > 0" type="button" class="s-btn" @click="qi -= 1">← 上一题</button>
            <span v-if="scaleLeft" class="s-muted">还有 {{ scaleLeft }} 行没选</span>
          </div>
        </section>
      </template>

      <!-- 引导对话：选项为主，也可以自己打字 -->
      <template v-if="phase === 'dialogue' && dialogue">
        <FlowBar :total="dialogue.total" :current="dialogue.index" :done="history.map((_, i) => i)" unit="句" />
        <section class="s-card stack">
          <div v-for="(h, i) in history" :key="i" class="talk">
            <p class="bubble bot">{{ h.ask }}</p>
            <p class="bubble me">{{ h.answer }}</p>
          </div>
          <p class="bubble bot now">{{ dialogue.ask }}</p>
          <div v-if="dialogue.options?.length" class="s-btn-row">
            <button
              v-for="o in dialogue.options"
              :key="o"
              type="button"
              class="s-btn"
              :disabled="busy"
              @click="reply(o, 'option')"
            >{{ o }}</button>
          </div>
          <form class="say" @submit.prevent="reply()">
            <input v-model="input" class="say-input" maxlength="30" placeholder="也可以自己写" aria-label="我的回答">
            <button type="submit" class="s-btn s-btn-primary" :disabled="busy || !input.trim()">说好了</button>
          </form>
          <p v-if="busy && dialogue.index === dialogue.total - 1" class="s-muted">正在整理你的回答……</p>
        </section>
      </template>

      <section v-if="phase === 'done'" class="s-card stack done">
        <span class="big-icon" aria-hidden="true">🌟</span>
        <h1 class="s-title">谢谢{{ nickname }}！</h1>
        <p class="s-sub">老师会看你的回答，然后给你安排任务。</p>
        <div class="s-btn-row">
          <RouterLink class="s-btn s-btn-primary" :to="{ name: 'star-home' }">回到首页</RouterLink>
        </div>
      </section>

      <div v-if="error" class="s-feedback is-bad err" role="alert"><span class="s-fb-icon">⚠️</span>{{ error }}</div>
    </main>
  </div>
</template>

<style scoped>
.narrow { max-width: 860px; display: flex; flex-direction: column; gap: 20px; }
.stack { display: flex; flex-direction: column; gap: 18px; }
.grid-options { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 14px; }
.pic-option {
  position: relative;
  min-height: 140px;
  padding: 12px;
  border: 2px solid var(--s-border);
  border-radius: var(--s-radius-card, 8px);
  background: var(--s-card);
  font: inherit;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--s-text);
  text-align: center;
}
.pic-option:hover { border-color: var(--s-accent-ink, var(--s-accent)); }
.pic-option.is-selected { border: 3px solid var(--s-accent); background: var(--s-accent-soft); }
.pic { font-size: 56px; line-height: 1; }
.pic-label { font-size: 20px; font-weight: 600; line-height: 1.35; }
.pic-check { position: absolute; top: 8px; right: 12px; font-weight: 700; color: var(--s-accent-ink, var(--s-accent)); }

.swatch {
  display: inline-block;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 8px;
  border: 2px solid var(--s-border-strong);
}
.swatch.big { width: 64px; height: 64px; }

.other { display: flex; align-items: center; gap: 10px; font-weight: 600; }

.scale { display: flex; flex-direction: column; gap: 10px; }
.scale-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 12px;
  border: 2px solid var(--s-border);
  border-radius: var(--s-radius-card, 8px);
  flex-wrap: wrap;
}
.scale-row.is-done { border-color: var(--s-accent-ink, var(--s-accent)); }
.scale-item { display: flex; align-items: center; gap: 12px; min-width: 190px; flex: 1; }
.shape { width: 44px; height: 44px; flex-shrink: 0; fill: var(--s-accent-soft); stroke: var(--s-accent); stroke-width: 2.5; }
.row-icon { font-size: 36px; line-height: 1; width: 44px; text-align: center; }
.row-text { display: flex; flex-direction: column; line-height: 1.3; }
.row-text small { color: var(--s-text-2); font-size: 15px; }
.levels { display: flex; gap: 6px; flex-wrap: wrap; }
.level {
  min-width: 72px;
  min-height: 64px;
  padding: 4px 6px;
  border: 2px solid var(--s-border);
  border-radius: var(--s-radius-card, 8px);
  background: var(--s-card);
  color: var(--s-text);
  font: inherit;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.level:hover { border-color: var(--s-accent-ink, var(--s-accent)); }
.level.is-selected { border: 3px solid var(--s-accent); background: var(--s-accent-soft); }
.face { font-size: 28px; line-height: 1.1; }
.level-label { font-size: 14px; white-space: nowrap; }

.talk { display: flex; flex-direction: column; gap: 8px; }
.bubble {
  margin: 0;
  padding: 10px 16px;
  border-radius: 8px;
  max-width: 85%;
  border: 1px solid var(--s-border);
}
.bubble.bot { background: var(--s-bg); align-self: flex-start; }
.bubble.me { background: var(--s-accent-soft); border-color: var(--s-accent-ink, var(--s-accent)); align-self: flex-end; }
.bubble.now { font-size: 24px; font-weight: 600; }
.say { display: flex; gap: 10px; }
.say-input {
  flex: 1;
  min-width: 0;
  font: inherit;
  padding: 8px 14px;
  border: 2px solid var(--s-border-strong);
  border-radius: 6px;
  background: var(--s-card);
  color: var(--s-text);
}
.done { align-items: flex-start; }
.big-icon { font-size: 56px; line-height: 1; }
.s-btn-row a { text-decoration: none; }
.err { margin-top: 8px; }
@media (max-width: 600px) {
  .level { min-width: 56px; }
  .level-label { font-size: 12px; }
}
</style>
