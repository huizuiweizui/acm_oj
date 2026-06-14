<script setup>
import { useRouter } from 'vue-router'
import StatsInline from './StatsInline.vue'

defineProps({
  stats: {
    type: Object,
    default: () => ({ problemCount: 0, userCount: 0 })
  }
})

const router = useRouter()
</script>

<template>
  <section class="hero">
    <h1 class="hero-title">ACM 算法教学平台</h1>
    <p class="hero-sub">让算法训练更高效 · 支持 ICPC / IOI 赛制 · AI 辅助讲解</p>
    <div class="hero-actions">
      <button class="btn-primary" @click="router.push({ name: 'problem-list' })">开始刷题</button>
      <button class="btn-outline" @click="router.push({ name: 'problem-list' })">进入题库</button>
    </div>
    <StatsInline :problem-count="stats.problemCount" :user-count="stats.userCount" />
  </section>
</template>

<style scoped>
.hero {
  padding: 48px 0 36px;
}
.hero-title {
  font-size: 28px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 10px;
  letter-spacing: -0.3px;
}
.hero-sub {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0 0 24px;
  line-height: 1.6;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.btn-primary {
  padding: 8px 22px;
  background: var(--home-accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover {
  background: var(--home-accent-hover);
}
.btn-outline {
  padding: 7px 22px;
  background: transparent;
  color: var(--home-accent);
  border: 1px solid var(--home-accent);
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-outline:hover {
  background: var(--home-accent-light);
}
</style>
