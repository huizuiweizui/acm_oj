<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { BarChart, LineChart, HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent, CalendarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { getStudentDetail } from '@/api/team'
import DifficultyBadge from '@/components/DifficultyBadge.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { DIFF_COLORS, DIFF_SHORT } from '@/utils/difficulty'

use([BarChart, LineChart, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent, CalendarComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.teamId)
const userId = Number(route.params.userId)

const loading = ref(true)
const data = ref(null)
const apiError = ref('')

onMounted(async () => {
  try {
    const { data: d } = await getStudentDetail(teamId, userId)
    data.value = d
    // 默认展开未 AC 比例最高的知识点
    if (d.knowledge?.length && d.knowledge[0].unsolved_ratio > 0) expanded.value = new Set([d.knowledge[0].tag])
  } catch (e) {
    const s = e.response?.status
    apiError.value = s === 403 ? '无权限查看该学生（仅团队创建者、队长和管理员可访问）'
      : s === 404 ? (e.response?.data?.detail || '学生不存在')
      : '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
})

const member = computed(() => data.value?.member ?? {})
const diffDist = computed(() => data.value?.diff_dist ?? [])
const trend = computed(() => data.value?.trend ?? [])
const heatmap = computed(() => data.value?.heatmap ?? {})
const acProblems = computed(() => data.value?.ac_problems ?? [])
const knowledge = computed(() => data.value?.knowledge ?? [])

const tooltipStyle = {
  backgroundColor: '#fff',
  borderColor: '#e5e7eb',
  textStyle: { color: '#52525b', fontSize: 12 }, borderRadius: 8,
}

// ── 难度分布柱状图 ────────────────────────────────────────────────
const barOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 16, right: 12, bottom: 28, left: 32 },
  tooltip: { trigger: 'axis', ...tooltipStyle, formatter: (p) => `${p[0].name}<br/>AC：<b>${p[0].value}</b> 题` },
  xAxis: {
    type: 'category',
    data: diffDist.value.map(d => d.level),
    axisLabel: { color: '#a1a1aa', fontSize: 10, interval: 0, formatter: (v) => DIFF_SHORT[v] ?? v },
    axisLine: { lineStyle: { color: '#e5e7eb' } },
  },
  yAxis: {
    type: 'value', minInterval: 1,
    splitLine: { lineStyle: { color: '#e5e7eb', type: 'dashed' } },
    axisLabel: { color: '#a1a1aa', fontSize: 11 },
  },
  series: [{
    type: 'bar',
    barMaxWidth: 22,
    data: diffDist.value.map(d => ({ value: d.count, itemStyle: { color: DIFF_COLORS[d.level], borderRadius: [3, 3, 0, 0] } })),
  }],
}))

// ── 近 30 天折线图 ─────────────────────────────────────────────────
const lineOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 20, right: 20, bottom: 30, left: 40 },
  tooltip: { trigger: 'axis', ...tooltipStyle },
  xAxis: {
    type: 'category',
    data: trend.value.map(t => t.date.slice(5)),
    axisLine: { lineStyle: { color: '#e5e7eb' } },
    axisLabel: { color: '#a1a1aa', fontSize: 11, interval: 4 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#e5e7eb', type: 'dashed' } },
    axisLabel: { color: '#a1a1aa', fontSize: 11 },
  },
  series: [
    {
      name: '提交数', type: 'line', data: trend.value.map(t => t.submit), smooth: true,
      symbol: 'circle', symbolSize: 4,
      lineStyle: { color: '#94a3b8', width: 1.5 }, itemStyle: { color: '#94a3b8' },
    },
    {
      name: 'AC 数', type: 'line', data: trend.value.map(t => t.count), smooth: true,
      symbol: 'circle', symbolSize: 5,
      lineStyle: { color: '#6366f1', width: 2 }, itemStyle: { color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: '#6366f140' }, { offset: 1, color: '#6366f100' }],
        },
      },
    },
  ],
}))

// ── 提交热力图（近一年，GitHub 贡献图样式）──────────────────────
const calRange = computed(() => {
  const end = new Date()
  const start = new Date(end.getTime() - 364 * 86400000)
  const f = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return [f(start), f(end)]
})

const calOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item', ...tooltipStyle,
    formatter: (p) => `${p.data[0]}<br/>提交：<b>${p.data[1]}</b> 次`,
  },
  visualMap: {
    min: 0, max: 10, show: false,
    inRange: { color: ['#e0f2e9', '#9fe1cb', '#5dcaa5', '#1d9e75'] },
  },
  calendar: {
    range: calRange.value,
    left: 36, right: 12, top: 24, bottom: 4,
    cellSize: ['auto', 13],
    dayLabel: { nameMap: 'ZH', color: '#a1a1aa', fontSize: 10, firstDay: 1 },
    monthLabel: { nameMap: 'ZH', color: '#a1a1aa', fontSize: 10 },
    yearLabel: { show: false },
    splitLine: { show: false },
    itemStyle: { borderColor: 'transparent', borderWidth: 2, color: 'rgba(148,163,184,0.15)' },
  },
  series: [{
    type: 'heatmap',
    coordinateSystem: 'calendar',
    data: Object.entries(heatmap.value),
  }],
}))

