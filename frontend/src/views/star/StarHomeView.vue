<script setup>
import '@/assets/star.css'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import StarHeader from '@/components/star/StarHeader.vue'
import { setStarUi, useStarTheme } from '@/components/star/starUi'
import { getMyTasks, getStarMe } from '@/api/star'

const router = useRouter()
const { style: themeStyle } = useStarTheme()
const me = ref(null)
const tasks = ref([])
const loading = ref(true)
const error = ref('')

const nextId = computed(() => tasks.value.find((t) => !t.done)?.id)
const doneCount = computed(() => tasks.value.filter((t) => t.done).length)

function progressText(t) {
  if (t.done) return '✅ 完成了'
  if (t.done_steps.length) return `做到第 ${t.done_steps.length + 1} 步`
  return '还没开始'
}

onMounted(async () => {
  try {
    const { data } = await getStarMe()
    me.value = data
    setStarUi(data.ui)
    const fresh = data.status === 'new' || data.status === 'surveying'
    if (fresh && !data.is_teacher) {
      router.replace({ name: 'star-start' })
      return
    }
    if (!fresh) tasks.value = (await getMyTasks()).data
  } catch {
    error.value = '没有连上，请刷新一下。'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="star-app" :style="themeStyle">
    <StarHeader :nickname="me?.nickname" />
    <main class="star-main">
      <p v-if="loading" class="s-muted">正在打开……</p>
      <div v-else-if="error" class="s-feedback is-bad" role="alert"><span class="s-fb-icon">⚠️</span>{{ error }}</div>

      <!-- 教师第一次进入：去教师端，或者以学生身份体验一遍 -->
      <section v-else-if="me.is_teacher && (me.status === 'new' || me.status === 'surveying')" class="s-card stack">
        <h1 class="s-title">星语 · 编程学伴</h1>
        <p class="s-sub">您是教师账号。可以去教师端管理学生，也可以先以学生身份体验问卷和学习流程。</p>
        <div class="s-btn-row">
          <RouterLink class="s-btn s-btn-primary" :to="{ name: 'star-teacher' }">进入教师端</RouterLink>
          <RouterLink class="s-btn" :to="{ name: 'star-start' }">以学生身份体验</RouterLink>
        </div>
      </section>

      <template v-else>
        <section v-if="me.status === 'pending'" class="s-card stack wait">
          <span class="big-icon" aria-hidden="true">⏳</span>
          <div>
            <h1 class="s-title">老师正在看你的回答</h1>
            <p class="s-sub">看完以后，这里会出现你的任务。</p>
          </div>
        </section>

        <section v-if="tasks.length" class="stack">
          <div class="list-head">
            <h1 class="s-title">{{ me.nickname }}的任务</h1>
            <p class="s-sub">完成了 {{ doneCount }} 个，一共 {{ tasks.length }} 个。</p>
          </div>
          <ol class="task-list">
            <li v-for="(t, i) in tasks" :key="t.id" class="s-card task" :class="{ 'is-next': t.id === nextId }">
              <span class="task-no">{{ i + 1 }}</span>
              <span class="task-icon" aria-hidden="true">{{ t.kind === 'level' ? '🧩' : '📝' }}</span>
              <div class="task-main">
                <b class="task-title">{{ t.title }}</b>
                <span class="s-muted">
                  {{ t.kind === 'level' ? '卡片闯关' : `分步学习 · 共 ${t.steps_total} 步` }} · {{ progressText(t) }}
                </span>
              </div>
              <span v-if="t.id === nextId" class="next-tag">下一个</span>
              <RouterLink
                class="s-btn"
                :class="{ 's-btn-primary': t.id === nextId }"
                :to="{ name: 'star-task', params: { id: t.id } }"
              >{{ t.done ? '再做一次' : t.done_steps.length ? '继续' : '开始' }}</RouterLink>
            </li>
          </ol>
        </section>

        <section v-else-if="me.status === 'confirmed'" class="s-card">
          <h1 class="s-title">还没有任务</h1>
          <p class="s-sub">老师还没有给你安排任务。</p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 16px; }
.wait { flex-direction: row; align-items: center; gap: 24px; margin-bottom: 24px; }
.big-icon { font-size: 56px; line-height: 1; }
.list-head .s-title { margin-bottom: 0; }
.task-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }
.task { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 18px; padding: 16px 20px; }
.task.is-next { border: 2px solid var(--s-accent); }
.task-no {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 6px;
  background: var(--s-bg);
  border: 2px solid var(--s-border-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-weight: 700;
}
.task-icon { font-size: 32px; }
.task-main { display: flex; flex-direction: column; flex: 1 1 220px; min-width: 0; }
.task-title { font-size: 22px; }
.next-tag {
  margin-left: auto;
  font-weight: 700;
  color: var(--s-accent-ink, var(--s-accent));
  white-space: nowrap;
}
.task .s-btn { text-decoration: none; white-space: nowrap; }
.task:not(.is-next) .s-btn { margin-left: auto; }
</style>
