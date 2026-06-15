<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getContestRank, finalizeRating } from '@/api/contests'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()

const contest = ref(null)
const problemLabels = ref([])
const rankedUsers = ref([])
const ruleType = ref('ICPC')
const frozen = ref(false)
const loading = ref(true)
const lastUpdated = ref(null)
let timer = null

async function fetchRank() {
  try {
    const { data } = await getContestRank(route.params.id)
    contest.value = data.contest
    problemLabels.value = data.problem_labels
    rankedUsers.value = data.ranked_users
    ruleType.value = data.rule_type || data.contest?.rule_type || 'ICPC'
    frozen.value = !!data.frozen
    lastUpdated.value = new Date()
  } finally {
    loading.value = false
  }
}

const userStore = useUserStore()
const finalizing = ref(false)
const finalizeMsg = ref('')

const isRunning = computed(() => contest.value?.status === 'running')
const isIOI = computed(() => ruleType.value === 'IOI')
const isEnded = computed(() => contest.value?.status === 'ended')
const canFinalize = computed(() => {
  if (!isEnded.value || contest.value?.rating_applied) return false
  const u = userStore.user
  return !!u && (u.role === 'admin' || u.username === contest.value?.created_by_username)
})
async function doFinalize() {
  if (!confirm('结算本场比赛 Rating？结算后不可撤销。')) return
  finalizing.value = true
  try {
    const { data } = await finalizeRating(route.params.id)
    finalizeMsg.value = `已结算 ${data.count} 人的 Rating`
    await fetchRank()
  } catch (e) {
    finalizeMsg.value = e.response?.data?.detail || '结算失败'
  } finally {
    finalizing.value = false
  }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatPenalty(min) {
  if (!min) return '0'
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}h${m}m` : `${m}m`
}

onMounted(async () => {
  await fetchRank()
  if (isRunning.value) {
    timer = setInterval(fetchRank, 30000)
  }
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>

  <div v-else-if="contest" class="ranking-page">

    <!-- 头部 -->
    <div class="page-header">
      <div class="header-left">
        <div class="back-link" @click="router.push(`/contests/${contest.id}`)">← 返回比赛</div>
        <h1 class="page-title">{{ contest.title }} · 排行榜</h1>
        <div class="meta-row">
          <span class="rule-badge">{{ contest.rule_type }}</span>
          <span v-if="isRunning" class="live-badge">LIVE</span>
          <span class="meta-time">{{ formatTime(contest.start_time) }} — {{ formatTime(contest.end_time) }}</span>
        </div>
      </div>
      <div class="header-right" v-if="lastUpdated">
        <div class="update-info">
          <span v-if="isRunning" class="refresh-dot"></span>
          {{ isRunning ? '每 30 秒自动刷新' : '比赛已结束' }}
        </div>
        <div class="update-time">更新于 {{ lastUpdated.toLocaleTimeString('zh-CN') }}</div>
      </div>
    </div>

    <div v-if="canFinalize || finalizeMsg" style="display:flex;align-items:center;gap:1rem;justify-content:flex-end;margin-bottom:1rem">
      <span v-if="finalizeMsg" style="font-size:0.85rem;color:#10b981">{{ finalizeMsg }}</span>
      <button v-if="canFinalize" :disabled="finalizing" @click="doFinalize"
              style="background:var(--accent);color:#fff;border:none;padding:0.45rem 1.1rem;border-radius:6px;cursor:pointer;font-size:0.875rem">
        {{ finalizing ? '结算中…' : '结算 Rating' }}
      </button>
    </div>

    <div v-if="frozen" style="background:#f59e0b18;border:1px solid #f59e0b55;color:#f59e0b;border-radius:8px;padding:0.6rem 1rem;font-size:0.875rem;margin-bottom:1rem;text-align:center">
      🔒 封榜中——赛末最后 {{ contest.freeze_minutes }} 分钟的提交暂不显示，比赛结束后揭晓
    </div>

    <!-- 空状态 -->
    <div v-if="rankedUsers.length === 0" class="empty-state">
      暂无参赛者
    </div>

    <!-- 榜单表格 -->
    <div v-else class="table-wrap">
      <table class="rank-table">
        <thead>
          <tr>
            <th class="th-rank">名次</th>
            <th class="th-user">选手</th>
            <th v-if="!isIOI" class="th-solved">通过</th>
            <th v-if="!isIOI" class="th-penalty">罚时</th>
            <th v-else class="th-solved">总分</th>
            <th
              v-for="label in problemLabels"
              :key="label"
              class="th-problem"
            >{{ label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(user, idx) in rankedUsers"
            :key="user.user_id"
            :class="['rank-row', { 'top3': user.rank <= 3 }]"
          >
            <!-- 名次 -->
            <td class="td-rank">
              <span v-if="user.rank === 1" class="medal medal-1">1</span>
              <span v-else-if="user.rank === 2" class="medal medal-2">2</span>
              <span v-else-if="user.rank === 3" class="medal medal-3">3</span>
              <span v-else class="rank-num">{{ user.rank }}</span>
            </td>

            <!-- 选手 -->
            <td class="td-user">
              <div class="user-cell" @click="router.push(`/users/${user.user_id}`)">
                <div class="avatar-sm" :style="{ background: user.avatar_color }">
                  {{ user.username[0].toUpperCase() }}
                </div>
                <span class="username">{{ user.username }}</span>
              </div>
            </td>

            <!-- 通过数 / 总分 -->
            <td v-if="!isIOI" class="td-solved">{{ user.solved }}</td>
            <td v-if="!isIOI" class="td-penalty">{{ user.solved ? formatPenalty(user.penalty) : '-' }}</td>
            <td v-else class="td-solved" style="font-weight:700;color:var(--accent)">{{ user.score }}</td>

            <!-- 各题结果 -->
            <td
              v-for="label in problemLabels"
              :key="label"
              class="td-problem"
            >
              <template v-if="isIOI">
                <div v-if="user.problems[label]"
                     :style="user.problems[label].score >= user.problems[label].max ? 'color:#10b981;font-weight:700' : (user.problems[label].score > 0 ? 'color:#f59e0b;font-weight:600' : 'color:var(--text-muted)')">
                  {{ user.problems[label].score }}
                  <span v-if="user.problems[label].frozen" style="font-size:0.7rem">🔒{{ user.problems[label].frozen }}</span>
                </div>
                <div v-else class="cell-empty">—</div>
              </template>
              <template v-else>
                <div v-if="user.problems[label]?.ac" class="cell-ac">
                  <div class="cell-time">{{ user.problems[label].time_min }}m</div>
                  <div v-if="user.problems[label].wrong_count" class="cell-wrong">-{{ user.problems[label].wrong_count }}</div>
                </div>
                <div v-else-if="user.problems[label]?.wrong_count > 0" class="cell-wa">-{{ user.problems[label].wrong_count }}</div>
                <div v-else-if="user.problems[label]?.frozen" style="color:#f59e0b;font-size:0.78rem">🔒{{ user.problems[label].frozen }}</div>
                <div v-else class="cell-empty">—</div>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<style scoped>
.loading { text-align: center; padding: 4rem; color: var(--text-muted); }
.ranking-page { padding: 0.5rem 0; }

/* 头部 */
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.4rem 1.8rem;
  margin-bottom: 1.2rem; gap: 1rem;
}
.back-link {
  font-size: 0.82rem; color: var(--text-muted); cursor: pointer;
  margin-bottom: 0.4rem; transition: color 0.15s;
}
.back-link:hover { color: var(--accent); }
.page-title { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.5rem; }
.meta-row { display: flex; align-items: center; gap: 0.6rem; }
.rule-badge {
  background: var(--bg-input); border: 1px solid var(--border);
  color: var(--accent); padding: 0.15rem 0.55rem;
  border-radius: 4px; font-size: 0.75rem; font-weight: 600;
}
.live-badge {
  background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.4);
  color: #22c55e; padding: 0.15rem 0.5rem;
  border-radius: 4px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.meta-time { font-size: 0.82rem; color: var(--text-muted); }
.header-right { text-align: right; flex-shrink: 0; }
.update-info { font-size: 0.82rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.4rem; justify-content: flex-end; }
.update-time { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem; }
.refresh-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #22c55e;
  animation: pulse 2s infinite;
}

.empty-state {
  text-align: center; padding: 3rem; color: var(--text-muted);
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
}

/* 表格 */
.table-wrap {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; overflow-x: auto;
}
.rank-table {
  width: 100%; border-collapse: collapse; min-width: 600px;
}
.rank-table th {
  padding: 0.7rem 0.9rem; text-align: center;
  font-size: 12.5px; font-weight: 500; color: var(--text-secondary); background: var(--bg-page);
  border-bottom: 1px solid var(--border); white-space: nowrap; position: sticky; top: 0;
}
.th-user { text-align: left; }
.rank-table td { padding: 0.65rem 0.9rem; border-bottom: 1px solid var(--border); text-align: center; }
.rank-row:last-child td { border-bottom: none; }
.rank-row:hover td { background: var(--bg-hover); }
.rank-row.top3 td { background: var(--bg-active); }

/* 名次 */
.medal {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  font-size: 0.78rem; font-weight: 700;
}
.medal-1 { background: rgba(255,215,0,0.18); color: #ffd700; border: 1px solid rgba(255,215,0,0.4); }
.medal-2 { background: rgba(192,192,192,0.18); color: #c0c0c0; border: 1px solid rgba(192,192,192,0.4); }
.medal-3 { background: rgba(205,127,50,0.18); color: #cd7f32; border: 1px solid rgba(205,127,50,0.4); }
.rank-num { color: var(--text-muted); font-size: 0.88rem; }

/* 选手 */
.td-user { text-align: left; }
.user-cell { display: flex; align-items: center; gap: 0.6rem; cursor: pointer; }
.user-cell:hover .username { color: var(--accent); }
.avatar-sm {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; color: #fff;
}
.username { color: var(--text-secondary); font-size: 0.88rem; transition: color 0.15s; }

/* 统计列 */
.td-solved { font-weight: 700; color: #22c55e; font-size: 0.95rem; }
.td-penalty { color: var(--text-muted); font-size: 0.85rem; }

/* 题目结果格 */
.td-problem { min-width: 56px; }
.cell-ac {
  display: flex; flex-direction: column; align-items: center;
  gap: 1px; line-height: 1.2;
}
.cell-time { color: #22c55e; font-size: 0.8rem; font-weight: 600; }
.cell-wrong { color: rgba(34,197,94,0.5); font-size: 0.72rem; }
.cell-wa { color: #ef4444; font-size: 0.82rem; font-weight: 600; }
.cell-empty { color: var(--text-muted); font-size: 0.85rem; }

@media (max-width: 700px) {
  .page-header { flex-direction: column; }
  .header-right { text-align: left; }
}
</style>
