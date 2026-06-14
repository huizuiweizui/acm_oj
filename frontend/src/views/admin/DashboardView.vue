<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/index'

const router = useRouter()
const loading     = ref(true)
const refreshing  = ref(false)
const lastUpdated = ref(null)
const errorMsg    = ref('')   // 空字符串 = 无错误；否则显示具体信息

const stats = ref(null)
const admin = ref(null)

let pollTimer = null
const POLL_MS = 20_000

function _httpErr(e) {
  const status = e.response?.status
  if (!status)         return '网络错误（无法连接服务器）'
  if (status === 401)  return '401 登录已过期，请重新登录'
  if (status === 403)  return '403 无权限（当前账号可能不是管理员角色）'
  if (status === 404)  return '404 接口不存在'
  if (status >= 500)   return `${status} 服务器内部错误`
  return `HTTP ${status}`
}

async function fetchData(initial = false) {
  if (!initial) refreshing.value = true
  errorMsg.value = ''

  // 两个接口分开请求，互不影响
  const [sRes, aRes] = await Promise.allSettled([
    api.get('/stats/'),
    api.get('/admin/stats/'),
  ])

  if (sRes.status === 'fulfilled') {
    stats.value = sRes.value.data
  } else {
    errorMsg.value = '/stats/: ' + _httpErr(sRes.reason)
  }

  if (aRes.status === 'fulfilled') {
    admin.value = aRes.value.data
  } else {
    const msg = '/admin/stats/: ' + _httpErr(aRes.reason)
    errorMsg.value = errorMsg.value ? errorMsg.value + ' | ' + msg : msg
  }

  lastUpdated.value = new Date()
  if (initial) loading.value = false
  refreshing.value = false
}

onMounted(() => {
  fetchData(true)
  pollTimer = setInterval(() => fetchData(false), POLL_MS)
})
onUnmounted(() => clearInterval(pollTimer))

// ── Derived values ────────────────────────────────────────────────────────
const totalUsers       = computed(() => stats.value?.total_users       ?? 0)
const totalProblems    = computed(() => stats.value?.total_problems     ?? 0)
const totalSubmissions = computed(() => stats.value?.total_submissions  ?? 0)
const totalTeams       = computed(() => admin.value?.total_teams        ?? 0)
const todayReg         = computed(() => admin.value?.today_reg          ?? 0)
const weekReg          = computed(() => admin.value?.week_reg           ?? 0)
const roles            = computed(() => admin.value?.roles              ?? {})
const recentUsers      = computed(() => admin.value?.recent_users       ?? [])
const recentSubs       = computed(() => stats.value?.recent_submissions ?? [])

// Role distribution bar widths
function rolePct(key) {
  if (!totalUsers.value) return 0
  return Math.round(((roles.value[key] ?? 0) / totalUsers.value) * 100)
}

// ── Helpers ───────────────────────────────────────────────────────────────
function fmtTime(d) {
  return d ? d.toLocaleTimeString('zh-CN', { hour12: false }) : ''
}
function timeAgo(iso) {
  if (!iso) return ''
  const m = Math.floor((Date.now() - new Date(iso)) / 60000)
  if (m < 1)  return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return new Date(iso).toLocaleDateString('zh-CN')
}
function fmtJoinDate(s) {
  if (!s) return '—'
  return s.slice(0, 10)
}

const STATUS_CLS = {
  AC: 'st-ac', WA: 'st-wa', TLE: 'st-tle', MLE: 'st-tle',
  RE: 'st-wa', CE: 'st-ce', PE: 'st-ce', Pending: 'st-pend', Judging: 'st-pend',
}
function stCls(s) { return STATUS_CLS[s] ?? 'st-pend' }

