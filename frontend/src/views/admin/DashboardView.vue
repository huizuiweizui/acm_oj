<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/index'

const router = useRouter()
const loading = ref(true)
const stats = ref(null)   // /api/stats/
const admin = ref(null)   // /api/admin/stats/

onMounted(async () => {
  try {
    const [s, a] = await Promise.all([
      api.get('/stats/'),
      api.get('/admin/stats/'),
    ])
    stats.value = s.data
    admin.value = a.data
  } finally {
    loading.value = false
  }
})

const roles = computed(() => admin.value?.roles ?? {})
const totalUsers = computed(() => stats.value?.total_users ?? 0)
const totalProblems = computed(() => stats.value?.total_problems ?? 0)
const totalSubmissions = computed(() => stats.value?.total_submissions ?? 0)
const totalTeams = computed(() => admin.value?.total_teams ?? 0)
const todayReg = computed(() => admin.value?.today_reg ?? 0)
const weekReg = computed(() => admin.value?.week_reg ?? 0)
const recentUsers = computed(() => admin.value?.recent_users ?? [])
const recentSubs = computed(() => stats.value?.recent_submissions ?? [])

const STATUS_MAP = {
  AC: { label: 'AC', cls: 'st-ac' },
  WA: { label: 'WA', cls: 'st-wa' },
  TLE: { label: 'TLE', cls: 'st-tle' },
  MLE: { label: 'MLE', cls: 'st-tle' },
  RE: { label: 'RE', cls: 'st-wa' },
  CE: { label: 'CE', cls: 'st-ce' },
  PE: { label: 'PE', cls: 'st-ce' },
  Pending: { label: '评测中', cls: 'st-pend' },
}
function statusInfo(s) { return STATUS_MAP[s] ?? { label: s, cls: 'st-pend' } }

const ROLE_LABEL = { student: '学生', teacher: '教师', admin: '管理员' }
const ROLE_CLS = { student: 'role-student', teacher: 'role-teacher', admin: 'role-admin' }
</script>

