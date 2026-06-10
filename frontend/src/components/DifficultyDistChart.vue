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
  '暂无评定':      '#bfbfbf',
  '入门':          '#fe4c61',
  '普及-':         '#f39c11',
  '普及/提高-':    '#ffc116',
  '普及+/提高':    '#52c41a',
  '提高+/省选-':   '#3498db',
  '省选/NOI-':     '#9d3dcf',
  'NOI/NOI+/CTSC': '#0e1d69',
}

const props = defineProps({
  acByDifficulty: { type: Object, default: () => ({}) },
})

const option = computed(() => {
  const keys = DIFFICULTY_ORDER.filter(d => props.acByDifficulty[d] != null)
  const values = keys.map(d => props.acByDifficulty[d])

  return {
    backgroundColor: 'transparent',
    grid: { left: 40, right: 10, top: 10, bottom: 50 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      backgroundColor: '#fff', borderColor: '#e5e7eb', borderWidth: 1,
      textStyle: { color: '#52525b', fontSize: 12 }, borderRadius: 8,
    },
    xAxis: {
      type: 'category', data: keys,
      axisLabel: { color: '#a1a1aa', fontSize: 9, rotate: 20 },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLabel: { color: '#a1a1aa', fontSize: 10 },
      splitLine: { lineStyle: { color: '#e5e7eb', type: 'dashed' } },
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
