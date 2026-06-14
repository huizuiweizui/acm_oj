<script setup>
/**
 * TypeScript-style interfaces for Home page data contracts
 *
 * interface SiteStats {
 *   problemCount: number
 *   userCount: number
 *   submissionCount: number
 * }
 *
 * interface Problem {
 *   id: number | string
 *   title: string
 *   difficulty: '入门' | '简单' | '中等' | '困难'
 *   acRate?: number
 * }
 *
 * interface ContestItem {
 *   id: number | string
 *   title: string
 *   startTime: string   // ISO 8601
 *   endTime: string     // ISO 8601
 *   mode: 'ICPC' | 'IOI' | 'OI'
 * }
 *
 * interface RecentSubmission {
 *   id: number | string
 *   problemId: number | string
 *   problemTitle: string
 *   status: 'AC' | 'WA' | 'TLE' | 'MLE' | 'RE' | 'CE'
 *   time: number | null   // ms
 *   memory: number | null // KB
 *   language: string
 *   submittedAt: string   // ISO 8601
 * }
 *
 * interface HeatmapEntry {
 *   date: string   // 'YYYY-MM-DD'
 *   count: number
 * }
 *
 * interface RecommendProblem {
 *   id: number | string
 *   title: string
 *   difficulty: string
 *   reason: string
 * }
 *
 * interface UserDashboard {
 *   acCount: number
 *   totalSubmissions: number
 *   streak: number
 *   heatmap: HeatmapEntry[]
 *   recommend: RecommendProblem | null
 *   recentSubmissions: RecentSubmission[]
 *   recentContests: ContestItem[]
 * }
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api/index.js'

import HeroGuest       from '@/components/home/HeroGuest.vue'
import HeatmapCard     from '@/components/home/HeatmapCard.vue'
import RecommendCard   from '@/components/home/RecommendCard.vue'
import RecentJudgeCard from '@/components/home/RecentJudgeCard.vue'
import ContestCard     from '@/components/home/ContestCard.vue'
import NoticeBar       from '@/components/home/NoticeBar.vue'

const router    = useRouter()
const userStore = useUserStore()

// ── Mock data (used when API is unavailable) ──────────────────────────────

const MOCK_SITE_STATS = { problemCount: 24, userCount: 5, submissionCount: 148 }

const MOCK_HOT_PROBLEMS = [
  { id: 1,  title: '两数之和',        difficulty: '入门', acRate: 72 },
  { id: 2,  title: '反转链表',        difficulty: '简单', acRate: 64 },
  { id: 7,  title: '最长公共子序列',  difficulty: '中等', acRate: 41 },
  { id: 12, title: '最大流（网络流）', difficulty: '困难', acRate: 18 },
  { id: 15, title: '二叉树层序遍历',  difficulty: '简单', acRate: 58 },
]

const MOCK_CONTESTS = [
  {
    id: 1,
    title: '2024 春季算法模拟赛',
    startTime: new Date(Date.now() + 2 * 86400000).toISOString(),
    endTime:   new Date(Date.now() + 2 * 86400000 + 3 * 3600000).toISOString(),
    mode: 'ICPC',
  },
  {
    id: 2,
    title: '第三届校内周赛',
    startTime: new Date(Date.now() - 5 * 86400000).toISOString(),
    endTime:   new Date(Date.now() - 5 * 86400000 + 2 * 3600000).toISOString(),
    mode: 'IOI',
  },
]

function genMockHeatmap() {
  const entries = []
  const today = new Date()
  for (let i = 111; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const date = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    const r = Math.random()
    const count = r < 0.55 ? 0 : r < 0.72 ? 1 : r < 0.84 ? 2 : r < 0.92 ? 4 : r < 0.97 ? 7 : 11
    if (count > 0) entries.push({ date, count })
  }
  return entries
}

const MOCK_DASHBOARD = {
  acCount: 42,
  totalSubmissions: 137,
  streak: 7,
  heatmap: genMockHeatmap(),
  recommend: {
    id: 7,
    title: '最长公共子序列',
    difficulty: '中等',
    reason: '基于你的薄弱知识点：动态规划',
  },
  recentSubmissions: [
    { id: 1, problemId: 2,  problemTitle: '反转链表',        status: 'AC',  time: 12,   memory: 5120,  language: 'C++',    submittedAt: new Date(Date.now() - 30 * 60000).toISOString() },
    { id: 2, problemId: 7,  problemTitle: '最长公共子序列',  status: 'WA',  time: 48,   memory: 8192,  language: 'Python', submittedAt: new Date(Date.now() - 2  * 3600000).toISOString() },
    { id: 3, problemId: 12, problemTitle: '最大流（网络流）', status: 'TLE', time: 2000, memory: 16384, language: 'C++',    submittedAt: new Date(Date.now() - 86400000).toISOString() },
    { id: 4, problemId: 1,  problemTitle: '两数之和',        status: 'AC',  time: 4,    memory: 4096,  language: 'Java',   submittedAt: new Date(Date.now() - 2  * 86400000).toISOString() },
  ],
  recentContests: MOCK_CONTESTS,
}

const MOCK_NOTICE = '系统已更新至 v2.3，新增 AI 代码讲解功能，欢迎体验！'

// ── Reactive state ────────────────────────────────────────────────────────

const siteStats     = ref(MOCK_SITE_STATS)
const hotProblems   = ref(MOCK_HOT_PROBLEMS)
const guestContests = ref(MOCK_CONTESTS)
const notice        = ref(MOCK_NOTICE)
const dashboard     = ref(MOCK_DASHBOARD)

// ── Greeting ──────────────────────────────────────────────────────────────

const timeGreeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6)  return '深夜好'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const dailyTip = computed(() => {
  const today = new Date()
  const ds = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`
  const entry = dashboard.value.heatmap.find(h => h.date === ds)
  return entry
    ? `今天已提交 ${entry.count} 次，继续加油！`
    : '今天还没有提交，从推荐题开始吧'
})

// ── Difficulty badge ───────────────────────────────────────────────────────

const DIFF_STYLE = {
  '入门': { bg: '#f0fdf4', color: '#166534' },
  '简单': { bg: '#f0fdf4', color: '#166534' },
  '中等': { bg: '#fefce8', color: '#854d0e' },
  '困难': { bg: '#fef2f2', color: '#991b1b' },
}
function diffStyle(d) {
  return DIFF_STYLE[d] ?? { bg: '#f1f5f9', color: '#475569' }
}

// ── Data loading ──────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const { data } = await api.get('/stats/')
    siteStats.value = {
      problemCount:    data.total_problems    ?? MOCK_SITE_STATS.problemCount,
      userCount:       data.total_users       ?? MOCK_SITE_STATS.userCount,
      submissionCount: data.total_submissions ?? MOCK_SITE_STATS.submissionCount,
    }
    if (data.recent_problems?.length) {
      hotProblems.value = data.recent_problems.map(p => ({
        id: p.id, title: p.title, difficulty: p.difficulty, acRate: p.ac_rate,
      }))
    }
    if (data.active_contests?.length) {
      const mapC = c => ({
        id: c.id, title: c.title,
        startTime: c.start_time, endTime: c.end_time, mode: c.rule_type ?? 'ICPC',
      })
      guestContests.value = data.active_contests.map(mapC)
      dashboard.value = { ...dashboard.value, recentContests: data.active_contests.map(mapC) }
    }
  } catch { /* keep mocks */ }

  if (userStore.isLoggedIn) {
    try {
      const { data } = await api.get('/submissions/', { params: { page_size: 5 } })
      const subs = (data.results ?? data).slice(0, 5).map(s => ({
        id: s.id,
        problemId:    s.problem,
        problemTitle: s.problem_title ?? `题目 #${s.problem}`,
        status:       s.status,
        time:         s.time_used,
        memory:       s.memory_used,
        language:     s.language,
        submittedAt:  s.submitted_at,
      }))
      if (subs.length) dashboard.value = { ...dashboard.value, recentSubmissions: subs }
    } catch { /* keep mocks */ }
  }
})
</script>