// ── 知识点下钻 ───────────────────────────────────────────────────
const expanded = ref(new Set())
const onlyUnsolved = ref(false)

function toggleTag(tag) {
  const s = new Set(expanded.value)
  if (s.has(tag)) s.delete(tag)
  else s.add(tag)
  expanded.value = s
}

function expandAll(open) {
  expanded.value = open ? new Set(knowledge.value.map(k => k.tag)) : new Set()
}

const visibleKnowledge = computed(() =>
  onlyUnsolved.value ? knowledge.value.filter(k => k.ac_count < k.tried_count) : knowledge.value,
)

function problemsOf(k) {
  return onlyUnsolved.value ? k.problems.filter(p => !p.ac) : k.problems
}

function resultText(p) {
  if (p.ac) return p.submits_to_ac === 1 ? '一次 AC' : `${p.submits_to_ac} 次提交后 AC`
  return `最近：${p.last_status}`
}

function openSubmissions(p) {
  router.push({ path: '/submissions', query: { user_id: userId, problem_id: p.problem_id } })
}

function fmt(dt) { return dt ? dt.slice(0, 10) : '' }
</script>

<template>
  <div class="student-detail" v-if="!loading && data">

    <!-- 顶部 -->
    <div class="sd-header">
      <button class="btn-back" @click="router.back()">← 返回</button>
      <div class="header-info">
        <h1 class="sd-name">
          {{ member.display_name }}
          <span v-if="member.role === 'captain'" class="crown" title="队长">👑</span>
        </h1>
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
          <span class="summ-val">{{ member.tried_count }}</span>
          <span class="summ-label">尝试题数</span>
        </div>
        <div class="summ-item">
          <span class="summ-val">{{ member.total_submit }}</span>
          <span class="summ-label">总提交</span>
        </div>
        <div class="summ-item">
          <span class="summ-val">{{ member.ac_rate }}%</span>
          <span class="summ-label">AC 率</span>
        </div>
      </div>
    </div>

    <!-- 图表行 -->
    <div class="chart-row">
      <div class="section-card">
        <h3 class="sc-title">难度分布（去重 AC）</h3>
        <v-chart class="bar-chart" :option="barOption" autoresize />
      </div>
      <div class="section-card">
        <h3 class="sc-title">近 30 天趋势 <span class="sc-hint">灰：提交 · 紫：AC</span></h3>
        <v-chart class="line-chart" :option="lineOption" autoresize />
      </div>
    </div>

    <!-- 热力图 -->
    <div class="section-card">
      <h3 class="sc-title">近一年提交热力图</h3>
      <v-chart class="cal-chart" :option="calOption" autoresize />
    </div>

    <!-- 知识点下钻 -->
    <div class="section-card">
      <div class="kp-head">
        <div>
          <h3 class="sc-title kp-title">知识点掌握情况</h3>
          <p class="sc-hint">按「尝试未通过」比例排序，越靠前越需要关注；点击题目查看该生的提交记录</p>
        </div>
        <div class="kp-tools">
          <label class="kp-check"><input v-model="onlyUnsolved" type="checkbox" /> 只看未 AC</label>
          <button class="btn-xs" @click="expandAll(true)">全部展开</button>
          <button class="btn-xs" @click="expandAll(false)">全部收起</button>
        </div>
      </div>

      <div v-if="visibleKnowledge.length === 0" class="empty-td">
        {{ onlyUnsolved ? '没有尝试未通过的题目 🎉' : '暂无提交记录' }}
      </div>
      <div v-else class="kp-list">
        <div
          v-for="k in visibleKnowledge" :key="k.tag"
          :class="['kp-item', k.ac_count < k.tried_count && 'kp-warn']"
        >
          <button class="kp-row" @click="toggleTag(k.tag)">
            <span class="kp-caret">{{ expanded.has(k.tag) ? '▾' : '▸' }}</span>
            <span class="kp-name">{{ k.tag }}</span>
            <span class="kp-bar">
              <span class="kp-bar-fill" :style="{ width: (k.ac_count / k.tried_count * 100) + '%' }"></span>
            </span>
            <span class="kp-count">
              AC <b>{{ k.ac_count }}</b> 题 / 尝试 <b>{{ k.tried_count }}</b> 题
            </span>
            <span v-if="k.tried_count > k.ac_count" class="kp-unsolved">{{ k.tried_count - k.ac_count }} 道未通过</span>
          </button>

          <table v-if="expanded.has(k.tag)" class="prob-table kp-table">
            <tbody>
              <tr
                v-for="p in problemsOf(k)" :key="p.problem_id"
                :class="['kp-prob', !p.ac && 'kp-prob-fail']"
                @click="openSubmissions(p)"
              >
                <td class="kp-icon">{{ p.ac ? '✓' : '✗' }}</td>
                <td>
                  <RouterLink :to="`/problems/${p.problem_id}`" class="prob-link" @click.stop>
                    #{{ p.problem_id }} {{ p.title }}
                  </RouterLink>
                </td>
                <td><DifficultyBadge :difficulty="p.difficulty" /></td>
                <td class="text-muted nowrap">{{ p.submit_count }} 次提交</td>
                <td class="nowrap">
                  <span v-if="p.ac" class="res-ac">{{ resultText(p) }}</span>
                  <span v-else class="res-fail">最近：<StatusBadge :status="p.last_status" /></span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
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
              <td><RouterLink :to="`/problems/${p.problem_id}`" class="prob-link">{{ p.title }}</RouterLink></td>
              <td><DifficultyBadge :difficulty="p.difficulty" /></td>
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
  <div v-else class="loading-tip error-tip">
    {{ apiError }}
    <button class="btn-back" @click="router.back()">← 返回</button>
  </div>
