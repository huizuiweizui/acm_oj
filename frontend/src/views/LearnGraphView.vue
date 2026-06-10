<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, GraphChart, TooltipComponent, LegendComponent])

const router = useRouter()
const chartRef = ref(null)
const loading = ref(true)
const rawNodes = ref([])
const rawEdges = ref([])

// 主题检测：监听 <html data-theme="..."> 变化
const isDark = ref(document.documentElement.getAttribute('data-theme') !== 'light')
let themeObserver = null
onMounted(() => {
  themeObserver = new MutationObserver(() => {
    isDark.value = document.documentElement.getAttribute('data-theme') !== 'light'
  })
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})
onUnmounted(() => themeObserver?.disconnect())

// 主题相关颜色
const theme = computed(() => isDark.value ? {
  labelColor:    '#e0e0f0',
  tooltipBg:     'rgba(15,23,42,0.93)',
  tooltipBorder: '#334155',
  tooltipText:   '#e2e8f0',
  tooltipMuted:  '#94a3b8',
  tooltipFaint:  '#64748b',
  legendText:    '#94a3b8',
  edgeRelated:   '#475569',
  edgeRelOpacity: 0.45,
} : {
  labelColor:    '#18181b',
  tooltipBg:     '#ffffff',
  tooltipBorder: '#e5e7eb',
  tooltipText:   '#18181b',
  tooltipMuted:  '#52525b',
  tooltipFaint:  '#a1a1aa',
  legendText:    '#a1a1aa',
  edgeRelated:   '#d1d5db',
  edgeRelOpacity: 0.6,
})

const selectedDiff = ref([])
const hiddenCategories = ref(new Set())

const DIFF_COLORS = { '入门': '#22c55e', '提高': '#f59e0b', '进阶': '#ef4444' }
const CAT_COLORS = {
  '基础算法': '#7c6af7',
  '排序':    '#22d3ee',
  '搜索':    '#3b82f6',
  '贪心':    '#10b981',
  '动态规划': '#f59e0b',
  '图论':    '#f97316',
  '数据结构': '#ec4899',
  '字符串':  '#8b5cf6',
  '数学':    '#06b6d4',
}
const CATEGORIES = Object.keys(CAT_COLORS)
const DIFFICULTIES = ['入门', '提高', '进阶']

// 每个节点的总出入度（用于控制节点大小）
const degreeMap = computed(() => {
  const m = {}
  for (const e of rawEdges.value) {
    m[e.source] = (m[e.source] || 0) + 1
    m[e.target] = (m[e.target] || 0) + 1
  }
  return m
})

const visibleNodeIds = computed(() => {
  const set = new Set()
  for (const n of rawNodes.value) {
    if (hiddenCategories.value.has(n.category)) continue
    if (selectedDiff.value.length && !selectedDiff.value.includes(n.difficulty)) continue
    set.add(n.id)
  }
  return set
})

// 按 algo_id 快查节点
const nodeById = computed(() => Object.fromEntries(rawNodes.value.map(n => [n.id, n])))

// 可见节点连接数（用于 tooltip）
const visibleDegree = computed(() => {
  const ids = visibleNodeIds.value
  const m = {}
  for (const e of rawEdges.value) {
    if (!ids.has(e.source) || !ids.has(e.target)) continue
    m[e.source] = (m[e.source] || 0) + 1
    m[e.target] = (m[e.target] || 0) + 1
  }
  return m
})

function nodeSize(id, difficulty) {
  const deg = degreeMap.value[id] || 0
  // base: 入门14 提高18 进阶22；degree 每增1 加1，最大 42
  const base = difficulty === '进阶' ? 22 : difficulty === '提高' ? 18 : 14
  return Math.min(42, base + deg)
}