<template>
  <div class="page-wrap">
    <div class="content">

      <!-- ════════════════════════════════════════
           GUEST VIEW
           ════════════════════════════════════════ -->
      <template v-if="!userStore.isLoggedIn">

        <HeroGuest :stats="siteStats" />

        <!-- Two-column: hot problems + contests -->
        <div class="guest-grid">

          <div class="card">
            <div class="sec-head">
              <span class="sec-title">热门题目</span>
              <button class="link-btn" @click="router.push({ name: 'problem-list' })">查看全部 →</button>
            </div>
            <table class="prob-table">
              <tbody>
                <tr
                  v-for="p in hotProblems"
                  :key="p.id"
                  class="prob-row"
                  @click="router.push({ name: 'problem-detail', params: { id: p.id } })"
                >
                  <td class="pid">#{{ p.id }}</td>
                  <td class="ptitle">{{ p.title }}</td>
                  <td class="pdiff">
                    <span
                      class="diff-pill"
                      :style="{ background: diffStyle(p.difficulty).bg, color: diffStyle(p.difficulty).color }"
                    >{{ p.difficulty }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <ContestCard :contests="guestContests" />

        </div>

        <NoticeBar :message="notice" />

      </template>

      <!-- ════════════════════════════════════════
           DASHBOARD VIEW (logged in)
           ════════════════════════════════════════ -->
      <template v-else>

        <!-- Greeting + personal stats -->
        <div class="dash-header">
          <div class="greeting-block">
            <span class="greeting">{{ timeGreeting }}，{{ userStore.user?.username ?? '同学' }}</span>
            <span class="daily-tip">{{ dailyTip }}</span>
          </div>
          <div class="personal-stats">
            <div class="ps-item">
              <span class="ps-num">{{ dashboard.acCount }}</span>
              <span class="ps-label">已 AC</span>
            </div>
            <div class="ps-sep"></div>
            <div class="ps-item">
              <span class="ps-num">{{ dashboard.totalSubmissions }}</span>
              <span class="ps-label">总提交</span>
            </div>
            <div class="ps-sep"></div>
            <div class="ps-item">
              <span class="ps-num">{{ dashboard.streak }}</span>
              <span class="ps-label">连续打卡</span>
            </div>
          </div>
        </div>

        <!-- 2×2 grid: heatmap | recommend / judge | contests -->
        <div class="dash-grid">
          <HeatmapCard     :submissions="dashboard.heatmap" />
          <RecommendCard   :problem="dashboard.recommend" />
          <RecentJudgeCard :submissions="dashboard.recentSubmissions" />
          <ContestCard     :contests="dashboard.recentContests" />
        </div>

      </template>

    </div>
  </div>
</template>

<style scoped>
/* ── Outer wrapper ─────────────────────────────────── */
.page-wrap {
  min-height: calc(100vh - 56px);
  background: var(--bg-page);
}
.content {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 24px 56px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Shared card shell (also used by sub-components via :deep) ── */
.card,
:deep(.card) {
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
}

/* ══════════════════════════════════════════
   GUEST
   ══════════════════════════════════════════ */
.guest-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
}

/* Hot problems card internals */
.sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px 12px;
  border-bottom: 1px solid var(--border);
}
.sec-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.link-btn {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--home-accent);
  cursor: pointer;
  padding: 0;
}
.link-btn:hover { text-decoration: underline; }

