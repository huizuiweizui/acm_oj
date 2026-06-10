<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { getContests } from '@/api/contests'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { canCreateContest } = storeToRefs(userStore)

const tab = ref(route.query.tab || 'all')
const contests = ref([])
const total = ref(0)
const page = ref(Number(route.query.page) || 1)
const loading = ref(false)
const pageSize = 10

const tabs = [
  { key: 'all',      label: '全部' },
  { key: 'running',  label: '进行中' },
  { key: 'upcoming', label: '即将开始' },
  { key: 'ended',    label: '已结束' },
]

const statusCfg = {
  running:  { label: '进行中', cls: 'status-running' },
  upcoming: { label: '即将开始', cls: 'status-upcoming' },
  ended:    { label: '已结束', cls: 'status-ended' },
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

async function fetchContests() {
  loading.value = true
  try {
    const { data } = await getContests({ tab: tab.value, page: page.value, page_size: pageSize })
    contests.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function switchTab(key) {
  tab.value = key
  page.value = 1
  router.replace({ query: { tab: key } })
  fetchContests()
}

function goPage(p) {
  page.value = p
  router.replace({ query: { tab: tab.value, page: p } })
  fetchContests()
  window.scrollTo(0, 0)
}

const totalPages = () => Math.ceil(total.value / pageSize)

onMounted(fetchContests)
</script>

<template>
  <div class="contest-list">

    <!-- 页头 -->
    <div class="page-header">
      <h1 class="page-title">比赛</h1>
      <button
        v-if="canCreateContest"
        class="btn-create"
        @click="router.push('/contests/create')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        创建比赛
      </button>
    </div>

    <!-- Tab 筛选 -->
    <div class="contest-tabs">
      <button
        v-for="t in tabs" :key="t.key"
        class="contest-tab"
        :class="{ active: tab === t.key }"
        @click="switchTab(t.key)"
      >{{ t.label }}</button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading">加载中...</div>

    <!-- 空状态 -->
    <div v-else-if="contests.length === 0" class="contest-empty">
      <div class="empty-icon">{{ tab === 'all' ? '🏟️' : '🔍' }}</div>
      <div class="empty-title">{{ tab === 'all' ? '暂时还没有比赛' : '没有符合条件的比赛' }}</div>
      <div class="empty-desc">{{ tab === 'all' ? '点击右上角按钮创建第一场编程竞赛' : '换个筛选条件试试' }}</div>
    </div>

    <!-- 卡片网格 -->
    <div v-else class="contest-grid">
      <div
        v-for="c in contests" :key="c.id"
        class="contest-card-new"
        @click="router.push(`/contests/${c.id}`)"
      >
        <div class="contest-card-top">
          <div class="contest-card-title">{{ c.title }}</div>
          <span class="status-badge" :class="statusCfg[c.status]?.cls">
            {{ statusCfg[c.status]?.label ?? c.status }}
          </span>
        </div>
        <div class="contest-card-meta">
          <div class="meta-row">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            编程题 × {{ c.problem_count }}
          </div>
          <div class="meta-row">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {{ formatTime(c.start_time) }} ~ {{ new Date(c.end_time).toLocaleTimeString('zh-CN', { hour:'2-digit', minute:'2-digit' }) }}
          </div>
          <div class="meta-row" v-if="!c.is_public">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            私有赛
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="totalPages() > 1">
      <button :disabled="page <= 1" @click="goPage(page - 1)">‹ 上一页</button>
      <span class="page-info">第 {{ page }} / {{ totalPages() }} 页</span>
      <button :disabled="page >= totalPages()" @click="goPage(page + 1)">下一页 ›</button>
    </div>

  </div>
</template>

<style scoped>
.contest-list { padding: 0.5rem 0; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1.2rem;
}
.page-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.btn-create {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--accent); color: #fff; border: none;
  border-radius: 8px; padding: 0.5rem 1.1rem;
  font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn-create:hover { opacity: 0.85; }

/* Tabs */
.contest-tabs {
  display: flex; gap: 4px;
  background: var(--bg-secondary); border-radius: 10px;
  padding: 4px; margin-bottom: 1.5rem; width: fit-content;
}
.contest-tab {
  padding: 0.4rem 1rem; border-radius: 7px;
  font-size: 0.875rem; font-weight: 500;
  color: var(--text-muted); background: none; border: none; cursor: pointer; transition: all 0.15s;
}
.contest-tab:hover { color: var(--text-primary); }
.contest-tab.active {
  background: var(--bg-card); color: var(--text-primary);
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
}

.loading { text-align: center; padding: 3rem; color: var(--text-muted); }

/* 空状态 */
.contest-empty { text-align: center; padding: 5rem 1rem; }
.empty-icon { font-size: 3.5rem; margin-bottom: 1rem; opacity: 0.5; }
.empty-title { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
.empty-desc { font-size: 0.875rem; color: var(--text-muted); }

/* 卡片网格 */
.contest-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.contest-card-new {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; padding: 1.2rem 1.4rem;
  cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s;
}
.contest-card-new:hover {
  box-shadow: 0 4px 18px rgba(0,0,0,.1);
  border-color: var(--accent);
}
.contest-card-top {
  display: flex; align-items: flex-start;
  justify-content: space-between; gap: 10px; margin-bottom: 12px;
}
.contest-card-title {
  font-size: 1rem; font-weight: 600; color: var(--text-primary); line-height: 1.4; flex: 1;
}

.status-badge {
  flex-shrink: 0; display: inline-block;
  padding: 0.2rem 0.65rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 600; white-space: nowrap;
}
.status-running  { background: rgba(34,197,94,.15);  color: #22c55e; }
.status-upcoming { background: rgba(99,102,241,.15); color: #6366f1; }
.status-ended    { background: rgba(107,114,128,.15);color: #6b7280; }

.contest-card-meta { display: flex; flex-direction: column; gap: 5px; }
.meta-row {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.8rem; color: var(--text-muted);
}
.meta-row svg { flex-shrink: 0; opacity: 0.7; }

/* 分页 */
.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: 1rem; margin-top: 2rem;
}
.pagination button {
  padding: 0.4rem 1rem; background: var(--bg-input); border: 1px solid var(--border);
  color: var(--text-secondary); border-radius: 6px; cursor: pointer; transition: border-color 0.15s, color 0.15s;
}
.pagination button:hover:not(:disabled) { border-color: var(--accent); color: var(--text-primary); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { color: var(--text-muted); font-size: 0.85rem; }

@media (max-width: 700px) {
  .contest-grid { grid-template-columns: 1fr; }
}
</style>
