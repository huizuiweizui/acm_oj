<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import StatusBadge from '@/components/StatusBadge.vue'
import api from '@/api/index.js'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const submissions = ref([])
const total = ref(0)
const page = ref(Number(route.query.page) || 1)
const showAll = ref(route.query.all === '1' || !userStore.isLoggedIn)
const loading = ref(false)
const pageSize = 20

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

async function fetchSubmissions() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (showAll.value) params.all = 1
    const { data } = await api.get('/submissions/', { params })
    submissions.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function switchMode(all) {
  showAll.value = all
  page.value = 1
  router.replace({ query: all ? { all: '1' } : {} })
  fetchSubmissions()
}

function goPage(p) {
  page.value = p
  const q = showAll.value ? { all: '1', page: p } : { page: p }
  router.replace({ query: q })
  fetchSubmissions()
  window.scrollTo(0, 0)
}

const totalPages = () => Math.ceil(total.value / pageSize)

onMounted(fetchSubmissions)
</script>

<template>
  <div class="submissions-page">
    <div class="page-header">
      <div class="page-title">评测记录</div>
      <div class="mode-tabs">
        <button
          v-if="userStore.isLoggedIn"
          class="mode-btn" :class="{ active: !showAll }"
          @click="switchMode(false)"
        >我的记录</button>
        <button
          class="mode-btn" :class="{ active: showAll }"
          @click="switchMode(true)"
        >全站记录</button>
      </div>
    </div>

    <div class="table-wrap">
      <div v-if="loading" class="loading">加载中...</div>
      <table v-else class="sub-table">
        <thead>
          <tr>
            <th width="60">#</th>
            <th width="110">用户</th>
            <th>题目</th>
            <th width="130">结果</th>
            <th width="80">语言</th>
            <th width="80">耗时</th>
            <th width="100">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in submissions" :key="s.id" class="sub-row">
            <td class="id-cell">{{ s.id }}</td>
            <td class="user-cell">
              <span
                class="sub-avatar"
                :style="{ background: '#4F46E5' }"
              >{{ (s.username || '?')[0].toUpperCase() }}</span>
              <RouterLink :to="`/users/${s.user_id}`" class="sub-user" @click.stop>
                {{ s.username }}
              </RouterLink>
            </td>
            <td>
              <RouterLink :to="`/problems/${s.problem_id}`" class="problem-link">
                #{{ s.problem_id }} {{ s.problem_title }}
              </RouterLink>
            </td>
            <td><StatusBadge :status="s.status" /></td>
            <td class="lang-cell">{{ s.language }}</td>
            <td class="time-used-cell">{{ s.time_used ? s.time_used + 'ms' : '-' }}</td>
            <td class="time-cell">{{ timeAgo(s.submitted_at) }}</td>
          </tr>
          <tr v-if="!loading && submissions.length === 0">
            <td colspan="7" class="empty">暂无提交记录</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination" v-if="totalPages() > 1">
      <button :disabled="page <= 1" @click="goPage(page - 1)">‹ 上一页</button>
      <span class="page-info">第 {{ page }} / {{ totalPages() }} 页，共 {{ total }} 条</span>
      <button :disabled="page >= totalPages()" @click="goPage(page + 1)">下一页 ›</button>
    </div>
  </div>
</template>

<style scoped>
.submissions-page { padding: 0.5rem 0; }
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1.2rem;
}
.page-title { font-size: 1.5rem; font-weight: 700; color: #e0e0f0; }

.mode-tabs { display: flex; gap: 0.4rem; }
.mode-btn {
  padding: 0.3rem 0.9rem;
  background: #1e1e38; border: 1px solid #3d3d5c;
  border-radius: 6px; color: #c0c0d8; font-size: 0.85rem; cursor: pointer;
}
.mode-btn:hover { border-color: #7c6af7; color: #fff; }
.mode-btn.active { background: #7c6af7; border-color: #7c6af7; color: #fff; }

.table-wrap { background: #16162a; border-radius: 8px; border: 1px solid #2d2d4e; overflow: hidden; }
.loading { padding: 3rem; text-align: center; color: #888; }

.sub-table { width: 100%; border-collapse: collapse; }
.sub-table th {
  padding: 0.7rem 1rem; text-align: left;
  font-size: 0.8rem; color: #888; background: #1a1a30;
  border-bottom: 1px solid #2d2d4e;
}
.sub-table td { padding: 0.65rem 1rem; border-bottom: 1px solid #1e1e38; font-size: 0.88rem; }
.sub-row:last-child td { border-bottom: none; }
.sub-row:hover td { background: #1c1c35; }

.id-cell { color: #555; font-size: 0.8rem; }
.user-cell { display: flex; align-items: center; gap: 0.5rem; }
.sub-avatar {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.65rem; font-weight: 700; color: #fff;
}
.sub-user { color: #a0c4ff; text-decoration: none; font-size: 0.85rem; }
.sub-user:hover { text-decoration: underline; }
.problem-link { color: #a0c4ff; text-decoration: none; }
.problem-link:hover { color: #7c6af7; text-decoration: underline; }
.lang-cell { color: #888; font-size: 0.82rem; }
.time-used-cell { color: #888; font-size: 0.82rem; font-variant-numeric: tabular-nums; }
.time-cell { color: #666; font-size: 0.78rem; white-space: nowrap; }
.empty { text-align: center; padding: 3rem; color: #666; }

.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: 1rem; margin-top: 1.5rem;
}
.pagination button {
  padding: 0.4rem 1rem; background: #1e1e38; border: 1px solid #3d3d5c;
  color: #c0c0d8; border-radius: 6px; cursor: pointer;
}
.pagination button:hover:not(:disabled) { border-color: #7c6af7; color: #fff; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { color: #888; font-size: 0.85rem; }
</style>
