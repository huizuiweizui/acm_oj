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
  if (rank === 1) return { color: '#f59e0b', fontWeight: '700' }
  if (rank === 2) return { color: '#94a3b8', fontWeight: '700' }
  if (rank === 3) return { color: '#b45309', fontWeight: '700' }
  return { color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }
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
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.2rem; color: var(--text-primary); }

.tabs {
  display: flex; gap: 0.3rem;
  border-bottom: 1px solid var(--border); margin-bottom: 1.5rem;
}
.tab-btn {
  padding: 0.55rem 1.2rem; background: transparent;
  border: none; border-bottom: 2px solid transparent;
  color: var(--text-muted); font-size: 0.9rem; cursor: pointer; margin-bottom: -1px;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--accent-text); border-bottom-color: var(--accent); font-weight: 600; }

.table-wrap { background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }
.empty { text-align: center; padding: 3rem; color: var(--text-muted); }
.loading { text-align: center; padding: 3rem; color: var(--text-muted); }

.rank-table { width: 100%; border-collapse: collapse; }
.rank-table th {
  padding: 8px 16px; text-align: left;
  font-size: 12.5px; color: var(--text-secondary); font-weight: 500;
  background: var(--bg-page); border-bottom: 1px solid var(--border);
  position: sticky; top: 0;
}
.rank-table td { padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 14px; line-height: 1.4; }
.rank-row { cursor: pointer; }
.rank-row:last-child td { border-bottom: none; }
.rank-row:hover td { background: var(--bg-hover); }

.rank-cell { font-size: 14px; }
.rank-num { font-size: 16px; }

.user-cell { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.username { color: var(--text-primary); font-weight: 500; }

.rating-cell { color: var(--accent-text); font-weight: 600; font-family: var(--font-mono); }
.ac-cell { color: var(--status-ac-text); font-weight: 600; font-family: var(--font-mono); }
.submit-cell { color: var(--text-muted); font-family: var(--font-mono); }
</style>
