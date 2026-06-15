<script setup>
import { ref } from 'vue'

const props = defineProps({
  streak:    { type: Number,  default: 0 },
  checkedIn: { type: Boolean, default: false },
  fortune:   { type: Object,  default: null },
})

const emit = defineEmits(['checkin'])

const loading = ref(false)

async function doCheckin() {
  loading.value = true
  try {
    emit('checkin')
  } finally {
    loading.value = false
  }
}

const MOOD_STYLE = {
  '大吉': { color: '#dc2626', bg: '#fef2f2' },
  '中吉': { color: '#d97706', bg: '#fffbeb' },
  '小吉': { color: '#16a34a', bg: '#f0fdf4' },
  '末吉': { color: '#6366f1', bg: '#eef2ff' },
  '凶':   { color: '#6b7280', bg: '#f9fafb' },
}
function moodStyle(mood) {
  return MOOD_STYLE[mood] ?? { color: '#6b7280', bg: '#f9fafb' }
}
</script>

<template>
  <div class="checkin-card card">
    <!-- Header -->
    <div class="card-head">
      <span class="card-title">每日打卡</span>
      <span v-if="streak > 0" class="streak-badge">连续 {{ streak }} 天</span>
    </div>

    <!-- Not checked in -->
    <div v-if="!checkedIn" class="state-idle">
      <div class="idle-icon">○</div>
      <div class="idle-text">今天还没有打卡</div>
      <button class="checkin-btn" :disabled="loading" @click="doCheckin">
        {{ loading ? '打卡中…' : '立即打卡' }}
      </button>
    </div>

    <!-- Checked in — show fortune -->
    <div v-else class="state-done">
      <div class="done-badge">
        <span class="done-check">✓</span>
        <span class="done-text">今日已打卡</span>
        <span
          v-if="fortune"
          class="mood-tag"
          :style="{ color: moodStyle(fortune.mood).color, background: moodStyle(fortune.mood).bg }"
        >{{ fortune.mood }}</span>
      </div>

      <div v-if="fortune" class="fortune-body">
        <div class="fortune-row">
          <span class="fortune-label lucky-label">宜</span>
          <span v-for="(item, i) in fortune.lucky" :key="i" class="fortune-item lucky-item">{{ item }}</span>
        </div>
        <div class="fortune-row">
          <span class="fortune-label unlucky-label">忌</span>
          <span v-for="(item, i) in fortune.unlucky" :key="i" class="fortune-item unlucky-item">{{ item }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.checkin-card {
  padding: 16px 20px;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

/* Header */
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.streak-badge {
  font-size: 12px;
  color: var(--home-accent);
  font-weight: 500;
}

/* Idle state */
.state-idle {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 0;
}
.idle-icon {
  font-size: 32px;
  color: var(--text-muted);
  line-height: 1;
}
.idle-text {
  font-size: 13px;
  color: var(--text-muted);
}
.checkin-btn {
  margin-top: 4px;
  padding: 7px 28px;
  background: var(--home-accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s;
}
.checkin-btn:hover:not(:disabled) { opacity: 0.88; }
.checkin-btn:disabled { opacity: 0.55; cursor: not-allowed; }

/* Done state */
.state-done {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.done-badge {
  display: flex;
  align-items: center;
  gap: 6px;
}
.done-check {
  font-size: 14px;
  color: var(--home-ac);
  font-weight: 700;
}
.done-text {
  font-size: 13px;
  color: var(--text-secondary);
}
.mood-tag {
  font-size: 12px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 999px;
}

/* Fortune */
.fortune-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
}
.fortune-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.fortune-label {
  font-size: 12px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 4px;
  flex-shrink: 0;
}
.lucky-label   { color: #16a34a; background: #f0fdf4; }
.unlucky-label { color: #dc2626; background: #fef2f2; }

.fortune-item {
  font-size: 13px;
  font-weight: 500;
}
.lucky-item   { color: var(--text-primary); }
.unlucky-item { color: var(--text-secondary); }
</style>
