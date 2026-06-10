<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { PieChart, LineChart, HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent, CalendarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { getStudentDetail } from '@/api/team'

use([PieChart, LineChart, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent, CalendarComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.teamId)
const userId = Number(route.params.userId)

const loading = ref(true)
const data = ref(null)

onMounted(async () => {
  try {
    const { data: d } = await getStudentDetail(teamId, userId)
    data.value = d
  } finally {
    loading.value = false
  }
})

const member = computed(() => data.value?.member ?? {})
const diffDist = computed(() => data.value?.diff_dist ?? [])
const trend = computed(() => data.value?.trend ?? [])
const heatmap = computed(() => data.value?.heatmap ?? {})
const acProblems = computed(() => data.value?.ac_problems ?? [])

// ── 难度分布饼图 ──────────────────────────────────────────────────
const DIFF_COLORS = {
  '入门': '#10b981',
  '普及': '#3b82f6',
  '提高': '#8b5cf6',
  'NOI': '#f59e0b',
  '其他': '#6b7280',
}

const pieOption = computed(() => {
  const series_data = diffDist.value
    .filter(d => d.count > 0)
    .map(d => ({ value: d.count, name: d.group, itemStyle: { color: DIFF_COLORS[d.group] } }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1e2030',
      borderColor: '#3a3f5c',
      textStyle: { color: '#c8cce8' },
      formatter: '{b}: {c} 题 ({d}%)',
    },
    series: [{
      type: 'pie',
      radius: ['45%', '75%'],
      center: ['50%', '52%'],
      data: series_data.length ? series_data : [{ value: 1, name: '暂无数据', itemStyle: { color: '#2a2d3e' } }],
      label: { show: true, color: '#9ca3af', fontSize: 12, formatter: '{b}\n{c}' },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  }
})

// ── 近 30 天折线图 ─────────────────────────────────────────────────
const lineOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 20, right: 20, bottom: 40, left: 40 },
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#1e2030',
    borderColor: '#3a3f5c',
    textStyle: { color: '#c8cce8' },
    formatter: (params) => `${params[0].axisValue}<br/>AC 数：<b>${params[0].value}</b>`,
  },
  xAxis: {
    type: 'category',
    data: trend.value.map(t => t.date.slice(5)),
    axisLine: { lineStyle: { color: '#3a3f5c' } },
    axisLabel: { color: '#6b7280', fontSize: 11, interval: 4 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#2a2d3e', type: 'dashed' } },
    axisLabel: { color: '#6b7280', fontSize: 11 },
  },
  series: [{
    type: 'line',
    data: trend.value.map(t => t.count),
    smooth: true,
    symbol: 'circle',
    symbolSize: 5,
    lineStyle: { color: '#6366f1', width: 2 },
    itemStyle: { color: '#6366f1' },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: '#6366f140' }, { offset: 1, color: '#6366f100' }],
      },
    },
  }],
}))

// ── 热力图（Calendar）──────────────────────────────────────────────
const heatmapData = computed(() =>
  Object.entries(heatmap.value).map(([date, count]) => [date, count])
)

