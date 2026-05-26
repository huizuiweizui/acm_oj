<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getContest, registerContest } from '@/api/contests'
import { useUserStore } from '@/stores/user'
import DifficultyBadge from '@/components/DifficultyBadge.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const contest = ref(null)
const problems = ref([])
const isRegistered = ref(false)
const participantCount = ref(0)
const loading = ref(true)
const registering = ref(false)
const regMsg = ref('')

const statusCfg = {
  running:  { label: '进行中', color: '#2ecc71' },
  upcoming: { label: '即将开始', color: '#3498db' },
  ended:    { label: '已结束', color: '#888' },
}
const statusIconMap = { ac: '✓', tried: '?', todo: '' }
const statusColorMap = { ac: '#2ecc71', tried: '#f39c12', todo: 'transparent' }

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

async function fetchContest() {
  loading.value = true
  try {
    const { data } = await getContest(route.params.id)
    contest.value = data.contest
    problems.value = data.problems
    isRegistered.value = data.is_registered
    participantCount.value = data.participant_count
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!userStore.isLoggedIn) {
    router.push(`/login?next=/contests/${route.params.id}`)
    return
  }
  registering.value = true
  regMsg.value = ''
  try {
    const { data } = await registerContest(route.params.id)
    isRegistered.value = true
    participantCount.value += 1
    regMsg.value = data.detail
  } catch (e) {
    regMsg.value = e.response?.data?.detail || '报名失败'
  } finally {
    registering.value = false
  }
}

onMounted(fetchContest)
</script>

<template>
  <div class="contest-detail" v-if="!loading && contest">
    <!-- 头部信息 -->
    <div class="contest-header">
      <div class="header-main">
        <h1 class="contest-title">{{ contest.title }}</h1>
        <div class="meta-row">
          <span class="rule-badge">{{ contest.rule_type }}</span>
          <span
            class="status-badge"
            :style="{ color: statusCfg[contest.status]?.color, borderColor: statusCfg[contest.status]?.color }"
          >{{ statusCfg[contest.status]?.label }}</span>
          <span class="meta-text">{{ participantCount }} 人参赛</span>
        </div>
        <div class="time-info">
          <span>开始：{{ formatTime(contest.start_time) }}</span>
          <span class="sep">|</span>
          <span>结束：{{ formatTime(contest.end_time) }}</span>
        </div>
        <p v-if="contest.description" class="desc">{{ contest.description }}</p>
      </div>

      <div class="header-action">
        <button class="btn-rank" @click="router.push(`/contests/${contest.id}/rank`)">
          排行榜
        </button>
        <template v-if="contest.status !== 'ended'">
          <div v-if="isRegistered" class="reg-ok">✓ 已报名</div>
          <button
            v-else
            class="btn-register"
            :disabled="registering"
            @click="handleRegister"
          >{{ registering ? '报名中...' : '立即报名' }}</button>
          <div v-if="regMsg" class="reg-msg">{{ regMsg }}</div>
        </template>
      </div>
    </div>

    <!-- 题目列表 -->
    <div class="section-title">题目列表</div>
    <div class="table-wrap">
      <table class="problem-table">
        <thead>
          <tr>
            <th width="48"></th>
            <th width="60">编号</th>
            <th>题目名称</th>
            <th width="160">难度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in problems" :key="p.problem_id">
            <td class="status-cell">
              <span
                class="status-dot"
                :style="{ background: statusColorMap[p.user_status] }"
              >{{ statusIconMap[p.user_status] }}</span>
            </td>
            <td class="label-cell">{{ p.label }}</td>
            <td>
              <RouterLink
                :to="`/problems/${p.problem_id}?contest_id=${contest.id}`"
                class="problem-link"
              >{{ p.title }}</RouterLink>
            </td>
            <td><DifficultyBadge :difficulty="p.difficulty" /></td>
          </tr>
          <tr v-if="problems.length === 0">
            <td colspan="4" class="empty">暂无题目</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div v-else-if="loading" class="loading">加载中...</div>
</template>

<style scoped>
.contest-detail { padding: 0.5rem 0; }
.loading { text-align: center; padding: 4rem; color: #888; }

.contest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: #16162a;
  border: 1px solid #2d2d4e;
  border-radius: 10px;
  padding: 1.8rem 2rem;
  margin-bottom: 1.8rem;
  gap: 1.5rem;
}
.header-main { flex: 1; }
.contest-title { font-size: 1.5rem; font-weight: 700; color: #e0e0f0; margin: 0 0 0.75rem; }

.meta-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.rule-badge {
  background: #1e1e38; border: 1px solid #3d3d5c;
  color: #a78bfa; padding: 0.15rem 0.55rem;
  border-radius: 4px; font-size: 0.78rem; font-weight: 600;
}
.status-badge {
  font-size: 0.82rem; font-weight: 600;
  border: 1px solid; padding: 0.15rem 0.55rem; border-radius: 4px;
}
.meta-text { color: #888; font-size: 0.85rem; }

.time-info { font-size: 0.85rem; color: #888; margin-bottom: 0.75rem; }
.sep { margin: 0 0.5rem; }
.desc { color: #a0a0c0; font-size: 0.9rem; line-height: 1.6; margin: 0.75rem 0 0; }

.header-action { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; flex-shrink: 0; }
.reg-ok { color: #2ecc71; font-weight: 600; font-size: 0.95rem; }
.btn-register {
  padding: 0.6rem 1.6rem; background: #7c6af7; color: #fff;
  border: none; border-radius: 7px; font-size: 0.95rem; font-weight: 600;
  cursor: pointer;
}
.btn-register:hover:not(:disabled) { background: #6c5ae7; }
.btn-register:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-rank {
  padding: 0.45rem 1.2rem; background: transparent;
  border: 1px solid #3d3d5c; color: #a78bfa;
  border-radius: 7px; font-size: 0.88rem; font-weight: 600;
  cursor: pointer; transition: border-color 0.15s;
}
.btn-rank:hover { border-color: #7c6af7; }
.reg-msg { font-size: 0.82rem; color: #a0a0c0; }

.section-title { font-size: 1.1rem; font-weight: 700; color: #e0e0f0; margin-bottom: 0.9rem; }

.table-wrap { background: #16162a; border-radius: 8px; border: 1px solid #2d2d4e; overflow: hidden; }
.problem-table { width: 100%; border-collapse: collapse; }
.problem-table th {
  padding: 0.7rem 1rem; text-align: left;
  font-size: 0.8rem; color: #888; background: #1a1a30;
  border-bottom: 1px solid #2d2d4e;
}
.problem-table td { padding: 0.7rem 1rem; border-bottom: 1px solid #1e1e38; }
.problem-table tr:last-child td { border-bottom: none; }
.problem-table tr:hover td { background: #1c1c35; }

.status-cell { text-align: center; }
.status-dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  font-size: 0.7rem; font-weight: 700; color: #fff;
}
.label-cell { font-weight: 700; color: #a78bfa; }
.problem-link { color: #a0c4ff; text-decoration: none; }
.problem-link:hover { color: #7c6af7; text-decoration: underline; }
.empty { text-align: center; padding: 2rem; color: #666; }
</style>