const option = computed(() => {
  const ids = visibleNodeIds.value
  const nodes = rawNodes.value
    .filter(n => ids.has(n.id))
    .map(n => ({
      id:         n.id,
      name:       n.name,
      category:   CATEGORIES.indexOf(n.category),
      label:      { show: true, color: theme.value.labelColor, fontSize: 10, fontWeight: 500 },
      itemStyle:  { color: CAT_COLORS[n.category] || '#888', borderWidth: 0 },
      symbolSize: nodeSize(n.id, n.difficulty),
    }))

  const edges = rawEdges.value
    .filter(e => ids.has(e.source) && ids.has(e.target))
    .map(e => ({
      source: e.source,
      target: e.target,
      lineStyle: {
        color:   e.type === 'prerequisite' ? '#f87171'
               : e.type === 'extends'      ? '#a78bfa'
               : theme.value.edgeRelated,
        width:   e.type === 'related' ? 1 : 1.8,
        type:    e.type === 'related' ? 'dashed' : 'solid',
        opacity: e.type === 'related' ? theme.value.edgeRelOpacity : 0.75,
        curveness: 0.05,
      },
    }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      confine: true,
      backgroundColor: theme.value.tooltipBg,
      borderColor: theme.value.tooltipBorder,
      textStyle: { color: theme.value.tooltipText, fontSize: 12 },
      formatter: (params) => {
        if (params.dataType !== 'node') return ''
        const n = nodeById.value[params.data.id]
        if (!n) return ''
        const t = theme.value
        const deg = visibleDegree.value[n.id] || 0
        return `<b style="font-size:13px;color:${t.tooltipText}">${n.name}</b>
          <div style="color:${t.tooltipMuted};margin:2px 0 6px">${n.name_en}</div>
          <span style="color:${CAT_COLORS[n.category]}">${n.category}</span>
          &nbsp;&nbsp;
          <span style="color:${DIFF_COLORS[n.difficulty]}">${n.difficulty}</span>
          <div style="margin-top:6px;color:${t.tooltipMuted}">连接数：${deg}</div>
          <div style="margin-top:2px;color:${t.tooltipFaint};font-size:11px">点击跳转到详情页</div>`
      },
    },
    legend: [{
      data: CATEGORIES.map(c => ({ name: c, itemStyle: { color: CAT_COLORS[c] } })),
      bottom: 6,
      textStyle: { color: theme.value.legendText, fontSize: 10.5 },
      itemWidth: 10, itemHeight: 10, itemGap: 12,
      selected: Object.fromEntries(CATEGORIES.map(c => [c, !hiddenCategories.value.has(c)])),
    }],
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      focusNodeAdjacency: true,
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 7],
      force: {
        repulsion: 340,
        edgeLength: [60, 200],
        gravity: 0.06,
        friction: 0.6,
        layoutAnimation: true,
      },
      categories: CATEGORIES.map(c => ({ name: c, itemStyle: { color: CAT_COLORS[c] } })),
      nodes,
      edges,
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3 },
        label: { show: true, fontSize: 12, fontWeight: 700, color: theme.value.labelColor },
      },
      blur: { itemStyle: { opacity: 0.15 }, lineStyle: { opacity: 0.07 } },
    }],
  }
})

function onChartClick(params) {
  if (params.dataType === 'node') {
    router.push({ name: 'learn-detail', params: { id: params.data.id } })
  }
}

function onLegendChange(params) {
  if (params.selected[params.name] === false) {
    hiddenCategories.value = new Set([...hiddenCategories.value, params.name])
  } else {
    const s = new Set(hiddenCategories.value)
    s.delete(params.name)
    hiddenCategories.value = s
  }
}

function toggleDiff(d) {
  if (selectedDiff.value.includes(d)) {
    selectedDiff.value = selectedDiff.value.filter(x => x !== d)
  } else {
    selectedDiff.value = [...selectedDiff.value, d]
  }
}

function resetView() {
  chartRef.value?.chart?.dispatchAction({ type: 'restore' })
}

onMounted(async () => {
  const res = await fetch('/api/algorithms/graph/')
  const data = await res.json()
  rawNodes.value = data.nodes
  rawEdges.value = data.edges
  loading.value = false
})
</script>