const heatmapYear = computed(() => {
  const now = new Date()
  return `${now.getFullYear() - 1}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
    + '/' + now.toISOString().slice(0, 10)
})

const calOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: '#1e2030',
    borderColor: '#3a3f5c',
    textStyle: { color: '#c8cce8' },
    formatter: (p) => `${p.data[0]}<br/>AC 数：<b>${p.data[1]}</b>`,
  },
  visualMap: {
    min: 0, max: 8, show: false,
    inRange: { color: ['#1e2030', '#3730a3', '#6366f1', '#a5b4fc'] },
  },
  calendar: {
    range: heatmapYear.value,
    left: 50, right: 20, top: 20,
    cellSize: ['auto', 14],
    dayLabel: { nameMap: 'ZH', color: '#6b7280', fontSize: 11 },
    monthLabel: { color: '#6b7280', fontSize: 11 },
    yearLabel: { show: false },
    splitLine: { show: false },
    itemStyle: { borderColor: '#12141f', color: '#1e2030' },
  },
  series: [{
    type: 'heatmap',
    coordinateSystem: 'calendar',
    data: heatmapData.value,
  }],
}))

// ── 难度样式 ─────────────────────────────────────────────────────
const DIFF_LABEL_MAP = {
  '暂无评定': { cls: 'diff-none', label: '暂无' },
  '入门': { cls: 'diff-easy', label: '入门' },
  '普及-': { cls: 'diff-normal', label: '普及-' },
  '普及/提高-': { cls: 'diff-normal', label: '普及/提高' },
  '普及+/提高': { cls: 'diff-normal', label: '普及+/提高' },
  '提高+/省选-': { cls: 'diff-hard', label: '提高+' },
  '省选/NOI-': { cls: 'diff-hard', label: '省选-' },
  'NOI/NOI+/CTSC': { cls: 'diff-noi', label: 'NOI' },
}
function diffInfo(d) { return DIFF_LABEL_MAP[d] ?? { cls: 'diff-none', label: d } }
function fmt(dt) { return dt ? dt.slice(0, 10) : '' }
</script>

<template>
  <div class="student-detail" v-if="!loading && data">

    <!-- 顶部 -->
    <div class="sd-header">
      <button class="btn-back" @click="router.back()">← 返回</button>
      <div class="header-info">
        <h1 class="sd-name">{{ member.display_name }}</h1>
        <p class="sd-meta">
          {{ member.username }}
          <span v-if="member.student_id"> · {{ member.student_id }}</span>
          <span v-if="member.major"> · {{ member.major }}</span>
          <span v-if="member.grade"> · {{ member.grade }}</span>
        </p>
      </div>
      <div class="sd-summary">
        <div class="summ-item">
          <span class="summ-val accent">{{ member.total_ac }}</span>
          <span class="summ-label">AC 题数</span>
        </div>
        <div class="summ-item">
          <span class="summ-val">{{ member.total_submit }}</span>
          <span class="summ-label">总提交</span>
        </div>
      </div>
    </div>

    <!-- 图表行 -->
    <div class="chart-row">
      <!-- 难度分布 -->
      <div class="section-card chart-card-pie">
        <h3 class="sc-title">难度分布</h3>
        <v-chart class="pie-chart" :option="pieOption" autoresize />
        <div class="diff-legend">
          <div v-for="d in diffDist.filter(x => x.count > 0)" :key="d.group" class="legend-row">
            <span class="legend-dot" :style="{ background: DIFF_COLORS[d.group] }"></span>
            <span class="legend-name">{{ d.group }}</span>
            <span class="legend-count">{{ d.count }}</span>
          </div>
        </div>
      </div>

      <!-- 近 30 天趋势 -->
      <div class="section-card chart-card-line">
        <h3 class="sc-title">近 30 天 AC 趋势</h3>
        <v-chart class="line-chart" :option="lineOption" autoresize />
      </div>
    </div>

    <!-- 热力图 -->
    <div class="section-card">
      <h3 class="sc-title">过去一年提交热力图</h3>
      <v-chart class="cal-chart" :option="calOption" autoresize />
    </div>

    <!-- AC 题目列表 -->
    <div class="section-card">
      <h3 class="sc-title">已 AC 题目（最近 50 题）</h3>
      <div class="table-wrap">
        <table class="prob-table">
          <thead>
            <tr>
              <th>题号</th><th>题目标题</th><th>难度</th><th>首次 AC</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in acProblems" :key="p.problem_id">
              <td class="text-muted">#{{ p.problem_id }}</td>
              <td>{{ p.title }}</td>
              <td>
                <span :class="['diff-tag', diffInfo(p.difficulty).cls]">
                  {{ diffInfo(p.difficulty).label }}
                </span>
              </td>
              <td class="text-muted">{{ fmt(p.first_ac_at) }}</td>
            </tr>
            <tr v-if="acProblems.length === 0">
              <td colspan="4" class="empty-td">暂无 AC 记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>
</template>

<style scoped>
.student-detail { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }

.sd-header { display: flex; align-items: flex-start; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; transition: border-color 0.15s; margin-top: 0.25rem;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.header-info { flex: 1; }
.sd-name { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.2rem; }
.sd-meta { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
.sd-summary { display: flex; gap: 1.5rem; flex-shrink: 0; }
.summ-item { display: flex; flex-direction: column; align-items: flex-end; }
.summ-val { font-size: 1.8rem; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.summ-val.accent { color: var(--accent); }
.summ-label { font-size: 0.75rem; color: var(--text-muted); }

.chart-row { display: grid; grid-template-columns: 260px 1fr; gap: 1.5rem; }
@media (max-width: 760px) { .chart-row { grid-template-columns: 1fr; } }
.section-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.25rem;
}
.sc-title { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin: 0 0 1rem; }

.pie-chart { width: 100%; height: 200px; }
.diff-legend { display: flex; flex-direction: column; gap: 0.35rem; margin-top: 0.75rem; }
.legend-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-name { flex: 1; color: var(--text-secondary); }
.legend-count { color: var(--text-primary); font-weight: 600; }

.line-chart { width: 100%; height: 220px; }

.cal-chart { width: 100%; height: 160px; }

.table-wrap { overflow-x: auto; }
.prob-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.prob-table th {
  padding: 0.5rem 0.75rem; text-align: left; color: var(--text-muted);
  font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap;
}
.prob-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.prob-table tr:last-child td { border-bottom: none; }
.text-muted { color: var(--text-muted); }
.empty-td { text-align: center; padding: 2rem; color: var(--text-muted); }

.diff-tag {
  display: inline-block; padding: 0.1rem 0.5rem; border-radius: 4px;
  font-size: 0.75rem; font-weight: 500;
}
.diff-easy { background: #10b98122; color: #10b981; }
.diff-normal { background: #3b82f622; color: #3b82f6; }
.diff-hard { background: #8b5cf622; color: #8b5cf6; }
.diff-noi { background: #f59e0b22; color: #f59e0b; }
.diff-none { background: rgba(107,114,128,0.15); color: var(--text-muted); }

.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }
</style>
