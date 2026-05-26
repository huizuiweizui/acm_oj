<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const props = defineProps({
  languageDist: { type: Object, default: () => ({}) },
})

const COLORS = ['#7c6af7', '#3b82f6', '#10b981', '#f59e0b', '#ef4444']

const option = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)' },
  legend: {
    bottom: 0, textStyle: { color: '#888', fontSize: 11 },
    itemWidth: 10, itemHeight: 10,
  },
  series: [{
    type: 'pie',
    radius: ['45%', '72%'],
    center: ['50%', '44%'],
    data: Object.entries(props.languageDist).map(([name, value], i) => ({
      name, value, itemStyle: { color: COLORS[i % COLORS.length] },
    })),
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 12, color: '#e0e0f0' } },
  }],
}))
</script>

<template>
  <VChart :option="option" autoresize style="height:200px; width:100%" />
</template>
