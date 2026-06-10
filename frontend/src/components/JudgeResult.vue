<script setup>
import { ref, watch, computed } from 'vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  submission: { type: Object, default: null },
  polling:    { type: Boolean, default: false },
})

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

const isAC = computed(() => !props.polling && props.submission?.status === 'AC')

const STATUS_COLOR = {
  AC:  'tc-ac',
  WA:  'tc-wa',
  TLE: 'tc-tle',
  MLE: 'tc-tle',
  RE:  'tc-wa',
  CE:  'tc-ce',
}
function tcClass(s) { return STATUS_COLOR[s] ?? 'tc-muted' }
</script>

<template>
  <div class="judge-result" v-if="submission">
    <div v-if="polling" class="judging">
      <span class="spinner"></span> 评测中...
    </div>

    <template v-else>
      <div :class="['result-row', isAC && 'ac-flash']">
        <StatusBadge :status="submission.status" />
        <span v-if="submission.time_used != null" class="stat">{{ submission.time_used }} ms</span>
        <span v-if="submission.memory_used != null" class="stat">
          {{ (submission.memory_used / 1024).toFixed(1) }} MB
        </span>
        <span class="sub-id">
          <a :href="`/submissions`" target="_blank" class="sub-link">#{{ submission.id }}</a>
        </span>
      </div>

      <pre v-if="submission.error_info" class="error-block">{{ submission.error_info }}</pre>

      <!-- Test point table -->
      <div v-if="submission.test_results?.length" class="test-wrap">
        <div class="test-label">测试点详情</div>
        <table class="test-table">
          <thead>
            <tr>
              <th class="th-num">#</th>
              <th>状态</th>
              <th class="th-num">耗时</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tc in submission.test_results" :key="tc.idx">
              <td class="mono">{{ tc.idx }}</td>
              <td><span :class="['tc-badge', tcClass(tc.status)]">{{ tc.status }}</span></td>
              <td class="mono">{{ tc.time_ms }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>

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

.judging { display: flex; align-items: center; gap: 0.5rem; color: var(--accent); font-size: 0.9rem; }
.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid var(--accent); border-top-color: transparent;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.result-row {
  display: flex; align-items: center; gap: 1rem; margin-bottom: 0.6rem;
  border-radius: 6px; padding: 0.3rem 0;
}
.stat { font-size: 0.82rem; color: var(--text-muted); font-family: var(--font-mono); }
.sub-id { margin-left: auto; }
.sub-link { font-size: 0.78rem; color: var(--text-muted); text-decoration: none; }
.sub-link:hover { color: var(--accent); }

@keyframes ac-flash {
  0%   { background: transparent; }
  40%  { background: rgba(16,185,129,0.1); }
  100% { background: transparent; }
}
.ac-flash { animation: ac-flash 0.2s ease-out; }

.error-block {
  background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.2);
  border-radius: 6px; padding: 0.75rem;
  font-size: 0.8rem; color: var(--status-wa-text);
  white-space: pre-wrap; word-break: break-all;
  max-height: 160px; overflow-y: auto; margin: 0.5rem 0 0;
  font-family: var(--font-mono);
}

.test-wrap { margin-top: 0.75rem; }
.test-label { font-size: 0.78rem; color: var(--text-muted); font-weight: 500; margin-bottom: 0.4rem; }
.test-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.test-table th {
  text-align: left; padding: 0.3rem 0.5rem; font-size: 0.72rem; font-weight: 500;
  color: var(--text-muted); border-bottom: 1px solid var(--border);
  background: var(--bg-page); position: sticky; top: 0;
}
.th-num { text-align: right; }
.test-table td { padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--border); }
.test-table tr:last-child td { border-bottom: none; }
.mono { text-align: right; font-family: var(--font-mono); }

.tc-badge { font-size: 0.72rem; font-weight: 600; padding: 0.1rem 0.35rem; border-radius: 3px; }
.tc-ac  { color: #10b981; background: rgba(16,185,129,0.1); }
.tc-wa  { color: var(--status-wa-text); background: rgba(239,68,68,0.08); }
.tc-tle { color: #f59e0b; background: rgba(245,158,11,0.1); }
.tc-ce  { color: var(--text-muted); background: var(--bg-secondary); }
.tc-muted { color: var(--text-muted); background: var(--bg-secondary); }

.ai-block {
  margin-top: 0.8rem;
  background: rgba(59,130,246,0.05);
  border: 1px solid rgba(59,130,246,0.15);
  border-radius: 6px; padding: 0.75rem;
}
.ai-label { font-size: 0.78rem; color: #3b82f6; font-weight: 600; margin-bottom: 0.4rem; }
.ai-text { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.7; white-space: pre-wrap; }
</style>
