<script setup>
import { ref, watch } from 'vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  submission: { type: Object, default: null },
  polling: { type: Boolean, default: false },
})

// AI 反馈逐字显示
const displayedAI = ref('')
let aiTimer = null

watch(() => props.submission?.ai_feedback, (text) => {
  if (!text) { displayedAI.value = ''; return }
  displayedAI.value = ''
  clearInterval(aiTimer)
  let i = 0
  aiTimer = setInterval(() => {
    displayedAI.value += text[i++]
    if (i >= text.length) clearInterval(aiTimer)
  }, 18)
})
</script>

<template>
  <div class="judge-result" v-if="submission">
    <!-- 评测中动画 -->
    <div v-if="polling" class="judging">
      <span class="spinner"></span> 评测中...
    </div>

    <!-- 最终结果 -->
    <template v-else>
      <div class="result-row">
        <StatusBadge :status="submission.status" />
        <span v-if="submission.time_used != null" class="stat">
          🕐 {{ submission.time_used }} ms
        </span>
        <span v-if="submission.memory_used != null" class="stat">
          💾 {{ (submission.memory_used / 1024).toFixed(1) }} MB
        </span>
      </div>

      <!-- 编译错误 / 运行错误 -->
      <pre v-if="submission.error_info" class="error-block">{{ submission.error_info }}</pre>

      <!-- AI 反馈 -->
      <div v-if="displayedAI || submission.ai_feedback" class="ai-block">
        <div class="ai-label">🤖 AI 反馈</div>
        <div class="ai-text">{{ displayedAI }}</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.judge-result {
  padding: 0.9rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.judging {
  display: flex; align-items: center; gap: 0.5rem;
  color: #3b82f6; font-size: 0.9rem;
}
.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid #3b82f6; border-top-color: transparent;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.result-row { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.6rem; }
.stat { font-size: 0.82rem; color: var(--text-muted); }

.error-block {
  background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.3);
  border-radius: 6px; padding: 0.75rem;
  font-size: 0.8rem; color: #ff9090;
  white-space: pre-wrap; word-break: break-all;
  max-height: 160px; overflow-y: auto;
  margin: 0.5rem 0 0;
}

.ai-block {
  margin-top: 0.8rem;
  background: rgba(59,130,246,0.06);
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 6px; padding: 0.75rem;
}
.ai-label { font-size: 0.78rem; color: #3b82f6; font-weight: 600; margin-bottom: 0.4rem; }
.ai-text { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.7; white-space: pre-wrap; }
</style>
