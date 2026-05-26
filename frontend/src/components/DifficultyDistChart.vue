<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { TooltipComponent, GridComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, TooltipComponent, GridComponent])

const DIFFICULTY_ORDER = [
  '入门', '普及-', '普及/提高-', '普及+/提高',
  '提高+/省选-', '省选/NOI-', 'NOI/NOI+/CTSC', '暂无评定',
]
const DIFF_COLORS = {
  '入门':          '#5cb85c',
  '普及-':         '#2185d0',
  '普及/提高-':    '#2185d0',
  '普及+/提高':    '#a0a0f0',
  '提高+/省选-':   '#ffcc00',
  '省选/NOI-':     '#ff8800',
  'NOI/NOI+/CTSC': '#e03131',
  '暂无评定':      '#666',
}

const props = defineProps({
  acByDifficulty: { type: Object, default: () => ({}) },
})

const option = computed(() => {
  const keys = DIFFICULTY_ORDER.filter(d => props.acByDifficulty[d] != null)
  const values = keys.map(d => props.acByDifficulty[d])

  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 40, right: 10, top: 10, bottom: 50 },
    xAxis: {
      type: 'category', data: keys,
      axisLabel: { color: '#888', fontSize: 9, rotate: 20 },
      axisLine: { lineStyle: { color: '#2d2d4e' } },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLabel: { color: '#666', fontSize: 10 },
      splitLine: { lineStyle: { color: '#1e1e38' } },
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: DIFF_COLORS[keys[i]] ?? '#7c6af7', borderRadius: [3, 3, 0, 0] },
      })),
      barMaxWidth: 32,
    }],
  }
})
</script>

<template>
  <VChart :option="option" autoresize style="height:200px; width:100%" />
</template>
