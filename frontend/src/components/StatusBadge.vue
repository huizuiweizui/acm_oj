<script setup>
defineProps({ status: String })

const cfg = {
  AC:      { label: 'AC',      color: '#2ecc71' },
  WA:      { label: 'WA',      color: '#e74c3c' },
  TLE:     { label: 'TLE',     color: '#e67e22' },
  MLE:     { label: 'MLE',     color: '#e67e22' },
  RE:      { label: 'RE',      color: '#9b59b6' },
  CE:      { label: 'CE',      color: '#e74c3c' },
  Pending: { label: '等待中',  color: '#95a5a6' },
  Judging: { label: '评测中',  color: '#3498db' },
}
</script>

<template>
  <span class="badge" :style="{ color: cfg[status]?.color ?? '#aaa', borderColor: cfg[status]?.color ?? '#aaa' }">
    {{ cfg[status]?.label ?? status }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid;
}
</style>
