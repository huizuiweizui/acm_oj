<script setup>
defineProps({
  problemCount: { type: Number, default: 0 },
  userCount:    { type: Number, default: 0 }
})
</script>

<template>
  <p class="stats-line">
    {{ problemCount }} 道题目 · {{ userCount }} 位用户 · 持续更新中
  </p>
</template>

<style scoped>
.stats-line {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
