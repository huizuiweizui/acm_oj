<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { CalendarComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'

use([CanvasRenderer, HeatmapChart, CalendarComponent, TooltipComponent, VisualMapComponent])

const props = defineProps({
  acByDate: { type: Object, default: () => ({}) },
})

const option = computed(() => {
  const today = new Date()
  const yearAgo = new Date(today)
  yearAgo.setFullYear(today.getFullYear() - 1)
  const fmt = (d) => d.toISOString().slice(0, 10)

  const data = Object.entries(props.acByDate).map(([date, cnt]) => [date, cnt])

  return {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (p) => `${p.data[0]}<br/>AC: ${p.data[1]} 次`,
      backgroundColor: '#fff', borderColor: '#e5e7eb', borderWidth: 1,
      textStyle: { color: '#52525b', fontSize: 12 }, borderRadius: 8,
    },
    visualMap: {
      min: 0, max: 5,
      inRange: { color: ['#f0fdf4', '#bbf7d0', '#4ade80', '#16a34a', '#14532d'] },
      show: false,
    },
    calendar: {
      range: [fmt(yearAgo), fmt(today)],
      cellSize: [13, 13],
      left: 30, right: 0, top: 20, bottom: 0,
      itemStyle: { borderWidth: 2, borderColor: 'transparent' },
      dayLabel: { color: '#a1a1aa', fontSize: 10, firstDay: 1 },
      monthLabel: { color: '#a1a1aa', fontSize: 10 },
      yearLabel: { show: false },
      splitLine: { show: false },
    },
    series: [{
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data,
    }],
  }
})
</script>

<template>
  <div class="chart-wrap">
    <VChart :option="option" autoresize style="height:120px; width:100%" />
  </div>
</template>

<style scoped>
.chart-wrap { width: 100%; overflow-x: auto; }
</style>
