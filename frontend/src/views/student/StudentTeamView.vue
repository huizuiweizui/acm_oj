<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTeam, getAnnouncements, getAssignments, getTeamRank } from '@/api/team'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { diffColor } from '@/utils/difficulty'

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)

const team = ref(null)
const announcements = ref([])
const assignments = ref([])
const ranking = ref([])
const loading = ref(true)
const loadError = ref('')
const activeTab = ref('assignments')

const isCaptain = computed(() => team.value?.my_role === 'captain')
const me = computed(() => ranking.value.find(r => r.is_me))

onMounted(async () => {
  try {
    const { data } = await getTeam(teamId)
    team.value = data
  } catch (e) {
    const s = e.response?.status
    loadError.value = s === 403 ? '你不是该团队成员' : s === 404 ? '团队不存在' : '加载失败，请稍后重试'
    loading.value = false
    return
  }
  // 子模块独立加载：任一失败不影响其他 Tab
  const [ann, asgn, rank] = await Promise.allSettled([
    getAnnouncements(teamId), getAssignments(teamId), getTeamRank(teamId),
  ])
  if (ann.status === 'fulfilled') announcements.value = ann.value.data
  if (asgn.status === 'fulfilled') assignments.value = asgn.value.data
  if (rank.status === 'fulfilled') ranking.value = rank.value.data
  loading.value = false
})

const pinnedAnn = computed(() => announcements.value.filter(a => a.is_pinned))
const normalAnn = computed(() => announcements.value.filter(a => !a.is_pinned))

const doneCount = (a) => a.problems.filter(p => p.ac).length

function fmt(dt) { return dt ? new Date(dt).toLocaleDateString('zh-CN') : '' }
function fmtDateTime(dt) {
  return dt ? new Date(dt).toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
}

// 作业时间窗状态：未开始 / 进行中（倒计时）/ 已截止
function windowInfo(a) {
  const now = Date.now()
  if (a.start_at && new Date(a.start_at) > now) {
    return { cls: 'dl-wait', text: `${fmtDateTime(a.start_at)} 开始` }
  }
  if (!a.deadline) return null
  const diff = new Date(a.deadline) - now
  if (diff < 0) return { cls: 'dl-over', text: '已截止（可补交）' }
  if (diff < 3600000) return { cls: 'dl-urgent', text: `${Math.ceil(diff / 60000)} 分钟后截止` }
  if (diff < 86400000) return { cls: 'dl-urgent', text: `${Math.ceil(diff / 3600000)} 小时后截止` }
  return { cls: 'dl-ok', text: `${Math.ceil(diff / 86400000)} 天后截止` }
}

const STATE = {
  ontime: { icon: '✓', cls: 'st-ontime', tip: '按时完成' },
  late: { icon: '🕐', cls: 'st-late', tip: '补交完成' },
  tried: { icon: '✗', cls: 'st-tried', tip: '尝试中' },
  none: { icon: '○', cls: 'st-none', tip: '未开始' },
}
</script>

