<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDiscussions } from '@/api/discussions'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const discussions = ref([])
const total = ref(0)
const page = ref(Number(route.query.page) || 1)
const loading = ref(false)
const pageSize = 20

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso)
  const m = Math.floor(diff / 60000)
  if (m < 1)   return '刚刚'
  if (m < 60)  return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24)  return `${h} 小时前`
  const d = Math.floor(h / 24)
  if (d < 30)  return `${d} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

async function fetchDiscussions() {
  loading.value = true
  try {
    const { data } = await getDiscussions({ page: page.value, page_size: pageSize })
    discussions.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function goPage(p) {
  page.value = p
  router.replace({ query: { page: p } })
  fetchDiscussions()
  window.scrollTo(0, 0)
}

const totalPages = () => Math.ceil(total.value / pageSize)

onMounted(fetchDiscussions)
</script>

<template>
  <div class="discussion-list">
    <div class="page-header">
      <div class="page-title">讨论区</div>
      <button
        v-if="userStore.isLoggedIn"
        class="btn-new"
        @click="router.push('/discussions/create')"
      >+ 发帖</button>
      <RouterLink v-else to="/login" class="btn-new">登录后发帖</RouterLink>
    </div>

    <div class="table-wrap" v-if="!loading">
      <div v-if="discussions.length === 0" class="empty">暂无讨论，来发第一帖吧</div>
      <table v-else class="disc-table">
        <thead>
          <tr>
            <th>标题</th>
            <th width="100">关联题目</th>
            <th width="90">作者</th>
            <th width="70">回复</th>
            <th width="100">发布时间</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="d in discussions" :key="d.id"
            class="disc-row"
            @click="router.push(`/discussions/${d.id}`)"
          >
            <td class="title-cell">{{ d.title }}</td>
            <td class="problem-cell">
              <RouterLink
                v-if="d.problem_id"
                :to="`/problems/${d.problem_id}`"
                class="problem-link"
                @click.stop
              >#{{ d.problem_id }}</RouterLink>
              <span v-else class="na">-</span>
            </td>
            <td class="author-cell">{{ d.username }}</td>
            <td class="reply-cell">{{ d.reply_count }}</td>
            <td class="time-cell">{{ timeAgo(d.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="loading">加载中...</div>

    <div class="pagination" v-if="totalPages() > 1">
      <button :disabled="page <= 1" @click="goPage(page - 1)">‹ 上一页</button>
      <span class="page-info">第 {{ page }} / {{ totalPages() }} 页</span>
      <button :disabled="page >= totalPages()" @click="goPage(page + 1)">下一页 ›</button>
    </div>
  </div>
</template>

<style scoped>
.discussion-list { padding: 0.5rem 0; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #e0e0f0; }
.btn-new {
  padding: 0.45rem 1.1rem; background: #7c6af7; color: #fff;
  border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;
  text-decoration: none;
}
.btn-new:hover { background: #6c5ae7; }

.table-wrap { background: #16162a; border-radius: 8px; border: 1px solid #2d2d4e; overflow: hidden; }
.empty { text-align: center; padding: 3rem; color: #666; }
.loading { text-align: center; padding: 3rem; color: #888; }

.disc-table { width: 100%; border-collapse: collapse; }
.disc-table th {
  padding: 0.7rem 1rem; text-align: left;
  font-size: 0.8rem; color: #888; background: #1a1a30;
  border-bottom: 1px solid #2d2d4e;
}
.disc-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #1e1e38; }
.disc-row { cursor: pointer; }
.disc-row:last-child td { border-bottom: none; }
.disc-row:hover td { background: #1c1c35; }

.title-cell { color: #e0e0f0; font-size: 0.95rem; }
.problem-link { color: #a78bfa; font-size: 0.85rem; }
.problem-link:hover { text-decoration: underline; }
.na { color: #555; }
.author-cell { color: #a0c4ff; font-size: 0.85rem; }
.reply-cell { color: #888; text-align: center; }
.time-cell { color: #666; font-size: 0.82rem; white-space: nowrap; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.5rem; }
.pagination button {
  padding: 0.4rem 1rem; background: #1e1e38; border: 1px solid #3d3d5c;
  color: #c0c0d8; border-radius: 6px; cursor: pointer;
}
.pagination button:hover:not(:disabled) { border-color: #7c6af7; color: #fff; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { color: #888; font-size: 0.85rem; }
</style>
