<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getTeam, getAnnouncements, getAssignments,
} from '@/api/team'

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)

const team = ref(null)
const announcements = ref([])
const assignments = ref([])
const loading = ref(true)
const activeTab = ref('announcements')

const isCaptain = computed(() => team.value?.my_role === 'captain')

onMounted(async () => {
  try {
    const [td, ann, asgn] = await Promise.all([
      getTeam(teamId),
      getAnnouncements(teamId),
      getAssignments(teamId),
    ])
    team.value = td.data
    announcements.value = ann.data
    assignments.value = asgn.data
  } finally {
    loading.value = false
  }
})

const pinnedAnn = computed(() => announcements.value.filter(a => a.is_pinned))
const normalAnn = computed(() => announcements.value.filter(a => !a.is_pinned))

const DIFF_COLORS = {
  '暂无评定': '#bfbfbf', '入门': '#fe4c61',
  '普及-': '#f39c11', '普及/提高-': '#ffc116', '普及+/提高': '#52c41a',
  '提高+/省选-': '#3498db', '省选/NOI-': '#9d3dcf', 'NOI/NOI+/CTSC': '#0e1d69',
}
function diffColor(d) { return DIFF_COLORS[d] ?? '#6b7280' }

function fmt(dt) { return dt ? new Date(dt).toLocaleDateString('zh-CN') : '' }
function fmtDeadline(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const now = new Date()
  const diff = d - now
  if (diff < 0) return '已截止'
  if (diff < 86400000) return `${Math.ceil(diff / 3600000)} 小时后截止`
  return `${Math.ceil(diff / 86400000)} 天后截止`
}
function deadlineClass(dt) {
  if (!dt) return ''
  const diff = new Date(dt) - new Date()
  if (diff < 0) return 'dl-over'
  if (diff < 86400000) return 'dl-urgent'
  return 'dl-ok'
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
        <p v-if="team.description" class="st-desc">{{ team.description }}</p>
      </div>
      <!-- 队长快捷入口 -->
      <div v-if="isCaptain" class="captain-nav">
        <button class="btn-captain" @click="router.push(`/teacher/teams/${teamId}`)">
          成员管理
        </button>
        <button class="btn-captain" @click="router.push(`/teacher/teams/${teamId}/dashboard`)">
          团队排行 →
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button :class="['tab', activeTab === 'announcements' && 'tab-active']" @click="activeTab = 'announcements'">
        公告
        <span v-if="pinnedAnn.length > 0" class="tab-badge">{{ pinnedAnn.length }}</span>
      </button>
      <button :class="['tab', activeTab === 'assignments' && 'tab-active']" @click="activeTab = 'assignments'">
        作业（{{ assignments.length }}）
      </button>
    </div>

    <!-- 公告 Tab -->
    <div v-if="activeTab === 'announcements'">
      <div v-if="announcements.length === 0" class="empty-tip">暂无公告</div>
      <div v-else class="ann-list">
        <!-- 置顶 -->
        <div v-for="a in pinnedAnn" :key="a.id" class="ann-card ann-pinned">
          <div class="ann-head">
            <span class="ann-pin-icon">📌</span>
            <span class="ann-title">{{ a.title }}</span>
            <span class="ann-date text-muted">{{ fmt(a.created_at) }}</span>
          </div>
          <div v-if="a.content" class="ann-content">{{ a.content }}</div>
        </div>
        <!-- 普通 -->
        <div v-for="a in normalAnn" :key="a.id" class="ann-card">
          <div class="ann-head">
            <span class="ann-title">{{ a.title }}</span>
            <span class="ann-date text-muted">{{ fmt(a.created_at) }}</span>
          </div>
          <div v-if="a.content" class="ann-content">{{ a.content }}</div>
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
              <!-- 完成进度 -->
              <span class="asgn-progress">
                <span class="prog-done">{{ a.problems.filter(p => p.ac).length }}</span>
                <span class="prog-sep">/</span>
                <span class="prog-total">{{ a.problem_count }}</span>
              </span>
              <span v-if="a.deadline" :class="['asgn-deadline', deadlineClass(a.deadline)]">
                {{ fmtDeadline(a.deadline) }}
              </span>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: a.problem_count ? (a.problems.filter(p=>p.ac).length / a.problem_count * 100) + '%' : '0%' }"
            ></div>
          </div>

          <p v-if="a.description" class="asgn-desc text-muted">{{ a.description }}</p>

          <!-- 题目列表 -->
          <div v-if="a.problems.length > 0" class="prob-list">
            <a
              v-for="p in a.problems"
              :key="p.id"
              class="prob-item"
              :class="{ 'prob-ac': p.ac }"
              :href="`/problems/${p.id}`"
              target="_blank"
            >
              <span class="prob-check">{{ p.ac ? '✓' : '○' }}</span>
              <span class="prob-title">#{{ p.id }} {{ p.title }}</span>
              <span class="prob-diff" :style="{ color: diffColor(p.difficulty) }">{{ p.difficulty }}</span>
            </a>
          </div>
        </div>
      </div>
    </div>

  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>
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
.st-desc { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
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
.ann-content {
  font-size: 0.875rem; color: var(--text-secondary); white-space: pre-wrap;
  line-height: 1.6; margin: 0;
}

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

.progress-bar { height: 4px; background: var(--bg-secondary); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: #10b981; border-radius: 2px; transition: width 0.3s; }

.asgn-desc { font-size: 0.85rem; margin: 0; }

.prob-list { display: flex; flex-direction: column; gap: 0.3rem; border-top: 1px solid var(--border); padding-top: 0.6rem; }
.prob-item {
  display: flex; align-items: center; gap: 0.6rem; padding: 0.3rem 0.4rem;
  border-radius: 4px; text-decoration: none; transition: background 0.1s;
}
.prob-item:hover { background: var(--bg-hover); }
.prob-check { font-size: 0.85rem; width: 1.1rem; text-align: center; color: var(--text-muted); }
.prob-ac .prob-check { color: #10b981; }
.prob-ac .prob-title { color: var(--text-secondary); }
.prob-title { flex: 1; font-size: 0.875rem; color: var(--text-primary); }
.prob-diff { font-size: 0.78rem; white-space: nowrap; }
.text-muted { color: var(--text-muted); }
.empty-tip { text-align: center; padding: 3rem 2rem; color: var(--text-muted); }
.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }
</style>
