<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

/**
 * @typedef {Object} RecommendProblem
 * @property {number|string} id
 * @property {string} title
 * @property {string} difficulty  — '入门' | '简单' | '中等' | '困难'
 * @property {string} reason
 * @property {'assignment'|'retry'|'practice'} [kind]
 */

const props = defineProps({
  /** @type {RecommendProblem|null} 只有一道时用 */
  problem: { type: Object, default: null },
  /** @type {RecommendProblem[]} 后端 /api/recommend/ 返回的列表，可"换一道" */
  problems: { type: Array, default: () => [] },
})

const list = computed(() => (props.problems.length ? props.problems : props.problem ? [props.problem] : []))
const idx = ref(0)
watch(list, () => { idx.value = 0 })
const current = computed(() => list.value[idx.value % Math.max(1, list.value.length)] ?? null)
const KIND_TEXT = { assignment: '作业', retry: '再试一次', practice: '练习' }
function next() { idx.value = (idx.value + 1) % list.value.length }

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
      <button v-if="list.length > 1" class="next-btn" @click="next">换一道（{{ idx + 1 }}/{{ list.length }}）</button>
    </div>

    <template v-if="current">
      <div class="problem-meta">
        <span class="problem-id">#{{ current.id }}</span>
        <span
          class="diff-badge"
          :style="{ background: diffStyle(current.difficulty).bg, color: diffStyle(current.difficulty).color }"
        >{{ current.difficulty }}</span>
        <span v-if="current.kind" class="kind-badge">{{ KIND_TEXT[current.kind] }}</span>
      </div>
      <p class="problem-title">{{ current.title }}</p>
      <p class="reason">{{ current.reason }}</p>
      <button
        class="solve-btn"
        @click="router.push({ name: 'problem-detail', params: { id: current.id } })"
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.next-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}
.next-btn:hover {
  color: var(--home-accent);
}
.kind-badge {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
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
