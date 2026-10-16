<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProblems } from '@/api/problems'
import DifficultyBadge from '@/components/DifficultyBadge.vue'

const route = useRoute()
const router = useRouter()

const problems = ref([])
const total = ref(0)
const loading = ref(false)

const keyword = ref(route.query.keyword || '')
const difficulty = ref(route.query.difficulty || '')
const tag = ref(route.query.tag || '')
const page = ref(Number(route.query.page) || 1)
const pageSize = 20

const difficulties = [
  '入门', '普及-', '普及/提高-', '普及+/提高',
  '提高+/省选-', '省选/NOI-', 'NOI/NOI+/CTSC', '暂无评定',
]

const statusIcon  = { ac: '✓', tried: '·', todo: '' }
const statusBg    = { ac: 'var(--status-ac-bg)', tried: 'var(--status-tle-bg)', todo: 'transparent' }
const statusColor = { ac: 'var(--status-ac-text)', tried: 'var(--status-tle-text)', todo: 'transparent' }

async function fetchProblems() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (keyword.value) params.keyword = keyword.value
    if (difficulty.value) params.difficulty = difficulty.value
    if (tag.value) params.tag = tag.value

    const { data } = await getProblems(params)
    problems.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function syncQuery() {
  const q = {}
  if (keyword.value) q.keyword = keyword.value
  if (difficulty.value) q.difficulty = difficulty.value
  if (tag.value) q.tag = tag.value
  if (page.value > 1) q.page = page.value
  router.replace({ query: q })
}

function search() {
  page.value = 1
  syncQuery()
  fetchProblems()
}

function setDifficulty(d) {
  difficulty.value = difficulty.value === d ? '' : d
  search()
}

function setTag(t) {
  tag.value = tag.value === t ? '' : t
  search()
}

function goPage(p) {
  page.value = p
  syncQuery()
  fetchProblems()
  window.scrollTo(0, 0)
}

const totalPages = () => Math.ceil(total.value / pageSize)

onMounted(fetchProblems)
</script>

<template>
  <div class="problem-list">
    <div class="page-title">题库</div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="keyword"
        class="search-input"
        placeholder="搜索题号或题目名"
        @keyup.enter="search"
      />
      <button class="btn-search" @click="search">搜索</button>
      <button v-if="keyword || difficulty || tag" class="btn-clear" @click="keyword=''; difficulty=''; tag=''; search()">
        清除筛选
      </button>
    </div>

    <!-- 难度筛选 -->
    <div class="filter-row">
      <span class="filter-label">难度：</span>
      <button
        v-for="d in difficulties" :key="d"
        class="filter-chip"
        :class="{ active: difficulty === d }"
        @click="setDifficulty(d)"
      >{{ d }}</button>
    </div>

    <!-- 题目表格 -->
    <div class="table-wrap">
      <div v-if="loading" class="loading">加载中...</div>
      <table v-else class="problem-table">
        <thead>
          <tr>
            <th width="48"></th>
            <th width="72">#</th>
            <th>题目名称</th>
            <th width="160">难度</th>
            <th width="90">通过率</th>
            <th>标签</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in problems" :key="p.id">
            <td class="status-cell">
              <span
                class="status-dot"
                :style="{ background: statusBg[p.user_status], color: statusColor[p.user_status] }"
                :title="p.user_status === 'ac' ? '已通过' : p.user_status === 'tried' ? '已尝试' : ''"
              >{{ statusIcon[p.user_status] }}</span>
            </td>
            <td class="id-cell">{{ p.id }}</td>
            <td>
              <RouterLink :to="`/problems/${p.id}`" class="problem-link">
                {{ p.title }}
              </RouterLink>
            </td>
            <td><DifficultyBadge :difficulty="p.difficulty" /></td>
            <td class="rate-cell">
              {{ p.submit_count ? (p.ac_rate + '%') : '-' }}
            </td>
            <td>
              <span
                v-for="t in p.tags" :key="t.id"
                class="tag-chip"
                :class="{ active: tag === t.name }"
                @click="setTag(t.name)"
              >{{ t.name }}</span>
            </td>
          </tr>
          <tr v-if="!loading && problems.length === 0">
            <td colspan="6" class="empty">没有找到符合条件的题目</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="totalPages() > 1">
      <button :disabled="page <= 1" @click="goPage(page - 1)">‹ 上一页</button>
      <span class="page-info">第 {{ page }} / {{ totalPages() }} 页，共 {{ total }} 题</span>
      <button :disabled="page >= totalPages()" @click="goPage(page + 1)">下一页 ›</button>
    </div>
    <div class="total-tip" v-else-if="total > 0">共 {{ total }} 题</div>
  </div>
