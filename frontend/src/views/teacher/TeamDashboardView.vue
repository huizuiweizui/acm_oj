<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { getTeamDashboard, exportDashboard } from '@/api/team'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)

const loading = ref(true)
const data = ref(null)
const sortKey = ref('total_ac')
const exporting = ref(false)

onMounted(async () => {
  try {
    const { data: d } = await getTeamDashboard(teamId)
    data.value = d
  } finally {
    loading.value = false
  }
})

const sortedRanking = computed(() => {
  if (!data.value) return []
  return [...data.value.ranking].sort((a, b) => b[sortKey.value] - a[sortKey.value])
})

const diffOrder = computed(() => data.value?.diff_order ?? [])
const stats = computed(() => data.value?.stats ?? {})
const team = computed(() => data.value?.team ?? {})

const chartOption = computed(() => {
  const trend = data.value?.trend ?? []
  return {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 20, bottom: 40, left: 40 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e5e7eb',
      textStyle: { color: '#52525b', fontSize: 12 }, borderRadius: 8,
      formatter: (params) => `${params[0].axisValue}<br/>AC 数：<b>${params[0].value}</b>`,
    },
    xAxis: {
      type: 'category',
      data: trend.map(t => t.date.slice(5)),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#a1a1aa', fontSize: 11, interval: 4 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#e5e7eb', type: 'dashed' } },
      axisLabel: { color: '#a1a1aa', fontSize: 11 },
    },
    series: [{
      type: 'line',
      data: trend.map(t => t.count),
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: { color: '#6366f1', width: 2 },
      itemStyle: { color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#6366f140' },
            { offset: 1, color: '#6366f100' },
          ],
        },
      },
    }],
  }
})

