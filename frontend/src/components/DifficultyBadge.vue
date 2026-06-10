<script setup>
defineProps({ difficulty: String })

const styleMap = {
  '暂无评定':      { bg: 'rgba(191,191,191,0.15)', color: '#6b7280',  dot: '#bfbfbf' },
  '入门':          { bg: 'rgba(254,76,97,0.12)',   color: '#dc2626',  dot: '#fe4c61' },
  '普及-':         { bg: 'rgba(243,156,17,0.12)',  color: '#b45309',  dot: '#f39c11' },
  '普及/提高-':    { bg: 'rgba(255,193,22,0.15)',  color: '#92400e',  dot: '#ffc116' },
  '普及+/提高':    { bg: 'rgba(82,196,26,0.12)',   color: '#15803d',  dot: '#52c41a' },
  '提高+/省选-':   { bg: 'rgba(52,152,219,0.12)',  color: '#1d4ed8',  dot: '#3498db' },
  '省选/NOI-':     { bg: 'rgba(157,61,207,0.12)',  color: '#7e22ce',  dot: '#9d3dcf' },
  'NOI/NOI+/CTSC': { bg: 'rgba(14,29,105,0.12)',  color: '#0e1d69',  dot: '#0e1d69' },
}
</script>

<template>
  <span class="badge" :style="{ background: (styleMap[difficulty] ?? styleMap['暂无评定']).bg, color: (styleMap[difficulty] ?? styleMap['暂无评定']).color }">
    <span class="dot" :style="{ background: (styleMap[difficulty] ?? styleMap['暂无评定']).dot }"></span>
    {{ difficulty }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
</style>
