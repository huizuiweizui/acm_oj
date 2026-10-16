<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { getTeamDashboard, exportDashboard, saveBlobResponse } from '@/api/team'
import { DIFF_COLORS, DIFF_SHORT } from '@/utils/difficulty'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)

const loading = ref(true)
const data = ref(null)
const apiError = ref('')
const exporting = ref(false)

// 时间范围筛选（作用于提交时间）
const RANGES = [
  { key: 'all', label: '全部' },
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
  { key: 'custom', label: '自定义' },
]
const range = ref('all')
const customStart = ref('')
const customEnd = ref('')

function rangeParams() {
  const p = { range: range.value }
  if (range.value === 'custom') {
    if (customStart.value) p.start = customStart.value
    if (customEnd.value) p.end = customEnd.value
  }
  return p
}

async function loadDashboard() {
  loading.value = !data.value   // 切换筛选时保留旧数据，避免整页闪烁
  apiError.value = ''
  try {
    const { data: d } = await getTeamDashboard(teamId, rangeParams())
    data.value = d
  } catch (e) {
    data.value = null
    const status = e.response?.status
    if (status === 401) apiError.value = '登录已过期，请重新登录后再试'
    else if (status === 403) apiError.value = '无权限查看此团队总览（仅团队创建者、队长和管理员可访问）'
    else if (status === 404) apiError.value = '团队不存在'
    else if (status === 500) apiError.value = '服务器内部错误，请刷新重试；若持续出现请联系管理员'
    else if (status) apiError.value = `请求失败（错误码 ${status}），请稍后重试`
    else apiError.value = '网络错误，无法连接到服务器，请检查网络连接'
  } finally {
    loading.value = false
  }
}

function setRange(key) {
  range.value = key
  if (key !== 'custom') loadDashboard()
}

function applyCustom() {
  if (customStart.value && customEnd.value && customStart.value > customEnd.value) {
    [customStart.value, customEnd.value] = [customEnd.value, customStart.value]
  }
  loadDashboard()
}

onMounted(loadDashboard)

// ── 排序：总 AC / 任一难度列 / 总提交 / AC 率 ─────────────────────
const sortKey = ref('total_ac')   // 'total_ac' | 'total_submit' | 'ac_rate' | 'diff:<难度>'
const sortDir = ref('desc')

function setSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc'
  }
}

function sortVal(r, key) {
  return key.startsWith('diff:') ? (r.by_diff[key.slice(5)] ?? 0) : r[key]
}

function arrow(key) {
  if (sortKey.value !== key) return '↕'
  return sortDir.value === 'asc' ? '▲' : '▼'
}

// 按当前排序键计算名次，同值同名次（与全站排行榜一致）
const sortedRanking = computed(() => {
  if (!data.value) return []
  const key = sortKey.value
  const mult = sortDir.value === 'desc' ? -1 : 1
  const rows = [...data.value.ranking].sort(
    (a, b) => mult * (sortVal(a, key) - sortVal(b, key)) || b.total_ac - a.total_ac,
  )
  const values = rows.map(r => sortVal(r, key)).sort((a, b) => b - a)
  const rankOf = new Map()
  values.forEach((v, i) => { if (!rankOf.has(v)) rankOf.set(v, i + 1) })
  return rows.map(r => ({ ...r, _rank: rankOf.get(sortVal(r, key)) }))
})

const diffLevels = computed(() => data.value?.diff_levels ?? [])
const stats = computed(() => data.value?.stats ?? {})
const team = computed(() => data.value?.team ?? {})
const canManage = computed(() => !!data.value?.can_manage)

// 迷你难度分布条：各难度占该生 AC 的比例
function miniBar(r) {
  if (!r.total_ac) return []
  return diffLevels.value
    .filter(d => r.by_diff[d])
    .map(d => ({ d, w: (r.by_diff[d] / r.total_ac) * 100, n: r.by_diff[d] }))
}