<template>
  <div class="st-view" v-if="!loading && team">

    <!-- 顶部 -->
    <div class="st-header">
      <button class="btn-back" @click="router.push('/my-teams')">← 我的团队</button>
      <div class="header-info">
        <h1 class="st-name">
          {{ team.name }}
          <span v-if="isCaptain" class="captain-badge">👑 队长</span>
        </h1>
        <p class="st-desc">
          教师 {{ team.creator_username }} · {{ team.member_count }} 人
          <template v-if="me"> · 我的排名 <b>{{ me.rank }}</b> / {{ ranking.length }}（AC {{ me.total_ac }}）</template>
        </p>
        <p v-if="team.description" class="st-desc">{{ team.description }}</p>
      </div>
      <!-- 队长快捷入口（只读） -->
      <div v-if="isCaptain" class="captain-nav">
        <button class="btn-captain" @click="router.push(`/teacher/teams/${teamId}`)">
          成员 / 作业情况
        </button>
        <button class="btn-captain" @click="router.push(`/teacher/teams/${teamId}/dashboard`)">
          团队总览 →
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button :class="['tab', activeTab === 'assignments' && 'tab-active']" @click="activeTab = 'assignments'">
        作业（{{ assignments.length }}）
      </button>
      <button :class="['tab', activeTab === 'announcements' && 'tab-active']" @click="activeTab = 'announcements'">
        公告
        <span v-if="pinnedAnn.length > 0" class="tab-badge">{{ pinnedAnn.length }}</span>
      </button>
      <button :class="['tab', activeTab === 'rank' && 'tab-active']" @click="activeTab = 'rank'">
        团队排行
      </button>
    </div>

    <!-- 公告 Tab -->
    <div v-if="activeTab === 'announcements'">
      <div v-if="announcements.length === 0" class="empty-tip">暂无公告</div>
      <div v-else class="ann-list">
        <div v-for="a in [...pinnedAnn, ...normalAnn]" :key="a.id" :class="['ann-card', a.is_pinned && 'ann-pinned']">
          <div class="ann-head">
            <span v-if="a.is_pinned" class="ann-pin-icon">📌</span>
            <span class="ann-title">{{ a.title }}</span>
            <span class="ann-date text-muted">{{ a.created_by }} · {{ fmt(a.created_at) }}</span>
          </div>
          <MarkdownRenderer v-if="a.content" :content="a.content" class="ann-content" />
        </div>
      </div>
    </div>

    <!-- 作业 Tab -->
    <div v-if="activeTab === 'assignments'">
      <div v-if="assignments.length === 0" class="empty-tip">暂无作业</div>
      <div v-else class="asgn-list">
        <div v-for="a in assignments" :key="a.id" class="asgn-card">
          <div class="asgn-head">
            <span class="asgn-title">{{ a.title }}</span>
            <div class="asgn-right">
              <span class="asgn-progress">
                <span class="prog-done">{{ doneCount(a) }}</span>
                <span class="prog-sep">/</span>
                <span class="prog-total">{{ a.problem_count }}</span>
              </span>
              <span v-if="windowInfo(a)" :class="['asgn-deadline', windowInfo(a).cls]">
                {{ windowInfo(a).text }}
              </span>
            </div>
          </div>

          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: a.problem_count ? (doneCount(a) / a.problem_count * 100) + '%' : '0%' }"
            ></div>
          </div>

          <p v-if="a.start_at || a.deadline" class="asgn-window text-muted">
            <span v-if="a.start_at">开始 {{ fmtDateTime(a.start_at) }}</span>
            <span v-if="a.start_at && a.deadline"> · </span>
            <span v-if="a.deadline">截止 {{ fmtDateTime(a.deadline) }}</span>
          </p>
          <p v-if="a.description" class="asgn-desc text-muted">{{ a.description }}</p>

          <div v-if="a.problems.length > 0" class="prob-list">
            <RouterLink
              v-for="p in a.problems"
              :key="p.id"
              :to="`/problems/${p.id}`"
              :class="['prob-item', STATE[p.state].cls]"
              :title="STATE[p.state].tip + (p.attempts ? `（${p.attempts} 次提交）` : '')"
            >
              <span class="prob-check">{{ STATE[p.state].icon }}</span>
              <span class="prob-title">#{{ p.id }} {{ p.title }}</span>
              <span v-if="p.state === 'late'" class="late-tag">补交</span>
              <span class="prob-diff" :style="{ color: diffColor(p.difficulty) }">{{ p.difficulty }}</span>
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- 排行 Tab：仅名次与 AC 数，不展示他人明细 -->
    <div v-if="activeTab === 'rank'">
      <div v-if="ranking.length === 0" class="empty-tip">暂无数据</div>
      <div v-else class="rank-list">
        <div v-for="r in ranking" :key="r.user_id" :class="['rank-row', r.is_me && 'rank-me']">
          <span :class="['rank-badge', r.rank <= 3 && `rank-${r.rank}`]">{{ r.rank }}</span>
          <span class="rank-name">
            {{ r.display_name }}
            <span v-if="r.role === 'captain'" title="队长">👑</span>
            <span v-if="r.is_me" class="me-tag">我</span>
          </span>
          <span class="rank-ac"><b>{{ r.total_ac }}</b> AC</span>
        </div>
      </div>
    </div>

  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>
  <div v-else class="loading-tip error-tip">
    {{ loadError }}
    <button class="btn-back" @click="router.push('/my-teams')">← 我的团队</button>
  </div>
</template>

<style scoped>
.st-view { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }

.st-header { display: flex; align-items: flex-start; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; margin-top: 0.2rem; transition: border-color 0.15s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.header-info { flex: 1; }
.st-name { font-size: 1.35rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.2rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.st-desc { font-size: 0.82rem; color: var(--text-muted); margin: 0 0 0.15rem; }
.st-desc b { color: var(--accent); }
.captain-badge { font-size: 0.78rem; background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; border-radius: 4px; padding: 0.1rem 0.5rem; }
.captain-nav { display: flex; flex-direction: column; gap: 0.4rem; flex-shrink: 0; }
.btn-captain {
  background: none; border: 1px solid rgba(99,102,241,0.4); color: var(--accent);
  padding: 0.3rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem;
  white-space: nowrap; transition: all 0.15s;
}
.btn-captain:hover { background: rgba(99,102,241,0.1); border-color: var(--accent); }

.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); }
.tab {
  background: none; border: none; border-bottom: 2px solid transparent;
  padding: 0.6rem 1.25rem; color: var(--text-secondary); cursor: pointer;
  font-size: 0.9rem; display: flex; align-items: center; gap: 0.4rem;
  transition: color 0.15s, border-color 0.15s;
}
.tab:hover { color: var(--text-primary); }
.tab-active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-badge {
  background: #f59e0b; color: #fff; border-radius: 10px;
  padding: 0 0.4rem; font-size: 0.7rem; font-weight: 700; line-height: 1.4;
}

