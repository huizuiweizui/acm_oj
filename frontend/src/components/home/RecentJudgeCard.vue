<script setup>
/**
 * @typedef {Object} RecentSubmission
 * @property {number|string} id
 * @property {number|string} problemId
 * @property {string} problemTitle
 * @property {string} status        — 'AC' | 'WA' | 'TLE' | 'MLE' | 'RE' | 'CE'
 * @property {number|null} time     — ms
 * @property {number|null} memory   — KB
 * @property {string} language
 * @property {string} submittedAt   — ISO 8601
 */

defineProps({
  /** @type {RecentSubmission[]} */
  submissions: { type: Array, default: () => [] }
})

// Maps status string → CSS variable names (no inline colour objects to maintain dark-mode compat)
const STATUS_CLASS = {
  AC:  'st-ac',
  WA:  'st-wa',
  TLE: 'st-tle',
  MLE: 'st-tle',
  RE:  'st-re',
  CE:  'st-ce',
}
function statusClass(s) {
  return STATUS_CLASS[s] ?? 'st-ce'
}

function formatTime(ms) {
  return ms == null ? '-' : `${ms} ms`
}

function timeAgo(iso) {
  if (!iso) return ''
  const m = Math.floor((Date.now() - new Date(iso)) / 60000)
  if (m < 1)  return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
}
</script>

<template>
  <div class="judge-card card">
    <div class="card-head">
      <span class="card-title">最近评测</span>
    </div>

    <div v-if="submissions.length" class="list">
      <div v-for="s in submissions" :key="s.id" class="sub-row">
        <div class="sub-left">
          <span class="status-tag" :class="statusClass(s.status)">{{ s.status }}</span>
          <span class="sub-title">{{ s.problemTitle }}</span>
        </div>
        <div class="sub-right">
          <span class="mono">{{ formatTime(s.time) }}</span>
          <span class="mono lang">{{ s.language }}</span>
          <span class="ago">{{ timeAgo(s.submittedAt) }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty">暂无提交记录</div>
  </div>
</template>

<style scoped>
.judge-card {
  padding: 16px 20px;
  height: 100%;
  box-sizing: border-box;
}
.card-head {
  margin-bottom: 12px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.list {
  display: flex;
  flex-direction: column;
}
.sub-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}
.sub-row:last-child {
  border-bottom: none;
}

.sub-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.status-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}
/* semantic colours via CSS variables — dark mode handled in main.css */
.st-ac  { background: var(--home-ac-bg);         color: var(--home-ac); }
.st-wa  { background: var(--home-wa-bg);         color: var(--home-wa); }
.st-tle { background: var(--home-tle-bg);        color: var(--home-tle); }
.st-re  { background: var(--status-re-bg);       color: var(--status-re-text); }
.st-ce  { background: var(--status-ce-bg);       color: var(--status-ce-text); }

.sub-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sub-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.mono {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.lang {
  color: var(--text-secondary);
}
.ago {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 28px 0;
  text-align: center;
}
</style>
