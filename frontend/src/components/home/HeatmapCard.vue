<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** @type {{ date: string, count: number }[]} */
  submissions: { type: Array, default: () => [] }
})

function toDateStr(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getLevel(count) {
  if (count === 0) return 0
  if (count <= 2)  return 1
  if (count <= 5)  return 2
  if (count <= 9)  return 3
  return 4
}

const countMap = computed(() => {
  const m = {}
  props.submissions.forEach(s => { m[s.date] = s.count })
  return m
})

// 16 weeks ending with the current week, columns = weeks, rows = Sun–Sat
const weeks = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // Sunday of the current week
  const thisSunday = new Date(today)
  thisSunday.setDate(today.getDate() - today.getDay())

  // Sunday 15 weeks earlier → gives 16 weeks total
  const startSunday = new Date(thisSunday)
  startSunday.setDate(thisSunday.getDate() - 15 * 7)

  const result = []
  for (let w = 0; w < 16; w++) {
    const weekSunday = new Date(startSunday)
    weekSunday.setDate(startSunday.getDate() + w * 7)
    const week = []
    for (let d = 0; d < 7; d++) {
      const cur = new Date(weekSunday)
      cur.setDate(weekSunday.getDate() + d)
      if (cur > today) {
        week.push({ date: '', count: 0, level: -1, empty: true })
      } else {
        const ds = toDateStr(cur)
        const count = countMap.value[ds] || 0
        week.push({ date: ds, count, level: getLevel(count), empty: false })
      }
    }
    result.push(week)
  }
  return result
})

// Month label: one label per month transition, positioned by column index
const monthLabels = computed(() => {
  const labels = []
  let lastMonth = -1
  weeks.value.forEach((week, wi) => {
    const firstReal = week.find(d => !d.empty && d.date)
    if (!firstReal) return
    const month = parseInt(firstReal.date.split('-')[1]) - 1
    if (month !== lastMonth) {
      labels.push({ month, col: wi })
      lastMonth = month
    }
  })
  return labels
})

const MONTH_NAMES = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
// row labels: show Mon / Wed / Fri (indices 1, 3, 5)
const ROW_LABELS = ['', '一', '', '三', '', '五', '']
</script>

<template>
  <div class="heatmap-card card">
    <div class="card-head">
      <span class="card-title">刷题热力图</span>
      <span class="card-sub">最近 16 周</span>
    </div>

    <div class="heatmap-wrap">
      <!-- Month labels row -->
      <div class="month-row">
        <div class="row-label-spacer"></div>
        <div class="month-track">
          <span
            v-for="(lbl, i) in monthLabels"
            :key="i"
            class="month-lbl"
            :style="{ left: lbl.col * 13 + 'px' }"
          >{{ MONTH_NAMES[lbl.month] }}</span>
        </div>
      </div>

      <!-- Grid -->
      <div class="grid-row">
        <!-- Day-of-week labels -->
        <div class="row-labels">
          <span v-for="(lbl, i) in ROW_LABELS" :key="i" class="row-lbl">{{ lbl }}</span>
        </div>
        <!-- Week columns -->
        <div class="weeks">
          <div v-for="(week, wi) in weeks" :key="wi" class="week-col">
            <div
              v-for="(day, di) in week"
              :key="di"
              class="cell"
              :class="day.empty ? 'cell-empty' : `level-${day.level}`"
              :title="day.empty ? '' : `${day.date}：${day.count} 次提交`"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="legend">
      <span class="legend-txt">少</span>
      <div v-for="l in [0,1,2,3,4]" :key="l" class="cell" :class="`level-${l}`"></div>
      <span class="legend-txt">多</span>
    </div>
  </div>
</template>

<style scoped>
.heatmap-card {
  padding: 16px 20px 14px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.card-sub {
  font-size: 12px;
  color: var(--text-muted);
}

.heatmap-wrap {
  overflow-x: auto;
}

/* Month label row */
.month-row {
  display: flex;
  align-items: flex-end;
  margin-bottom: 3px;
}
.row-label-spacer {
  width: 18px;
  flex-shrink: 0;
}
.month-track {
  position: relative;
  height: 14px;
  flex: 1;
}
.month-lbl {
  position: absolute;
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
  top: 0;
}

/* Grid row */
.grid-row {
  display: flex;
  gap: 4px;
}
.row-labels {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 14px;
  flex-shrink: 0;
}
.row-lbl {
  height: 11px;
  font-size: 9px;
  color: var(--text-muted);
  line-height: 11px;
  text-align: right;
}

.weeks {
  display: flex;
  gap: 2px;
}
.week-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cell {
  width: 11px;
  height: 11px;
  border-radius: 2px;
}
.cell-empty  { background: transparent; }
.level-0 { background: var(--heatmap-0); }
.level-1 { background: var(--heatmap-1); }
.level-2 { background: var(--heatmap-2); }
.level-3 { background: var(--heatmap-3); }
.level-4 { background: var(--heatmap-4); }

/* Legend */
.legend {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 10px;
  justify-content: flex-end;
}
.legend-txt {
  font-size: 10px;
  color: var(--text-muted);
  margin: 0 2px;
}
</style>
