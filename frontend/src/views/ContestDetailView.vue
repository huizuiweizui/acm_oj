<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getContest, registerContest } from '@/api/contests'
import { useUserStore } from '@/stores/user'
import DifficultyBadge from '@/components/DifficultyBadge.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const contest = ref(null)
const problems = ref([])
const problemsVisible = ref(true)
const problemCount = ref(0)
const isRegistered = ref(false)
const participantCount = ref(0)
const loading = ref(true)
const registering = ref(false)
const regMsg = ref('')

const statusCfg = {
  running:  { label: '进行中', bg: 'var(--status-ac-bg)',      color: 'var(--status-ac-text)' },
  upcoming: { label: '即将开始', bg: 'var(--status-pending-bg)', color: 'var(--status-pending-text)' },
  ended:    { label: '已结束', bg: 'var(--bg-hover)',           color: 'var(--text-muted)' },
}
const statusIconMap  = { ac: '✓', tried: '·', todo: '' }
const statusBgMap    = { ac: 'var(--status-ac-bg)',  tried: 'var(--status-tle-bg)', todo: 'transparent' }
const statusColorMap = { ac: 'var(--status-ac-text)', tried: 'var(--status-tle-text)', todo: 'transparent' }

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
    problemsVisible.value = data.problems_visible !== false
    problemCount.value = data.problem_count ?? data.problems.length
    isRegistered.value = data.is_registered
    participantCount.value = data.participant_count
  } finally {
    loading.value = false
  }
}

// 私有赛需要密码；公开赛这一栏不出现
const needPassword = computed(() => contest.value && !contest.value.is_public)
const regPassword = ref('')

async function handleRegister() {
  if (!userStore.isLoggedIn) {
    router.push(`/login?next=/contests/${route.params.id}`)
    return
  }
  registering.value = true
  regMsg.value = ''
  try {
    const { data } = await registerContest(route.params.id, regPassword.value.trim())
    isRegistered.value = true
    participantCount.value += 1
    regMsg.value = data.detail
    regPassword.value = ''
    // 报名后才拿得到题目清单，重新取一次
    await fetchContest()
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
            :style="{ background: statusCfg[contest.status]?.bg, color: statusCfg[contest.status]?.color }"
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
          <template v-else>
            <input
              v-if="needPassword"
              v-model="regPassword"
              type="password"
              class="reg-password"
              placeholder="比赛密码"
              autocomplete="off"
              @keyup.enter="handleRegister"
            />
            <button
              class="btn-register"
              :disabled="registering"
              @click="handleRegister"
            >{{ registering ? '报名中...' : '立即报名' }}</button>
          </template>
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
                :style="{ background: statusBgMap[p.user_status], color: statusColorMap[p.user_status] }"
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
          <!-- 赛前 / 未报名时题目不公开，说明清楚原因，避免看起来像"这场没题" -->
          <tr v-if="!problemsVisible">
            <td colspan="4" class="empty locked">
              <div class="locked-title">
                本场共 {{ problemCount }} 道题，题目将在比赛开始后公开
              </div>
              <div class="locked-hint">
                {{ contest.status === 'upcoming'
                  ? '请先报名，开赛后即可查看题面并提交'
                  : '报名后即可查看题面并提交' }}
              </div>
            </td>
          </tr>
          <tr v-else-if="problems.length === 0">
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
.loading { text-align: center; padding: 4rem; color: var(--text-muted); }

.contest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.8rem 2rem;
  margin-bottom: 1.8rem;
  gap: 1.5rem;
}
.header-main { flex: 1; }
.contest-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.75rem; }

.meta-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.rule-badge {
  background: var(--bg-input); border: 1px solid var(--border);
  color: var(--accent); padding: 0.15rem 0.55rem;
  border-radius: 4px; font-size: 0.78rem; font-weight: 600;
}
.status-badge {
  font-size: 12.5px; font-weight: 600;
  padding: 2px 10px; border-radius: 6px;
}
.meta-text { color: var(--text-muted); font-size: 0.85rem; }

.time-info { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem; }
.sep { margin: 0 0.5rem; }
.desc { color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; margin: 0.75rem 0 0; }

.header-action { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; flex-shrink: 0; }
.btn-register {
  padding: 0.6rem 1.6rem; background: var(--accent); color: #fff;
  border: none; border-radius: 7px; font-size: 0.95rem; font-weight: 600;
  cursor: pointer;
}
.btn-register:hover:not(:disabled) { background: var(--accent-hover); }
.btn-register:disabled { opacity: 0.6; cursor: not-allowed; }
.reg-password {
  padding: 0.55rem 0.8rem; margin-bottom: 0.5rem; width: 100%;
  background: var(--bg-input); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 7px; font-size: 0.9rem;
}
.reg-password:focus { border-color: var(--accent); outline: none; }
.btn-rank {
  padding: 0.45rem 1.2rem; background: transparent;
  border: 1px solid var(--border); color: var(--accent);
  border-radius: 7px; font-size: 0.88rem; font-weight: 600;
  cursor: pointer; transition: border-color 0.15s;
}
.btn-rank:hover { border-color: var(--accent); }
.reg-msg { font-size: 0.82rem; color: var(--text-secondary); }

.section-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.9rem; }

.table-wrap { background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }
.problem-table { width: 100%; border-collapse: collapse; }
.problem-table th {
  padding: 8px 16px; text-align: left;
  font-size: 12.5px; color: var(--text-secondary); font-weight: 500;
  background: var(--bg-page); border-bottom: 1px solid var(--border);
  position: sticky; top: 0;
}
.problem-table td { padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 14px; }
.problem-table tr:last-child td { border-bottom: none; }
.problem-table tr:hover td { background: var(--bg-hover); }

.status-cell { text-align: center; }
.status-dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  font-size: 11px; font-weight: 700;
}
.label-cell { font-weight: 700; color: var(--accent); font-family: var(--font-mono); }
.problem-link { color: var(--text-primary); text-decoration: none; }
.problem-link:hover { color: var(--accent-text); }
.reg-ok { color: var(--status-ac-text); font-weight: 600; font-size: 0.95rem; }
.empty { text-align: center; padding: 2rem; color: var(--text-muted); }
.locked-title { color: var(--text-secondary); font-size: 0.95rem; font-weight: 600; }
.locked-hint { margin-top: 0.4rem; font-size: 0.85rem; color: var(--text-muted); }
</style>