async function doExport() {
  exporting.value = true
  try {
    const { data: blob } = await exportDashboard(teamId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${team.value.name}_ranking.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="dashboard" v-if="!loading && data">

    <!-- 顶部 -->
    <div class="dash-header">
      <button class="btn-back" @click="router.back()">← 返回</button>
      <div class="header-info">
        <h1 class="dash-title">{{ team.name }}</h1>
        <p class="dash-sub">团队总览</p>
      </div>
      <button class="btn-export" :disabled="exporting" @click="doExport">
        {{ exporting ? '导出中…' : '↓ 导出 Excel' }}
      </button>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="sc-value">{{ stats.member_count }}</div>
        <div class="sc-label">团队人数</div>
      </div>
      <div class="stat-card">
        <div class="sc-value accent">{{ stats.total_ac }}</div>
        <div class="sc-label">总 AC 题数</div>
      </div>
      <div class="stat-card">
        <div class="sc-value green">{{ stats.week_ac }}</div>
        <div class="sc-label">本周 AC</div>
      </div>
      <div class="stat-card">
        <div class="sc-value">{{ stats.avg_ac }}</div>
        <div class="sc-label">人均 AC</div>
      </div>
      <div class="stat-card" :class="{ 'card-warn': stats.pending_count > 0 }">
        <div class="sc-value" :class="stats.pending_count > 0 ? 'warn' : ''">{{ stats.pending_count }}</div>
        <div class="sc-label">待审核申请</div>
      </div>
    </div>

    <!-- 排行榜 -->
    <div class="section-card">
      <div class="section-head">
        <h2 class="section-title">成员排行</h2>
        <div class="sort-tabs">
          <button :class="['sort-tab', sortKey === 'total_ac' && 'sort-active']" @click="sortKey = 'total_ac'">总排名</button>
          <button :class="['sort-tab', sortKey === 'week_ac' && 'sort-active']" @click="sortKey = 'week_ac'">本周</button>
          <button :class="['sort-tab', sortKey === 'month_ac' && 'sort-active']" @click="sortKey = 'month_ac'">本月</button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="rank-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th>姓名</th>
              <th>学号</th>
              <th class="col-num sortable" :class="{ active: sortKey === 'total_ac' }" @click="sortKey = 'total_ac'">
                总AC <span class="sort-arrow">▾</span>
              </th>
              <th class="col-num sortable" :class="{ active: sortKey === 'week_ac' }" @click="sortKey = 'week_ac'">
                本周 <span class="sort-arrow">▾</span>
              </th>
              <th class="col-num sortable" :class="{ active: sortKey === 'month_ac' }" @click="sortKey = 'month_ac'">
                本月 <span class="sort-arrow">▾</span>
              </th>
              <th v-for="d in diffOrder" :key="d" class="col-num col-diff-head">{{ d }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, idx) in sortedRanking" :key="r.user_id">
              <td class="col-rank">
                <span :class="['rank-badge', idx < 3 ? `rank-${idx + 1}` : '']">{{ idx + 1 }}</span>
              </td>
              <td>
                <span
                  class="member-name member-link"
                  @click="router.push(`/teacher/teams/${teamId}/students/${r.user_id}`)"
                >{{ r.display_name }}</span>
                <span v-if="r.role === 'captain'" class="crown">👑</span>
              </td>
              <td class="text-muted">{{ r.student_id || '—' }}</td>
              <td class="col-num" :class="{ 'col-active-val': sortKey === 'total_ac' }">{{ r.total_ac }}</td>
              <td class="col-num" :class="{ 'col-active-val': sortKey === 'week_ac' }">{{ r.week_ac }}</td>
              <td class="col-num" :class="{ 'col-active-val': sortKey === 'month_ac' }">{{ r.month_ac }}</td>
              <td v-for="d in diffOrder" :key="d" class="col-num col-diff-val">
                {{ r.by_group[d] || 0 }}
              </td>
            </tr>
            <tr v-if="sortedRanking.length === 0">
              <td :colspan="6 + diffOrder.length" class="empty-td">暂无成员数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 30 天趋势 -->
    <div class="section-card">
      <div class="section-head">
        <h2 class="section-title">近 30 天 AC 趋势</h2>
        <span class="trend-hint">每日全团去重 AC 数</span>
      </div>
      <v-chart class="trend-chart" :option="chartOption" autoresize />
    </div>

  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>
</template>

<style scoped>
.dashboard { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }

.dash-header { display: flex; align-items: center; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; transition: border-color 0.15s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.header-info { flex: 1; }
.dash-title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.15rem; }
.dash-sub { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
.btn-export {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; transition: border-color 0.15s;
}
.btn-export:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn-export:disabled { opacity: 0.4; cursor: default; }

.stat-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; }
@media (max-width: 760px) { .stat-cards { grid-template-columns: repeat(3, 1fr); } }
.stat-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.2rem 1rem; text-align: center;
}
.card-warn { border-color: #f59e0b55; }
.sc-value { font-size: 1.9rem; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.sc-value.accent { color: var(--accent); }
.sc-value.green { color: #10b981; }
.sc-value.warn { color: #f59e0b; }
.sc-label { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.3rem; }

.section-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.25rem;
}
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; gap: 1rem; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.trend-hint { font-size: 0.78rem; color: var(--text-muted); }

.sort-tabs { display: flex; gap: 0.25rem; }
.sort-tab {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.22rem 0.7rem; border-radius: 20px; cursor: pointer; font-size: 0.82rem;
  transition: all 0.15s;
}
.sort-tab:hover { border-color: var(--accent); color: var(--accent); }
.sort-active { background: var(--accent); color: #fff; border-color: var(--accent); }

.table-wrap { overflow-x: auto; }
.rank-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.rank-table th {
  padding: 0.55rem 0.75rem; text-align: left;
  color: var(--text-muted); font-weight: 500;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
.rank-table td { padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.rank-table tr:last-child td { border-bottom: none; }

.col-rank { width: 3rem; text-align: center; }
.col-num { text-align: right; }
.col-diff-head { color: var(--text-muted); font-size: 0.78rem; }
.col-diff-val { color: var(--text-secondary); font-size: 0.83rem; }
.col-active-val { color: var(--accent); font-weight: 600; }
.sortable { cursor: pointer; user-select: none; }
.sortable.active { color: var(--accent); }
.sortable:hover { color: var(--text-primary); }
.sort-arrow { opacity: 0.5; font-size: 0.75rem; }
.sortable.active .sort-arrow { opacity: 1; }

.rank-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.65rem; height: 1.65rem; border-radius: 50%; font-size: 0.78rem;
  background: var(--bg-secondary); color: var(--text-muted);
}
.rank-1 { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b55; }
.rank-2 { background: rgba(148,163,184,0.12); color: #94a3b8; border: 1px solid rgba(148,163,184,0.3); }
.rank-3 { background: #cd7c2222; color: #cd7c22; border: 1px solid #cd7c2255; }

.member-name { color: var(--text-primary); font-weight: 500; }
.member-link { cursor: pointer; }
.member-link:hover { color: var(--accent); text-decoration: underline; }
.crown { margin-left: 0.2rem; font-size: 0.82rem; }
.text-muted { color: var(--text-muted); }
.empty-td { text-align: center; padding: 2rem; color: var(--text-muted); }

.trend-chart { width: 100%; height: 240px; }
.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }
</style>
