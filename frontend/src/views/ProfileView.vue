<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUser, getUserStats } from '@/api/users'
import { useUserStore } from '@/stores/user'
import StatusBadge from '@/components/StatusBadge.vue'
import AcCalendarChart from '@/components/AcCalendarChart.vue'
import LanguageDistChart from '@/components/LanguageDistChart.vue'
import DifficultyDistChart from '@/components/DifficultyDistChart.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const profile = ref(null)
const recentSubs = ref([])
const stats = ref(null)
const loading = ref(true)

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

const totalSubs = (dist) => Object.values(dist || {}).reduce((a, b) => a + b, 0)

onMounted(async () => {
  const id = route.params.id
  loading.value = true
  try {
    const [profileRes, statsRes] = await Promise.all([
      getUser(id),
      getUserStats(id),
    ])
    profile.value = profileRes.data.user
    recentSubs.value = profileRes.data.recent_submissions
    stats.value = statsRes.data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>

  <div v-else-if="profile" class="profile-page">

    <!-- 用户信息卡 -->
    <div class="user-card">
      <div class="avatar-big" :style="{ background: profile.avatar_color }">
        {{ profile.username[0].toUpperCase() }}
      </div>
      <div class="user-info">
        <div class="username">{{ profile.username }}</div>
        <div class="bio" v-if="profile.bio">{{ profile.bio }}</div>
        <div class="stats-row">
          <div class="stat-item">
            <div class="stat-val">{{ profile.rating }}</div>
            <div class="stat-label">Rating</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-val">{{ profile.ac_count }}</div>
            <div class="stat-label">AC 题目</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-val">{{ profile.submit_count }}</div>
            <div class="stat-label">总提交</div>
          </div>
          <div class="stat-divider" v-if="profile.submit_count"></div>
          <div class="stat-item" v-if="profile.submit_count">
            <div class="stat-val">
              {{ ((profile.ac_count / Math.max(profile.submit_count,1)) * 100).toFixed(1) }}%
            </div>
            <div class="stat-label">AC 率</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-grid">

      <!-- 左列 -->
      <div class="col-left">

        <!-- AC 日历热力图 -->
        <div class="chart-card">
          <div class="card-title">AC 记录（近一年）</div>
          <AcCalendarChart :ac-by-date="stats?.ac_by_date ?? {}" />
          <div class="chart-note">
            近一年共 AC
            <strong>{{ Object.values(stats?.ac_by_date ?? {}).reduce((a,b)=>a+b,0) }}</strong> 次
          </div>
        </div>

        <!-- 近期提交 -->
        <div class="chart-card">
          <div class="card-title">近期提交</div>
          <div v-if="recentSubs.length === 0" class="empty">暂无提交记录</div>
          <table v-else class="sub-table">
            <thead>
              <tr>
                <th>题目</th>
                <th width="80">语言</th>
                <th width="80">结果</th>
                <th width="90">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="s in recentSubs" :key="s.id"
                class="sub-row"
                @click="router.push(`/problems/${s.problem_id}`)"
              >
                <td class="problem-cell">
                  <span class="problem-title">{{ s.problem_title }}</span>
                </td>
                <td class="lang-cell">{{ s.language }}</td>
                <td><StatusBadge :status="s.status" /></td>
                <td class="time-cell">{{ timeAgo(s.submitted_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 右列：图表 -->
      <div class="col-right">

        <!-- 语言分布 -->
        <div class="chart-card" v-if="totalSubs(stats?.language_dist) > 0">
          <div class="card-title">语言分布</div>
          <LanguageDistChart :language-dist="stats?.language_dist ?? {}" />
        </div>

        <!-- 难度分布 -->
        <div class="chart-card" v-if="Object.keys(stats?.ac_by_difficulty ?? {}).length > 0">
          <div class="card-title">AC 题目难度分布</div>
          <DifficultyDistChart :ac-by-difficulty="stats?.ac_by_difficulty ?? {}" />
        </div>

        <div
          v-if="totalSubs(stats?.language_dist) === 0 && Object.keys(stats?.ac_by_difficulty ?? {}).length === 0"
          class="empty-charts"
        >提交后这里会显示数据统计图表</div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.loading { text-align: center; padding: 4rem; color: #888; }
.profile-page { padding: 0.5rem 0; }

/* 用户卡 */
.user-card {
  display: flex; align-items: center; gap: 1.8rem;
  background: #16162a; border: 1px solid #2d2d4e;
  border-radius: 12px; padding: 1.8rem 2rem; margin-bottom: 1.5rem;
}
.avatar-big {
  width: 80px; height: 80px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem; font-weight: 700; color: #fff;
}
.user-info { flex: 1; }
.username { font-size: 1.4rem; font-weight: 700; color: #e0e0f0; margin-bottom: 0.3rem; }
.bio { color: #888; font-size: 0.9rem; margin-bottom: 0.8rem; }
.stats-row { display: flex; align-items: center; gap: 0; }
.stat-item { text-align: center; padding: 0 1.2rem; }
.stat-item:first-child { padding-left: 0; }
.stat-val { font-size: 1.3rem; font-weight: 700; color: #a78bfa; }
.stat-label { font-size: 0.75rem; color: #666; margin-top: 0.1rem; }
.stat-divider { width: 1px; height: 32px; background: #2d2d4e; }

/* 内容网格 */
.content-grid { display: grid; grid-template-columns: 1fr 340px; gap: 1.2rem; align-items: start; }
.col-left, .col-right { display: flex; flex-direction: column; gap: 1.2rem; }

.chart-card {
  background: #16162a; border: 1px solid #2d2d4e;
  border-radius: 10px; padding: 1.2rem 1.4rem;
}
.card-title { font-size: 0.9rem; font-weight: 700; color: #a78bfa; margin-bottom: 0.9rem; }
.chart-note { font-size: 0.8rem; color: #666; margin-top: 0.5rem; }

/* 近期提交表格 */
.sub-table { width: 100%; border-collapse: collapse; }
.sub-table th {
  padding: 0.5rem 0.6rem; font-size: 0.78rem;
  color: #666; text-align: left; border-bottom: 1px solid #2d2d4e;
}
.sub-table td { padding: 0.55rem 0.6rem; border-bottom: 1px solid #1e1e38; }
.sub-row { cursor: pointer; }
.sub-row:last-child td { border-bottom: none; }
.sub-row:hover td { background: #1c1c35; }
.problem-title { color: #a0c4ff; font-size: 0.88rem; }
.lang-cell { color: #888; font-size: 0.82rem; }
.time-cell { color: #666; font-size: 0.78rem; white-space: nowrap; }

.empty { color: #666; font-size: 0.9rem; padding: 1rem 0; text-align: center; }
.empty-charts {
  background: #16162a; border: 1px solid #2d2d4e; border-radius: 10px;
  padding: 2rem; text-align: center; color: #555; font-size: 0.88rem;
}

@media (max-width: 900px) {
  .content-grid { grid-template-columns: 1fr; }
  .user-card { flex-direction: column; align-items: flex-start; gap: 1rem; }
}
</style>