const ROLE_LABEL = { student: '学生', teacher: '教师', admin: '管理员' }
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="loading-screen">
    <div class="spinner"></div>
    <span>加载中…</span>
  </div>

  <div v-else class="dash">

    <!-- ── 页头 ── -->
    <div class="page-head">
      <h1 class="page-title">管理后台</h1>
      <div class="head-right">
        <span v-if="errorMsg" class="err-badge" :title="errorMsg">{{ errorMsg }}</span>
        <span v-if="lastUpdated && !errorMsg" class="updated-at">{{ fmtTime(lastUpdated) }} 更新</span>
        <button
          class="icon-btn"
          :class="{ spin: refreshing }"
          title="立即刷新"
          @click="fetchData(false)"
        >
          <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
            <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
            <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- ── 4 个统计卡 ── -->
    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-top">
          <span class="stat-num">{{ totalUsers }}</span>
          <span class="stat-label">注册用户</span>
        </div>
        <div class="stat-sub">今日 +{{ todayReg }} · 本周 +{{ weekReg }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-top">
          <span class="stat-num accent">{{ totalProblems }}</span>
          <span class="stat-label">题目总数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-top">
          <span class="stat-num">{{ totalSubmissions }}</span>
          <span class="stat-label">提交总数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-top">
          <span class="stat-num green">{{ totalTeams }}</span>
          <span class="stat-label">团队总数</span>
        </div>
      </div>
    </div>

    <!-- ── 角色分布 + 快捷入口 ── -->
    <div class="two-col">

      <div class="card">
        <h2 class="card-title">用户角色分布</h2>
        <div class="role-rows">
          <div v-for="key in ['student','teacher','admin']" :key="key" class="role-row">
            <span class="role-name">{{ ROLE_LABEL[key] }}</span>
            <div class="bar-track">
              <div class="bar-fill" :class="`bar-${key}`" :style="{ width: rolePct(key) + '%' }"></div>
            </div>
            <span class="role-cnt">{{ roles[key] ?? 0 }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h2 class="card-title">快捷管理</h2>
        <div class="quick-grid">
          <button class="ql" @click="router.push('/admin/users')">
            <span class="ql-icon">👥</span>用户管理
          </button>
          <button class="ql" @click="router.push('/problems')">
            <span class="ql-icon">📝</span>题目列表
          </button>
          <button class="ql" @click="router.push('/contests')">
            <span class="ql-icon">🏆</span>比赛管理
          </button>
          <button class="ql" @click="router.push('/teacher')">
            <span class="ql-icon">🏫</span>团队管理
          </button>
        </div>
      </div>

    </div>

    <!-- ── 最近注册 ── -->
    <div class="card">
      <div class="card-head">
        <h2 class="card-title" style="margin:0">最近注册</h2>
        <button class="link-btn" @click="router.push('/admin/users')">查看全部 →</button>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>姓名</th>
              <th>学号</th>
              <th>角色</th>
              <th>注册时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!recentUsers.length">
              <td colspan="5" class="empty-cell">暂无数据</td>
            </tr>
            <tr v-for="u in recentUsers" :key="u.id" class="data-row">
              <td>
                <span class="user-link" @click="router.push(`/users/${u.id}`)">{{ u.username }}</span>
              </td>
              <td class="muted">{{ u.display_name || '—' }}</td>
              <td class="muted mono">{{ u.student_id || '—' }}</td>
              <td>
                <span class="role-pill" :class="`rp-${u.role}`">{{ ROLE_LABEL[u.role] ?? u.role }}</span>
              </td>
              <td class="muted">{{ fmtJoinDate(u.date_joined) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── 最近提交 ── -->
    <div class="card">
      <div class="card-head">
        <h2 class="card-title" style="margin:0">
          <span class="live-dot" :class="{ pulse: refreshing }"></span>最近提交
        </h2>
      </div>
      <div v-if="!recentSubs.length" class="empty-msg">暂无提交记录</div>
      <div v-else class="sub-list">
        <div v-for="s in recentSubs" :key="s.id" class="sub-row">
          <span class="sub-user" @click="router.push(`/users/${s.user_id ?? s.username}`)">
            {{ s.username }}
          </span>
          <span class="sub-arrow muted">→</span>
          <span class="sub-prob">
            <span class="mono muted">#{{ s.problem_id ?? s.problem }}</span>
            {{ s.problem_title }}
          </span>
          <span class="sub-status mono" :class="stCls(s.status)">{{ s.status }}</span>
          <span v-if="s.time_used" class="sub-meta mono muted">{{ s.time_used }} ms</span>
          <span v-if="s.language" class="sub-meta mono muted">{{ s.language }}</span>
          <span class="sub-ago muted">{{ timeAgo(s.submitted_at) }}</span>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ── Layout ──────────────────────────────────────────── */
.dash {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px 56px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Loading ─────────────────────────────────────────── */
.loading-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 40vh;
  color: var(--text-muted);
  font-size: 13px;
}
.spinner {
  width: 22px; height: 22px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* ── Page head ───────────────────────────────────────── */
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 24px;
  flex-wrap: wrap;
  gap: 8px;
}
.page-title {
  font-size: 20px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0;
}
.head-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.updated-at {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.err-badge {
  font-size: 12px;
  color: #b91c1c;
  background: #fee2e2;
  padding: 1px 8px;
  border-radius: 4px;
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: help;
}
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px; height: 28px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  padding: 0;
}
.icon-btn:hover { color: var(--accent); border-color: var(--accent); }
.icon-btn.spin svg { animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Shared card ─────────────────────────────────────── */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 16px 20px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 14px;
}
.link-btn {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--accent);
  cursor: pointer;
  padding: 0;
}
.link-btn:hover { text-decoration: underline; }

/* ── Stat row ────────────────────────────────────────── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 16px 20px;
}
.stat-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}
.stat-num {
  font-size: 28px;
  font-weight: 500;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.stat-num.accent { color: var(--accent); }
.stat-num.green  { color: #059669; }
.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.stat-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Two-col ─────────────────────────────────────────── */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* ── Role distribution ───────────────────────────────── */
.role-rows { display: flex; flex-direction: column; gap: 10px; }
.role-row  { display: flex; align-items: center; gap: 10px; }
.role-name {
  width: 40px;
  font-size: 13px;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 7px;
  background: var(--bg-secondary);
  border-radius: 999px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
  min-width: 2px;
}
.bar-student { background: var(--accent); }
.bar-teacher { background: #059669; }
.bar-admin   { background: #d97706; }
.role-cnt {
  width: 28px;
  text-align: right;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

/* ── Quick links ─────────────────────────────────────── */
.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.ql {
  display: flex;
  align-items: center;
  gap: 7px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  text-align: left;
}
.ql:hover {
  border-color: var(--accent);
  color: var(--accent-text);
  background: var(--accent-light);
}
.ql-icon { font-size: 15px; }

/* ── Data table ──────────────────────────────────────── */
.table-wrap { overflow-x: auto; }
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  padding: 6px 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.data-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.data-row:last-child td { border-bottom: none; }
.data-row:hover td { background: var(--bg-hover); }
.user-link {
  color: var(--accent);
  cursor: pointer;
  font-weight: 500;
}
.user-link:hover { text-decoration: underline; }
.empty-cell {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
  font-size: 13px;
}

/* Role pills */
.role-pill {
  display: inline-block;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 4px;
  font-weight: 500;
}
.rp-student { background: var(--accent-light);  color: var(--accent-text); }
.rp-teacher { background: #d1fae5; color: #065f46; }
.rp-admin   { background: #fef3c7; color: #92400e; }

/* ── Submission list ─────────────────────────────────── */
.empty-msg {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  padding: 24px 0;
}
.sub-list { display: flex; flex-direction: column; gap: 1px; }
.sub-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  transition: background 0.1s;
}
.sub-row:last-child { border-bottom: none; }
.sub-row:hover { background: var(--bg-hover); border-radius: 4px; }
.sub-user {
  color: var(--accent);
  cursor: pointer;
  min-width: 64px;
  flex-shrink: 0;
  font-weight: 500;
}
.sub-user:hover { text-decoration: underline; }
.sub-arrow { font-size: 11px; flex-shrink: 0; }
.sub-prob {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  color: var(--text-primary);
  white-space: nowrap;
}
.sub-status {
  font-size: 11px;
  font-weight: 600;
  min-width: 36px;
  text-align: center;
  flex-shrink: 0;
}
.sub-meta {
  font-size: 11px;
  flex-shrink: 0;
}
.sub-ago {
  font-size: 11px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Status colours */
.st-ac   { color: var(--home-ac);  }
.st-wa   { color: var(--home-wa);  }
.st-tle  { color: var(--home-tle); }
.st-ce   { color: var(--status-ce-text); }
.st-pend { color: var(--text-muted); }

/* ── Live dot ────────────────────────────────────────── */
.live-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #059669;
  margin-right: 7px;
  vertical-align: middle;
  position: relative; top: -1px;
}
.live-dot.pulse { animation: livePulse 1s ease-in-out infinite; }
@keyframes livePulse { 0%,100%{opacity:1} 50%{opacity:.25} }

/* Utility */
.muted { color: var(--text-muted); }
.mono  { font-family: var(--font-mono); }

/* ── Responsive ──────────────────────────────────────── */
@media (max-width: 860px) {
  .stat-row  { grid-template-columns: repeat(2, 1fr); }
  .two-col   { grid-template-columns: 1fr; }
}
@media (max-width: 540px) {
  .dash { padding: 0 14px 40px; }
  .stat-row { grid-template-columns: repeat(2, 1fr); }
  .sub-meta { display: none; }
}
</style>
