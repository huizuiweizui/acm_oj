<script setup>
defineProps({ difficulty: String })

const colorMap = {
  '入门':          '#5cb85c',
  '普及-':         '#2185d0',
  '普及/提高-':    '#2185d0',
  '普及+/提高':    '#a0a0f0',
  '提高+/省选-':   '#ffcc00',
  '省选/NOI-':     '#ff8800',
  'NOI/NOI+/CTSC': '#e03131',
  '暂无评定':      '#888',
}
</script>

<template>
  <span class="badge" :style="{ background: colorMap[difficulty] ?? '#888' }">
    {{ difficulty }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #fff;
  white-space: nowrap;
  font-weight: 500;
}
</style>