/* Announcements */
.ann-list { display: flex; flex-direction: column; gap: 0.75rem; }
.ann-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem;
}
.ann-pinned { border-color: #f59e0b55; background: rgba(245,158,11,0.04); }
.ann-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
.ann-pin-icon { font-size: 0.9rem; }
.ann-title { flex: 1; font-weight: 600; color: var(--text-primary); }
.ann-date { font-size: 0.78rem; }
.ann-content { font-size: 0.875rem; color: var(--text-secondary); line-height: 1.6; }

/* Assignments */
.asgn-list { display: flex; flex-direction: column; gap: 1rem; }
.asgn-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 1.1rem; display: flex; flex-direction: column; gap: 0.6rem;
}
.asgn-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.asgn-title { font-weight: 600; color: var(--text-primary); font-size: 1rem; }
.asgn-right { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }
.asgn-progress { font-size: 0.9rem; font-family: monospace; }
.prog-done { color: #10b981; font-weight: 700; }
.prog-sep { color: var(--text-muted); }
.prog-total { color: var(--text-muted); }
.asgn-deadline { font-size: 0.78rem; padding: 0.1rem 0.5rem; border-radius: 4px; font-weight: 500; }
.dl-ok { background: #10b98122; color: #10b981; }
.dl-urgent { background: #f59e0b22; color: #f59e0b; }
.dl-over { background: #f8717122; color: #f87171; }
.dl-wait { background: rgba(99,102,241,0.12); color: var(--accent); }

.progress-bar { height: 4px; background: var(--bg-secondary); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: #10b981; border-radius: 2px; transition: width 0.3s; }

.asgn-window, .asgn-desc { font-size: 0.82rem; margin: 0; }
.asgn-desc { white-space: pre-wrap; }

.prob-list { display: flex; flex-direction: column; gap: 0.3rem; border-top: 1px solid var(--border); padding-top: 0.6rem; }
.prob-item {
  display: flex; align-items: center; gap: 0.6rem; padding: 0.3rem 0.4rem;
  border-radius: 4px; text-decoration: none; transition: background 0.1s;
}
.prob-item:hover { background: var(--bg-hover); }
.prob-check { font-size: 0.85rem; width: 1.1rem; text-align: center; color: var(--text-muted); }
.st-ontime .prob-check { color: #10b981; }
.st-late .prob-check { color: #f59e0b; }
.st-tried .prob-check { color: #f87171; }
.st-ontime .prob-title, .st-late .prob-title { color: var(--text-secondary); }
.prob-title { flex: 1; font-size: 0.875rem; color: var(--text-primary); }
.late-tag { font-size: 0.7rem; color: #f59e0b; border: 1px solid #f59e0b55; border-radius: 3px; padding: 0 0.3rem; }
.prob-diff { font-size: 0.78rem; white-space: nowrap; }

/* Rank */
.rank-list { display: flex; flex-direction: column; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.rank-row { display: flex; align-items: center; gap: 0.9rem; padding: 0.6rem 1rem; border-bottom: 1px solid var(--border); }
.rank-row:last-child { border-bottom: none; }
.rank-me { background: var(--accent-light); }
.rank-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.65rem; height: 1.65rem; border-radius: 50%; font-size: 0.78rem; flex-shrink: 0;
  background: var(--bg-secondary); color: var(--text-muted);
}
.rank-1 { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b55; }
.rank-2 { background: rgba(148,163,184,0.12); color: #94a3b8; border: 1px solid rgba(148,163,184,0.3); }
.rank-3 { background: #cd7c2222; color: #cd7c22; border: 1px solid #cd7c2255; }
.rank-name { flex: 1; color: var(--text-primary); font-size: 0.9rem; display: flex; align-items: center; gap: 0.35rem; }
.me-tag { font-size: 0.7rem; color: #fff; background: var(--accent); border-radius: 3px; padding: 0 0.35rem; }
.rank-ac { font-size: 0.85rem; color: var(--text-muted); }
.rank-ac b { color: var(--text-primary); font-family: var(--font-mono); }

.text-muted { color: var(--text-muted); }
.empty-tip { text-align: center; padding: 3rem 2rem; color: var(--text-muted); }
.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }
.error-tip { color: #f87171; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
</style>
