<script setup>
import '@/assets/star.css'
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import StarHeader from '@/components/star/StarHeader.vue'
import LevelPlayer from '@/components/star/LevelPlayer.vue'
import StepsPlayer from '@/components/star/StepsPlayer.vue'
import StarAssistant from '@/components/star/StarAssistant.vue'
import { getMyTask, getStarMe } from '@/api/star'

const route = useRoute()
const task = ref(null)
const nickname = ref('')
const step = ref(0)
const finished = ref(false)
const levelSolved = ref(false)
const error = ref('')

async function load() {
  task.value = null
  error.value = ''
  finished.value = false
  levelSolved.value = false
  step.value = 0
  try {
    const [t, me] = await Promise.all([getMyTask(route.params.id), getStarMe()])
    task.value = t.data
    nickname.value = me.data.nickname
    levelSolved.value = t.data.done
  } catch (e) {
    error.value = e.response?.status === 404 ? '没有找到这个任务。' : '没有连上，请刷新一下。'
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <div class="star-app">
    <StarHeader :nickname="nickname" :title="task ? task.content.title : ''" />
    <main class="star-main">
      <div v-if="error" class="s-feedback is-bad" role="alert">
        <span class="s-fb-icon">⚠️</span>{{ error }}
        <RouterLink :to="{ name: 'star-home' }" class="back">回到任务列表</RouterLink>
      </div>
      <p v-else-if="!task" class="s-muted">正在打开……</p>

      <template v-else>
        <div class="task-top">
          <RouterLink :to="{ name: 'star-home' }" class="s-btn back-btn">← 任务列表</RouterLink>
          <span class="s-muted">任务 {{ task.position }} / {{ task.tasks_total }}</span>
        </div>

        <section v-if="finished" class="s-card done">
          <span class="big-icon" aria-hidden="true">🌟</span>
          <div>
            <h1 class="s-title">任务完成了！</h1>
            <p class="s-sub">「{{ task.content.title }}」做完了。</p>
          </div>
          <div class="s-btn-row">
            <RouterLink
              v-if="task.next_task_id"
              class="s-btn s-btn-primary"
              :to="{ name: 'star-task', params: { id: task.next_task_id } }"
            >下一个任务 →</RouterLink>
            <RouterLink class="s-btn" :class="{ 's-btn-primary': !task.next_task_id }" :to="{ name: 'star-home' }">
              回到任务列表
            </RouterLink>
          </div>
        </section>

        <template v-else-if="task.content.kind === 'level'">
          <h1 class="s-title">{{ task.content.title }}</h1>
          <LevelPlayer
            :task-id="task.id"
            :level="task.content"
            :solved="levelSolved"
            @solved="levelSolved = true"
          />
          <div v-if="levelSolved" class="s-btn-row after-level">
            <button type="button" class="s-btn s-btn-primary" @click="finished = true">完成这一关 ✓</button>
          </div>
        </template>

        <StepsPlayer
          v-else
          :task-id="task.id"
          :content="task.content"
          :done-steps="task.done_steps"
          @step-change="step = $event"
          @done="finished = true"
        />
      </template>
    </main>
    <StarAssistant v-if="task" :nickname="nickname" :task-id="task.id" :step="step" />
  </div>
</template>

<style scoped>
.task-top { display: flex; align-items: center; gap: 16px; margin-bottom: 18px; }
.back-btn { text-decoration: none; min-height: 44px; font-size: 17px; }
.done { display: flex; flex-direction: column; gap: 16px; align-items: flex-start; }
.big-icon { font-size: 56px; line-height: 1; }
.after-level { margin-top: 24px; }
.s-btn-row a { text-decoration: none; }
.back { margin-left: auto; }
</style>