<template>
  <div class="adm-dash" v-if="!loading">
    <h1 class="page-title">管理后台</h1>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="sc-val">{{ totalUsers }}</div>
        <div class="sc-lbl">注册用户</div>
        <div class="sc-sub">今日 +{{ todayReg }} · 本周 +{{ weekReg }}</div>
      </div>
      <div class="stat-card">
        <div class="sc-val accent">{{ totalProblems }}</div>
        <div class="sc-lbl">题目总数</div>
      </div>
      <div class="stat-card">
        <div class="sc-val">{{ totalSubmissions }}</div>
        <div class="sc-lbl">提交总数</div>
      </div>
      <div class="stat-card">
        <div class="sc-val green">{{ totalTeams }}</div>
        <div class="sc-lbl">团队总数</div>
      </div>
    </div>

    <!-- 角色分布 + 快捷入口 -->
    <div class="two-col">
      <!-- 角色分布 -->
      <div class="section-card">
        <h2 class="sec-title">用户角色分布</h2>
        <div class="role-rows">
          <div v-for="(key, i) in ['student','teacher','admin']" :key="key" class="role-row">
            <span :class="['role-badge', ROLE_CLS[key]]">{{ ROLE_LABEL[key] }}</span>
            <div class="role-bar-wrap">
              <div
                class="role-bar"
                :class="ROLE_CLS[key]"
                :style="{ width: totalUsers ? (roles[key] ?? 0) / totalUsers * 100 + '%' : '0%' }"
              ></div>
            </div>
            <span class="role-cnt">{{ roles[key] ?? 0 }}</span>
          </div>
        </div>
      </div>

      <!-- 快捷入口 -->
      <div class="section-card">
        <h2 class="sec-title">快捷管理</h2>
        <div class="quick-links">
          <button class="ql-btn" @click="router.push('/admin/users')">
            <span class="ql-icon">👥</span>
            <span>用户管理</span>
          </button>
          <button class="ql-btn" @click="router.push('/problems')">
            <span class="ql-icon">📝</span>
            <span>题目列表</span>
          </button>
          <button class="ql-btn" @click="router.push('/contests')">
            <span class="ql-icon">🏆</span>
            <span>比赛管理</span>
          </button>
          <button class="ql-btn" @click="router.push('/teacher')">
            <span class="ql-icon">🏫</span>
            <span>团队管理</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 最近注册用户 -->
    <div class="section-card">
      <div class="sec-head">
        <h2 class="sec-title">最近注册</h2>
        <button class="btn-link" @click="router.push('/admin/users')">查看全部 →</button>
      </div>
      <div class="table-wrap">
        <table class="adm-table">
          <thead>
            <tr>
              <th>用户名</th><th>姓名</th><th>学号</th><th>角色</th><th>注册时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in recentUsers" :key="u.id">
              <td>
                <span class="user-link" @click="router.push(`/users/${u.id}`)">{{ u.username }}</span>
              </td>
              <td class="text-muted">{{ u.display_name || '—' }}</td>
              <td class="text-muted">{{ u.student_id || '—' }}</td>
              <td>
                <span :class="['role-badge', ROLE_CLS[u.role]]">{{ ROLE_LABEL[u.role] ?? u.role }}</span>
              </td>
              <td class="text-muted">{{ u.date_joined }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 最近提交 -->
    <div class="section-card">
      <h2 class="sec-title">最近提交</h2>
      <div class="sub-list">
        <div v-for="s in recentSubs" :key="s.id" class="sub-row">
          <span class="sub-user" @click="router.push(`/users/${s.username}`)">{{ s.username }}</span>
          <span class="sub-problem">{{ s.problem_title }}</span>
          <span :class="['sub-status', statusInfo(s.status).cls]">{{ statusInfo(s.status).label }}</span>
          <span class="sub-time text-muted">{{ new Date(s.submitted_at).toLocaleString('zh-CN', { hour12: false }).slice(5) }}</span>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="loading-tip">加载中…</div>
</template>

<style scoped>
.adm-dash { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0; }

.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
@media (max-width: 760px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.2rem 1rem; text-align: center;
}
.sc-val { font-size: 2rem; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.sc-val.accent { color: var(--accent); }
.sc-val.green { color: #10b981; }
.sc-lbl { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem; }
.sc-sub { font-size: 0.72rem; color: var(--text-muted); margin-top: 0.3rem; }

.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
@media (max-width: 760px) { .two-col { grid-template-columns: 1fr; } }

.section-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.25rem;
}
.sec-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.sec-title { font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin: 0 0 1rem; }
.sec-head .sec-title { margin: 0; }
.btn-link { background: none; border: none; color: var(--accent); cursor: pointer; font-size: 0.82rem; padding: 0; }
.btn-link:hover { text-decoration: underline; }

.role-rows { display: flex; flex-direction: column; gap: 0.8rem; }
.role-row { display: flex; align-items: center; gap: 0.75rem; }
.role-bar-wrap { flex: 1; height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden; }
.role-bar { height: 100%; border-radius: 4px; transition: width 0.4s; }
.role-student .role-bar, .role-bar.role-student { background: #6366f1; }
.role-teacher .role-bar, .role-bar.role-teacher { background: #10b981; }
.role-admin .role-bar, .role-bar.role-admin { background: #f59e0b; }
.role-cnt { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); min-width: 2rem; text-align: right; }

.role-badge {
  display: inline-block; padding: 0.1rem 0.5rem; border-radius: 4px;
  font-size: 0.75rem; font-weight: 500; white-space: nowrap;
}
.role-student { background: var(--accent-light); color: var(--accent-text); }
.role-teacher { background: #10b98122; color: #10b981; }
.role-admin { background: #f59e0b22; color: #f59e0b; }

.quick-links { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.ql-btn {
  display: flex; align-items: center; gap: 0.6rem;
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.75rem 1rem; cursor: pointer;
  color: var(--text-secondary); font-size: 0.875rem; transition: all 0.15s; text-align: left;
}
.ql-btn:hover { border-color: var(--accent); color: var(--accent-text); background: var(--accent-light); }
.ql-icon { font-size: 1.1rem; }

.table-wrap { overflow-x: auto; }
.adm-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.adm-table th {
  padding: 0.5rem 0.75rem; text-align: left; color: var(--text-muted);
  font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap;
}
.adm-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.adm-table tr:last-child td { border-bottom: none; }
.user-link { color: var(--accent); cursor: pointer; }
.user-link:hover { text-decoration: underline; }
.text-muted { color: var(--text-muted); }

.sub-list { display: flex; flex-direction: column; gap: 0.4rem; }
.sub-row {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.4rem 0.5rem;
  border-radius: 6px; font-size: 0.875rem; transition: background 0.1s;
}
.sub-row:hover { background: var(--bg-hover); }
.sub-user { color: var(--accent); cursor: pointer; min-width: 80px; }
.sub-user:hover { text-decoration: underline; }
.sub-problem { flex: 1; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-status { min-width: 50px; font-weight: 600; font-size: 0.8rem; text-align: center; }
.sub-time { font-size: 0.78rem; white-space: nowrap; }

.st-ac { color: #10b981; }
.st-wa { color: #f87171; }
.st-tle { color: #f59e0b; }
.st-ce { color: #94a3b8; }
.st-pend { color: var(--text-muted); }

.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }
</style>