</template>

<style scoped>
.student-detail { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }

.sd-header { display: flex; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; transition: border-color 0.15s; margin-top: 0.25rem;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.header-info { flex: 1; min-width: 200px; }
.sd-name { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.2rem; }
.crown { font-size: 1rem; }
.sd-meta { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
.sd-summary { display: flex; gap: 1.5rem; flex-shrink: 0; }
.summ-item { display: flex; flex-direction: column; align-items: flex-end; }
.summ-val { font-size: 1.8rem; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.summ-val.accent { color: var(--accent); }
.summ-label { font-size: 0.75rem; color: var(--text-muted); }

.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
@media (max-width: 760px) { .chart-row { grid-template-columns: 1fr; } }
.section-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.25rem;
}
.sc-title { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin: 0 0 1rem; }
.sc-hint { font-size: 0.75rem; color: var(--text-muted); font-weight: 400; margin: 0; }

.bar-chart, .line-chart { width: 100%; height: 220px; }
.cal-chart { width: 100%; height: 150px; }

/* 知识点 */
.kp-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
.kp-title { margin-bottom: 0.25rem; }
.kp-tools { display: flex; align-items: center; gap: 0.5rem; }
.kp-check { display: flex; align-items: center; gap: 0.3rem; font-size: 0.82rem; color: var(--text-secondary); cursor: pointer; }
.btn-xs {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.2rem 0.55rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem;
}
.btn-xs:hover { border-color: var(--accent); color: var(--accent); }

.kp-list { display: flex; flex-direction: column; gap: 0.5rem; }
.kp-item { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.kp-warn { border-left: 3px solid var(--status-wa-dot); }
.kp-row {
  width: 100%; display: flex; align-items: center; gap: 0.75rem;
  background: none; border: none; padding: 0.65rem 0.9rem; cursor: pointer;
  color: var(--text-primary); font-size: 0.875rem; text-align: left;
}
.kp-row:hover { background: var(--bg-hover); }
.kp-caret { color: var(--text-muted); width: 0.8rem; }
.kp-name { font-weight: 600; min-width: 6rem; }
.kp-bar { flex: 1; max-width: 220px; height: 6px; border-radius: 3px; background: var(--status-wa-bg); overflow: hidden; }
.kp-bar-fill { display: block; height: 100%; background: var(--status-ac-dot); }
.kp-count { color: var(--text-secondary); font-size: 0.82rem; white-space: nowrap; }
.kp-count b { color: var(--text-primary); }
.kp-unsolved {
  margin-left: auto; font-size: 0.75rem; font-weight: 600; white-space: nowrap;
  color: var(--status-wa-text); background: var(--status-wa-bg); padding: 0.1rem 0.5rem; border-radius: 10px;
}
.kp-table { border-top: 1px solid var(--border); }
.kp-prob { cursor: pointer; }
.kp-prob:hover td { background: var(--bg-hover); }
.kp-prob-fail td { background: rgba(239, 68, 68, 0.04); }
.kp-icon { width: 2rem; text-align: center; font-weight: 700; color: var(--status-ac-text); }
.kp-prob-fail .kp-icon { color: var(--status-wa-text); }
.res-ac { color: var(--status-ac-text); font-size: 0.82rem; }
.res-fail { display: inline-flex; align-items: center; gap: 0.3rem; color: var(--text-muted); font-size: 0.82rem; }

.table-wrap { overflow-x: auto; }
.prob-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.prob-table th {
  padding: 0.5rem 0.75rem; text-align: left; color: var(--text-muted);
  font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap;
}
.prob-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.prob-table tr:last-child td { border-bottom: none; }
.prob-link { color: var(--text-primary); text-decoration: none; }
.prob-link:hover { color: var(--accent-text); text-decoration: underline; }
.text-muted { color: var(--text-muted); }
.nowrap { white-space: nowrap; }
.empty-td { text-align: center; padding: 2rem; color: var(--text-muted); }

.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }
.error-tip { color: #f87171; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
</style>