</template>

<style scoped>
.problem-list { padding: 0.5rem 0; }
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.2rem; color: var(--text-primary); }

.search-bar { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.search-input {
  flex: 1; max-width: 360px;
  padding: 0.45rem 0.8rem;
  background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text-primary); font-size: 0.9rem;
}
.search-input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-light); }
.btn-search {
  padding: 0.45rem 1.2rem; background: var(--accent); color: #fff;
  border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;
}
.btn-search:hover { background: var(--accent-hover); }
.btn-clear {
  padding: 0.45rem 1rem; background: transparent; color: var(--text-muted);
  border: 1px solid var(--border); border-radius: 6px; cursor: pointer; font-size: 0.85rem;
}
.btn-clear:hover { border-color: var(--accent); color: var(--text-primary); }

.filter-row { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.2rem; }
.filter-label { color: var(--text-muted); font-size: 0.85rem; }
.filter-chip {
  padding: 0.2rem 0.7rem; border-radius: 999px;
  background: var(--bg-input); border: 1px solid var(--border);
  color: var(--text-secondary); font-size: 0.8rem; cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.filter-chip:hover { border-color: var(--accent); color: var(--text-primary); }
.filter-chip.active { background: var(--accent-light); border-color: var(--accent); color: var(--accent-text); }

.table-wrap { background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }
.loading { padding: 3rem; text-align: center; color: var(--text-muted); }

.problem-table { width: 100%; border-collapse: collapse; }
.problem-table th {
  padding: 8px 16px; text-align: left;
  font-size: 12.5px; color: var(--text-secondary); font-weight: 500;
  background: var(--bg-page); border-bottom: 1px solid var(--border);
  position: sticky; top: 0;
}
.problem-table td { padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 14px; line-height: 1.4; }
.problem-table tr:last-child td { border-bottom: none; }
.problem-table tr:hover td { background: var(--bg-hover); }

.status-cell { text-align: center; }
.status-dot {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  font-size: 11px; font-weight: 700;
}
.id-cell { color: var(--text-muted); font-size: 13px; font-family: var(--font-mono); }
.problem-link { color: var(--text-primary); text-decoration: none; font-size: 14px; }
.problem-link:hover { color: var(--accent-text); }
.rate-cell { color: var(--text-muted); font-size: 13px; font-family: var(--font-mono); }
.empty { text-align: center; padding: 3rem; color: var(--text-muted); }

.tag-chip {
  display: inline-block; margin: 1px 2px;
  padding: 1px 7px; border-radius: 6px;
  background: var(--bg-hover); color: var(--text-secondary); font-size: 12px; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.tag-chip:hover { background: var(--bg-active); color: var(--accent-text); }
.tag-chip.active { background: var(--accent-light); color: var(--accent-text); }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.5rem; }
.pagination button {
  padding: 0.4rem 1rem; background: var(--bg-input); border: 1px solid var(--border);
  color: var(--text-secondary); border-radius: 6px; cursor: pointer; font-size: 0.9rem;
  transition: border-color 0.15s, color 0.15s;
}
.pagination button:hover:not(:disabled) { border-color: var(--accent); color: var(--text-primary); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { color: var(--text-muted); font-size: 0.85rem; }
.total-tip { text-align: center; color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem; }
</style>