<template>
  <div class="graph-page">

    <!-- Header -->
    <div class="graph-header">
      <div>
        <h1 class="graph-title">算法知识图谱</h1>
        <p class="graph-sub">
          {{ visibleNodeIds.size }} 个算法 · {{ rawEdges.filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)).length }} 条关系
          &nbsp;—&nbsp;探索依赖与关联，规划学习路径
        </p>
      </div>
      <div class="header-right">
        <div class="graph-legend-wrap">
          <span class="leg-item"><span class="leg-line prereq"></span>前置依赖</span>
          <span class="leg-item"><span class="leg-line extends"></span>扩展应用</span>
          <span class="leg-item"><span class="leg-line related"></span>相关算法</span>
        </div>
        <button class="reset-btn" @click="resetView" title="重置视图">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
          重置视图
        </button>
      </div>
    </div>

    <!-- 难度筛选 -->
    <div class="diff-filter">
      <span class="filter-label">难度：</span>
      <button
        v-for="d in DIFFICULTIES" :key="d"
        class="diff-btn"
        :class="[`diff-${d}`, { active: selectedDiff.includes(d) }]"
        @click="toggleDiff(d)"
      >{{ d }}</button>
      <button
        v-if="selectedDiff.length"
        class="diff-btn clear"
        @click="selectedDiff = []"
      >清除</button>
      <span class="filter-sep"></span>
      <span class="filter-label">节点大小由连接数决定 · 悬停查看详情</span>
    </div>

    <!-- 图 -->
    <div class="chart-wrap">
      <div v-if="loading" class="loading-box">
        <div class="spinner"></div>
        <p>加载图谱中…</p>
      </div>
      <VChart
        v-else
        ref="chartRef"
        class="graph-chart"
        :option="option"
        autoresize
        @click="onChartClick"
        @legendselectchanged="onLegendChange"
      />
    </div>

    <p class="graph-hint">点击节点跳转详情 · 滚轮缩放 · 拖拽平移 · 点击空白取消高亮</p>
  </div>
</template>

<style scoped>
.graph-page {
  display: flex; flex-direction: column; height: calc(100vh - 56px);
  padding: 0; overflow: hidden;
}

/* Header */
.graph-header {
  display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap;
  gap: 12px; padding: 16px 24px 10px; flex-shrink: 0;
}
.graph-title {
  font-size: 1.6rem; font-weight: 800; margin: 0 0 4px;
  background: linear-gradient(135deg, #7c6af7, #22d3ee);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.graph-sub { color: var(--text-muted); font-size: 0.83rem; margin: 0; }

.header-right { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }

/* Legend */
.graph-legend-wrap { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
.leg-item { display: flex; align-items: center; gap: 5px; font-size: 0.78rem; color: var(--text-muted); }
.leg-line { display: inline-block; width: 24px; height: 2px; border-radius: 2px; }
.leg-line.prereq  { background: #f87171; }
.leg-line.extends { background: #a78bfa; }
.leg-line.related { background: transparent; border-top: 2px dashed #a1a1aa; height: 0; }

/* Reset button */
.reset-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text-muted); font-size: 0.78rem; cursor: pointer;
  transition: all 0.15s;
}
.reset-btn:hover { border-color: var(--accent); color: var(--accent); }

/* Diff filter */
.diff-filter {
  display: flex; align-items: center; gap: 7px; padding: 0 24px 8px;
  flex-shrink: 0; flex-wrap: wrap;
}
.filter-label { font-size: 0.78rem; color: var(--text-muted); }
.filter-sep { flex: 1; }
.diff-btn {
  padding: 3px 12px; border-radius: 20px; border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-muted);
  font-size: 0.78rem; font-weight: 500; cursor: pointer; transition: all 0.15s;
}
.diff-btn.diff-入门.active  { border-color: #22c55e; color: #22c55e; background: rgba(34,197,94,0.12); }
.diff-btn.diff-提高.active  { border-color: #f59e0b; color: #f59e0b; background: rgba(245,158,11,0.12); }
.diff-btn.diff-进阶.active  { border-color: #ef4444; color: #ef4444; background: rgba(239,68,68,0.12); }
.diff-btn.clear             { border-color: var(--accent); color: var(--accent); }
.diff-btn:hover:not(.active){ border-color: var(--accent); color: var(--accent); }

/* Chart */
.chart-wrap {
  flex: 1; min-height: 0; position: relative;
  margin: 0 16px; border: 1px solid var(--border); border-radius: 12px;
  background: var(--bg-card); overflow: hidden;
}
.graph-chart { width: 100%; height: 100%; }

.loading-box {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  color: var(--text-muted); font-size: 0.9rem;
}
.spinner {
  width: 32px; height: 32px; border: 3px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Hint */
.graph-hint {
  text-align: center; font-size: 0.73rem; color: var(--text-muted);
  padding: 5px 0 7px; flex-shrink: 0; margin: 0;
}
</style>
