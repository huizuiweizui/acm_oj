<script setup>
import { useRouter } from 'vue-router'

/**
 * @typedef {Object} RecommendProblem
 * @property {number|string} id
 * @property {string} title
 * @property {string} difficulty  — '入门' | '简单' | '中等' | '困难'
 * @property {string} reason
 */

defineProps({
  /** @type {RecommendProblem|null} */
  problem: { type: Object, default: null }
})

const router = useRouter()

const DIFF_STYLE = {
  '入门': { bg: '#f0fdf4', color: '#166534' },
  '简单': { bg: '#f0fdf4', color: '#166534' },
  '中等': { bg: '#fefce8', color: '#854d0e' },
  '困难': { bg: '#fef2f2', color: '#991b1b' },
}
function diffStyle(d) {
  return DIFF_STYLE[d] ?? { bg: '#f1f5f9', color: '#475569' }
}
</script>

<template>
  <div class="recommend-card card">
    <div class="card-head">
      <span class="card-title">今日推荐</span>
    </div>

    <template v-if="problem">
      <div class="problem-meta">
        <span class="problem-id">#{{ problem.id }}</span>
        <span
          class="diff-badge"
          :style="{ background: diffStyle(problem.difficulty).bg, color: diffStyle(problem.difficulty).color }"
        >{{ problem.difficulty }}</span>
      </div>
      <p class="problem-title">{{ problem.title }}</p>
      <p class="reason">{{ problem.reason }}</p>
      <button
        class="solve-btn"
        @click="router.push({ name: 'problem-detail', params: { id: problem.id } })"
      >去做题 →</button>
    </template>

    <div v-else class="empty">暂无推荐题目</div>
  </div>
</template>

<style scoped>
.recommend-card {
  padding: 16px 20px;
  height: 100%;
  box-sizing: border-box;
}
.card-head {
  margin-bottom: 14px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.problem-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.problem-id {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
}
.diff-badge {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 500;
}
.problem-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 8px;
  line-height: 1.4;
}
.reason {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 0 18px;
  line-height: 1.55;
}
.solve-btn {
  display: inline-block;
  padding: 6px 16px;
  background: var(--home-accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.solve-btn:hover {
  background: var(--home-accent-hover);
}

.empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 28px 0;
  text-align: center;
}
</style>
