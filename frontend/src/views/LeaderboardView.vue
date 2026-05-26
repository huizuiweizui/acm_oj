<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getRank } from '@/api/users'

const router = useRouter()
const tab = ref('ac')
const rankedUsers = ref([])
const loading = ref(false)

const tabs = [
  { key: 'ac', label: 'AC 数排行' },
  { key: 'rating', label: 'Rating 排行' },
]

async function fetchRank() {
  loading.value = true
  try {
    const { data } = await getRank({ tab: tab.value })
    rankedUsers.value = data.ranked_users
  } finally {
    loading.value = false
  }
}

function switchTab(key) {
  tab.value = key
  fetchRank()
}

const rankStyle = (rank) => {
  if (rank === 1) return { color: '#ffd700', fontWeight: '700' }
  if (rank === 2) return { color: '#c0c0c0', fontWeight: '700' }
  if (rank === 3) return { color: '#cd7f32', fontWeight: '700' }
  return { color: '#888' }
}

onMounted(fetchRank)
</script>

<template>
  <div class="leaderboard">
    <div class="page-title">排行榜</div>

    <div class="tabs">
      <button
        v-for="t in tabs" :key="t.key"
        class="tab-btn" :class="{ active: tab === t.key }"
        @click="switchTab(t.key)"
      >{{ t.label }}</button>
    </div>

    <div class="table-wrap" v-if="!loading">
      <div v-if="rankedUsers.length === 0" class="empty">暂无数据</div>
      <table v-else class="rank-table">
        <thead>
          <tr>
            <th width="72">排名</th>
            <th>用户</th>
            <th width="100">Rating</th>
            <th width="100">AC 题数</th>
            <th width="100">提交总数</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="u in rankedUsers" :key="u.user_id"
            class="rank-row"
            @click="router.push(`/users/${u.user_id}`)"
          >
            <td class="rank-cell">
              <span class="rank-num" :style="rankStyle(u.rank)">
                {{ u.rank <= 3 ? ['🥇','🥈','🥉'][u.rank-1] : u.rank }}
              </span>
            </td>
            <td class="user-cell">
              <div class="avatar" :style="{ background: u.avatar_color }">
                {{ u.username[0].toUpperCase() }}
              </div>
              <span class="username">{{ u.username }}</span>
            </td>
            <td class="rating-cell">{{ u.rating }}</td>
            <td class="ac-cell">{{ u.ac_count }}</td>
            <td class="submit-cell">{{ u.submit_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="loading">加载中...</div>
  </div>
</template>

<style scoped>
.leaderboard { padding: 0.5rem 0; }
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.2rem; color: #e0e0f0; }

.tabs {
  display: flex; gap: 0.3rem;
  border-bottom: 1px solid #2d2d4e; margin-bottom: 1.5rem;
}
.tab-btn {
  padding: 0.55rem 1.2rem; background: transparent;
  border: none; border-bottom: 2px solid transparent;
  color: #888; font-size: 0.9rem; cursor: pointer; margin-bottom: -1px;
}
.tab-btn:hover { color: #e0e0f0; }
.tab-btn.active { color: #a78bfa; border-bottom-color: #a78bfa; font-weight: 600; }

.table-wrap { background: #16162a; border-radius: 8px; border: 1px solid #2d2d4e; overflow: hidden; }
.empty { text-align: center; padding: 3rem; color: #666; }
.loading { text-align: center; padding: 3rem; color: #888; }

.rank-table { width: 100%; border-collapse: collapse; }
.rank-table th {
  padding: 0.75rem 1rem; text-align: left;
  font-size: 0.8rem; color: #888; background: #1a1a30;
  border-bottom: 1px solid #2d2d4e;
}
.rank-table td { padding: 0.8rem 1rem; border-bottom: 1px solid #1e1e38; }
.rank-row { cursor: pointer; }
.rank-row:last-child td { border-bottom: none; }
.rank-row:hover td { background: #1c1c35; }

.rank-cell { font-size: 0.95rem; }
.rank-num { font-size: 1rem; }

.user-cell { display: flex; align-items: center; gap: 0.75rem; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; font-weight: 700; color: #fff; flex-shrink: 0;
}
.username { color: #a0c4ff; font-weight: 500; }

.rating-cell { color: #a78bfa; font-weight: 600; }
.ac-cell { color: #2ecc71; font-weight: 600; }
.submit-cell { color: #888; }
</style>
