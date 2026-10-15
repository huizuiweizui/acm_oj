<script setup>
// 画像采集：图形化问卷（一屏一题、图片选项）→ 引导对话（以选项为主，也可以自己打字）。
import '@/assets/star.css'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StarHeader from '@/components/star/StarHeader.vue'
import FlowBar from '@/components/star/FlowBar.vue'
import { answerDialogue, getStarMe, submitSurvey } from '@/api/star'

const router = useRouter()
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
const answeredIdx = computed(() => questions.value.map((x, i) => (answers.value[x.key] ? i : -1)).filter((i) => i >= 0))

onMounted(async () => {
  try {
    const { data } = await getStarMe()
    nickname.value = data.nickname
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

function choose(value) {
  answers.value = { ...answers.value, [q.value.key]: value }
  error.value = ''
}

async function next() {
  if (!answers.value[q.value.key]) return
  if (qi.value < questions.value.length - 1) {
    qi.value += 1
    return
  }
  busy.value = true
  try {
    const { data } = await submitSurvey(answers.value)
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
  <div class="star-app">
    <StarHeader :nickname="nickname" title="认识你" />
    <main class="star-main narrow">
      <p v-if="phase === 'loading' && !error" class="s-muted">正在打开……</p>

      <!-- 问卷：一屏一题 -->
      <template v-if="phase === 'survey' && q">
        <FlowBar :total="questions.length" :current="qi" :done="answeredIdx" unit="题" />
        <section class="s-card stack" :aria-label="q.title">
          <h1 class="s-title">{{ q.title }}</h1>
          <div class="grid-options" role="radiogroup" :aria-label="q.title">
            <button
              v-for="o in q.options"
              :key="o.value"
              type="button"
              role="radio"
              class="pic-option"
              :class="{ 'is-selected': answers[q.key] === o.value }"
              :aria-checked="answers[q.key] === o.value"
              @click="choose(o.value)"
            >
              <span class="pic" aria-hidden="true">{{ o.icon }}</span>
              <span class="pic-label">{{ o.label }}</span>
              <span v-if="answers[q.key] === o.value" class="pic-check" aria-hidden="true">✓</span>
            </button>
          </div>
          <div class="s-btn-row">
            <button type="button" class="s-btn s-btn-primary" :disabled="!answers[q.key] || busy" @click="next">
              {{ qi < questions.length - 1 ? '下一题 →' : '完成问卷 ✓' }}
            </button>
            <button v-if="qi > 0" type="button" class="s-btn" @click="qi -= 1">← 上一题</button>
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
.narrow { max-width: 820px; display: flex; flex-direction: column; gap: 20px; }
.stack { display: flex; flex-direction: column; gap: 18px; }
.grid-options { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 14px; }
.pic-option {
  position: relative;
  min-height: 140px;
  border: 2px solid var(--s-border);
  border-radius: 8px;
  background: var(--s-card);
  font: inherit;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--s-text);
}
.pic-option:hover { border-color: var(--s-accent); }
.pic-option.is-selected { border: 3px solid var(--s-accent); background: var(--s-accent-soft); }
.pic { font-size: 56px; line-height: 1; }
.pic-label { font-size: 22px; font-weight: 600; }
.pic-check { position: absolute; top: 8px; right: 12px; font-weight: 700; color: var(--s-accent); }
.talk { display: flex; flex-direction: column; gap: 8px; }
.bubble {
  margin: 0;
  padding: 10px 16px;
  border-radius: 8px;
  max-width: 85%;
  border: 1px solid var(--s-border);
}
.bubble.bot { background: var(--s-bg); align-self: flex-start; }
.bubble.me { background: var(--s-accent-soft); border-color: var(--s-accent); align-self: flex-end; }
.bubble.now { font-size: 24px; font-weight: 600; }
.say { display: flex; gap: 10px; }
.say-input {
  flex: 1;
  min-width: 0;
  font: inherit;
  padding: 8px 14px;
  border: 2px solid var(--s-border-strong);
  border-radius: 6px;
}
.done { align-items: flex-start; }
.big-icon { font-size: 56px; line-height: 1; }
.s-btn-row a { text-decoration: none; }
.err { margin-top: 8px; }
</style>