.prob-table {
  width: 100%;
  border-collapse: collapse;
}
.prob-row { cursor: pointer; }
.prob-row:hover td { background: var(--bg-hover); }
.prob-row td {
  padding: 10px 20px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  transition: background 0.1s;
}
.prob-row:last-child td { border-bottom: none; }
.pid {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  width: 52px;
}
.ptitle { color: var(--text-primary); }
.pdiff  { text-align: right; }
.diff-pill {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 500;
  white-space: nowrap;
}

/* ══════════════════════════════════════════
   DASHBOARD
   ══════════════════════════════════════════ */
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 0 4px;
  gap: 16px;
  flex-wrap: wrap;
}
.greeting-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.greeting {
  font-size: 20px;
  font-weight: 500;
  color: var(--text-primary);
}
.daily-tip {
  font-size: 13px;
  color: var(--text-secondary);
}

.personal-stats {
  display: flex;
  align-items: center;
}
.ps-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 0 20px;
}
.ps-item:first-child { padding-left: 0; }
.ps-num {
  font-size: 20px;
  font-weight: 500;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.ps-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.ps-sep {
  width: 1px;
  height: 32px;
  background: var(--border);
  flex-shrink: 0;
}

.dash-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
  align-items: start;
}

/* ── Responsive ────────────────────────────────────── */
@media (max-width: 768px) {
  .content   { padding: 0 16px 40px; }
  .guest-grid { grid-template-columns: 1fr; }
  .dash-grid  { grid-template-columns: 1fr; }
  .dash-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding-top: 20px;
  }
  .personal-stats { width: 100%; }
  .ps-item { align-items: flex-start; padding: 0 16px; }
  .ps-item:first-child { padding-left: 0; }
}
</style>
