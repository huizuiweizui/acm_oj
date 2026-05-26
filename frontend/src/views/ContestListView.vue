<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getContests } from '@/api/contests'

const route = useRoute()
const router = useRouter()

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
  running:  { label: '进行中', color: '#2ecc71' },
  upcoming: { label: '即将开始', color: '#3498db' },
  ended:    { label: '已结束', color: '#888' },
}

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function duration(start, end) {
  const ms = new Date(end) - new Date(start)
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  return h ? `${h}h ${m}m` : `${m}m`
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
    <div class="page-title">比赛</div>

    <!-- 标签页 -->
    <div class="tabs">
      <button
        v-for="t in tabs" :key="t.key"
        class="tab-btn"
        :class="{ active: tab === t.key }"
        @click="switchTab(t.key)"
      >{{ t.label }}</button>
    </div>

    <!-- 列表 -->
    <div class="contest-cards" v-if="!loading">
      <div v-if="contests.length === 0" class="empty">暂无比赛</div>

      <div
        v-for="c in contests" :key="c.id"
        class="contest-card"
        @click="router.push(`/contests/${c.id}`)"
      >
        <div class="card-left">
          <div class="card-title">{{ c.title }}</div>
          <div class="card-meta">
            <span class="rule-badge">{{ c.rule_type }}</span>
            <span class="time-range">
              {{ formatTime(c.start_time) }} ~ {{ formatTime(c.end_time) }}
            </span>
            <span class="duration">时长 {{ duration(c.start_time, c.end_time) }}</span>
          </div>
        </div>
        <div class="card-right">
          <span
            class="status-badge"
            :style="{ color: statusCfg[c.status]?.color, borderColor: statusCfg[c.status]?.color }"
          >{{ statusCfg[c.status]?.label ?? c.status }}</span>
        </div>
      </div>
    </div>

    <div v-else class="loading">加载中...</div>

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
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.2rem; color: #e0e0f0; }

.tabs {
  display: flex;
  gap: 0.3rem;
  border-bottom: 1px solid #2d2d4e;
  margin-bottom: 1.5rem;
}
.tab-btn {
  padding: 0.55rem 1.2rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #888;
  font-size: 0.9rem;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s;
}
.tab-btn:hover { color: #e0e0f0; }
.tab-btn.active { color: #a78bfa; border-bottom-color: #a78bfa; font-weight: 600; }

.contest-cards { display: flex; flex-direction: column; gap: 0.75rem; }
.empty { text-align: center; padding: 3rem; color: #666; }
.loading { text-align: center; padding: 3rem; color: #888; }

.contest-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #16162a;
  border: 1px solid #2d2d4e;
  border-radius: 8px;
  padding: 1.1rem 1.4rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.contest-card:hover {
  border-color: #7c6af7;
  background: #1c1c35;
}
.card-left { display: flex; flex-direction: column; gap: 0.5rem; flex: 1; }
.card-title { font-size: 1rem; font-weight: 600; color: #e0e0f0; }
.card-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.82rem;
  color: #888;
}
.rule-badge {
  background: #1e1e38;
  border: 1px solid #3d3d5c;
  color: #a78bfa;
  padding: 0.1rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.time-range, .duration { color: #888; }

.card-right { margin-left: 1.5rem; flex-shrink: 0; }
.status-badge {
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid;
  padding: 0.2rem 0.65rem;
  border-radius: 4px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}
.pagination button {
  padding: 0.4rem 1rem;
  background: #1e1e38;
  border: 1px solid #3d3d5c;
  color: #c0c0d8;
  border-radius: 6px;
  cursor: pointer;
}
.pagination button:hover:not(:disabled) { border-color: #7c6af7; color: #fff; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { color: #888; font-size: 0.85rem; }
</style>
