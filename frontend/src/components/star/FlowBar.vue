<script setup>
// 学习流程条：共几步、现在第几步、哪几步做完了。一屏一步，学习者随时知道还剩多少。
defineProps({
  total: { type: Number, required: true },
  current: { type: Number, required: true },   // 从 0 起
  done: { type: Array, default: () => [] },
  unit: { type: String, default: '步' },
})
</script>

<template>
  <div class="flow" role="group" :aria-label="`第 ${current + 1} ${unit}，共 ${total} ${unit}`">
    <div class="flow-text">第 <b>{{ current + 1 }}</b> {{ unit }} / 共 {{ total }} {{ unit }}</div>
    <ol class="flow-bar">
      <li
        v-for="i in total"
        :key="i"
        :class="{ 'is-current': i - 1 === current, 'is-done': done.includes(i - 1) }"
      >
        <span v-if="done.includes(i - 1)">✓<span class="sr-only">已完成</span></span>
        <span v-else>{{ i }}</span>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.flow { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.flow-text { font-weight: 600; white-space: nowrap; }
.flow-bar {
  display: flex;
  gap: 8px;
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
  min-width: 200px;
}
.flow-bar li {
  flex: 1;
  min-width: 40px;
  height: 40px;
  border: 2px solid var(--s-border-strong);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--s-text-2);
  background: var(--s-card);
}
.flow-bar li.is-done { border-color: var(--s-ok); background: var(--s-ok-soft); color: var(--s-ok); }
.flow-bar li.is-current { border-color: var(--s-accent); background: var(--s-accent); color: #fff; }
.sr-only {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}
</style>