function fmtActive(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso)
  const day = Math.floor(diff / 86400000)
  if (day < 1) {
    const h = Math.floor(diff / 3600000)
    return h < 1 ? '刚刚' : `${h} 小时前`
  }
  if (day < 30) return `${day} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

const rangeLabel = computed(() => {
  const r = data.value?.range
  if (!r) return ''
  if (r.name === 'all') return '全部时间'
  return `${r.start || '最早'} ~ ${r.end || '今天'}`
})

const chartOption = computed(() => {
  const trend = data.value?.trend ?? []
  return {
    backgroundColor: 'transparent',
    grid: { top: 36, right: 20, bottom: 30, left: 40 },
    legend: { top: 0, right: 0, textStyle: { color: '#a1a1aa', fontSize: 12 }, itemWidth: 14, itemHeight: 8 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e5e7eb',
      textStyle: { color: '#52525b', fontSize: 12 }, borderRadius: 8,
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
    series: [
      {
        name: '提交数', type: 'line', data: trend.map(t => t.submit), smooth: true,
        symbol: 'circle', symbolSize: 4,
        lineStyle: { color: '#94a3b8', width: 1.5 }, itemStyle: { color: '#94a3b8' },
      },
      {
        name: 'AC 数', type: 'line', data: trend.map(t => t.count), smooth: true,
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
  }
})

async function doExport() {
  exporting.value = true
  try {
    const resp = await exportDashboard(teamId, rangeParams())
    saveBlobResponse(resp, `${team.value.name}_ranking.xlsx`)
  } catch {
    alert('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="dashboard" v-if="!loading && data">

    <!-- 顶部 -->
    <div class="dash-header">
      <button class="btn-back" @click="router.push(`/teacher/teams/${teamId}`)">← 团队</button>
      <div class="header-info">
        <h1 class="dash-title">{{ team.name }}</h1>
        <p class="dash-sub">团队总览<span v-if="!canManage"> · 只读（队长）</span></p>
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
        <div class="sc-label">总 AC（{{ stats.distinct_problems }} 道不同题）</div>
      </div>
      <div class="stat-card">
        <div class="sc-value green">{{ stats.week_new_ac }}</div>
        <div class="sc-label">本周新增 AC</div>
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
        <div>
          <h2 class="section-title">成员排行</h2>
          <span class="trend-hint">{{ rangeLabel }} · 点击表头排序，点击姓名查看详情</span>
        </div>
        <div class="range-bar">
          <div class="sort-tabs">
            <button
              v-for="r in RANGES" :key="r.key"
              :class="['sort-tab', range === r.key && 'sort-active']"
              @click="setRange(r.key)"
            >{{ r.label }}</button>
          </div>
          <div v-if="range === 'custom'" class="custom-range">
            <input v-model="customStart" type="date" class="date-input" />
            <span class="text-muted">~</span>
            <input v-model="customEnd" type="date" class="date-input" />
            <button class="btn-apply" @click="applyCustom">应用</button>
          </div>
        </div>
      </div>

      <div class="table-wrap">
        <table class="rank-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th>备注(姓名)</th>
              <th>学号</th>
              <th class="col-num sortable" :class="{ active: sortKey === 'total_ac' }" @click="setSort('total_ac')">
                总AC <span class="sort-arrow">{{ arrow('total_ac') }}</span>
              </th>
              <th
                v-for="d in diffLevels" :key="d"
                class="col-num col-diff-head sortable" :class="{ active: sortKey === `diff:${d}` }"
                :title="d" @click="setSort(`diff:${d}`)"
              >
                <span class="diff-dot" :style="{ background: DIFF_COLORS[d] }"></span>{{ DIFF_SHORT[d] }}
                <span class="sort-arrow">{{ arrow(`diff:${d}`) }}</span>
              </th>
              <th class="col-num sortable" :class="{ active: sortKey === 'total_submit' }" @click="setSort('total_submit')">
                总提交 <span class="sort-arrow">{{ arrow('total_submit') }}</span>
              </th>
              <th class="col-num sortable" :class="{ active: sortKey === 'ac_rate' }" @click="setSort('ac_rate')">
                AC率 <span class="sort-arrow">{{ arrow('ac_rate') }}</span>
              </th>
              <th class="col-num">最近活跃</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in sortedRanking" :key="r.user_id">
              <td class="col-rank">
                <span :class="['rank-badge', r._rank <= 3 ? `rank-${r._rank}` : '']">{{ r._rank }}</span>
              </td>
              <td>
                <span
                  class="member-name member-link"
                  @click="router.push(`/teacher/teams/${teamId}/students/${r.user_id}`)"
                >{{ r.display_name }}</span>
                <span v-if="r.role === 'captain'" class="crown">👑</span>
              </td>
              <td class="text-muted">{{ r.student_id || '—' }}</td>
              <td class="col-num" :class="{ 'col-active-val': sortKey === 'total_ac' }">
                <div class="ac-cell">
                  <span>{{ r.total_ac }}</span>
                  <span class="mini-bar" :title="miniBar(r).map(x => `${x.d}: ${x.n}`).join('\n')">
                    <span
                      v-for="seg in miniBar(r)" :key="seg.d"
                      class="mini-seg" :style="{ width: seg.w + '%', background: DIFF_COLORS[seg.d] }"
                    ></span>
                  </span>
                </div>
              </td>
              <td
                v-for="d in diffLevels" :key="d"
                class="col-num col-diff-val"
                :class="{ 'col-active-val': sortKey === `diff:${d}`, zero: !r.by_diff[d] }"
              >{{ r.by_diff[d] || 0 }}</td>
              <td class="col-num" :class="{ 'col-active-val': sortKey === 'total_submit' }">{{ r.total_submit }}</td>
              <td class="col-num" :class="{ 'col-active-val': sortKey === 'ac_rate' }">{{ r.ac_rate }}%</td>
              <td class="col-num text-muted nowrap">{{ fmtActive(r.last_active) }}</td>
            </tr>
            <tr v-if="sortedRanking.length === 0">
              <td :colspan="7 + diffLevels.length" class="empty-td">暂无成员数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 30 天趋势 -->
    <div class="section-card">
      <div class="section-head">
        <h2 class="section-title">近 30 天趋势</h2>
        <span class="trend-hint">全团每日提交数 / 去重 AC 数</span>
      </div>
      <v-chart class="trend-chart" :option="chartOption" autoresize />
    </div>

  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>
  <div v-else class="error-wrap">
    <p class="error-msg">{{ apiError || '未知错误' }}</p>
    <div class="error-actions">
      <button class="btn-retry" @click="loadDashboard">重试</button>
      <button class="btn-back-err" @click="router.back()">← 返回</button>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1240px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }

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
  padding: 0.55rem 0.55rem; text-align: left;
  color: var(--text-muted); font-weight: 500;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
.rank-table td { padding: 0.55rem 0.55rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.rank-table tr:last-child td { border-bottom: none; }

.col-rank { width: 3rem; text-align: center; }
.rank-table th.col-num,
.col-num { text-align: right; }
.col-diff-head { color: var(--text-muted); font-size: 0.78rem; }
.col-diff-val { color: var(--text-secondary); font-size: 0.83rem; }
.col-active-val { color: var(--accent); font-weight: 600; }
.sortable { cursor: pointer; user-select: none; }
.rank-table th.sortable.active { color: var(--accent); }
.rank-table th.sortable:hover { color: var(--text-primary); }
.sort-arrow { opacity: 0.45; font-size: 0.72rem; margin-left: 0.15rem; }
.rank-table th.sortable.active .sort-arrow { opacity: 1; color: var(--accent); }

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
.error-wrap { text-align: center; padding: 4rem 2rem; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
.error-msg { color: #f87171; font-size: 0.95rem; margin: 0; max-width: 480px; }
.error-actions { display: flex; gap: 0.75rem; }
.btn-retry {
  background: var(--accent); color: #fff; border: none;
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-retry:hover { opacity: 0.88; }
.btn-back-err {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-back-err:hover { border-color: var(--text-secondary); }

.range-bar { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; }
.custom-range { display: flex; align-items: center; gap: 0.4rem; }
.date-input {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--text-primary);
  border-radius: 6px; padding: 0.2rem 0.45rem; font-size: 0.8rem;
}
.date-input:focus { outline: none; border-color: var(--accent); }
.btn-apply {
  background: var(--accent); color: #fff; border: none; border-radius: 6px;
  padding: 0.25rem 0.75rem; font-size: 0.8rem; cursor: pointer;
}
.diff-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 0.25rem; vertical-align: middle; }
.col-diff-val.zero { color: var(--text-muted); opacity: 0.6; }
.ac-cell { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
.mini-bar { display: flex; width: 56px; height: 4px; border-radius: 2px; overflow: hidden; background: var(--bg-secondary); }
.mini-seg { height: 100%; }
.nowrap { white-space: nowrap; }
@media (max-width: 760px) { .section-head { flex-direction: column; align-items: flex-start; } .range-bar { align-items: flex-start; } }
</style>
