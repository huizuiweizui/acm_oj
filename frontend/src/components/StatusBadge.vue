<script setup>
defineProps({ status: String })

const cfg = {
  AC:      { icon: '✓', label: 'AC',      bg: 'var(--status-ac-bg)',      color: 'var(--status-ac-text)' },
  WA:      { icon: '✗', label: 'WA',      bg: 'var(--status-wa-bg)',      color: 'var(--status-wa-text)' },
  TLE:     { icon: '⏱', label: 'TLE',     bg: 'var(--status-tle-bg)',     color: 'var(--status-tle-text)' },
  MLE:     { icon: '▤', label: 'MLE',     bg: 'var(--status-mle-bg)',     color: 'var(--status-mle-text)' },
  OLE:     { icon: '⇥', label: 'OLE',     bg: 'var(--status-tle-bg)',     color: 'var(--status-tle-text)' },
  RE:      { icon: '⚠', label: 'RE',      bg: 'var(--status-re-bg)',      color: 'var(--status-re-text)' },
  CE:      { icon: '⚙', label: 'CE',      bg: 'var(--status-ce-bg)',      color: 'var(--status-ce-text)' },
  Pending: { icon: '◌', label: '等待中',  bg: 'var(--status-pending-bg)', color: 'var(--status-pending-text)' },
  Judging: { icon: '◌', label: '评测中',  bg: 'var(--status-pending-bg)', color: 'var(--status-pending-text)' },
  NT:      { icon: '—', label: '无测试点', bg: 'var(--status-nt-bg)',      color: 'var(--status-nt-text)' },
}
</script>

<template>
  <span class="badge" :style="{ background: cfg[status]?.bg ?? 'var(--status-nt-bg)', color: cfg[status]?.color ?? 'var(--text-muted)' }">
    <span class="badge-icon" :class="{ spin: status === 'Judging' }">{{ cfg[status]?.icon ?? '—' }}</span>
    {{ cfg[status]?.label ?? status }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
  font-family: var(--font-mono);
}
.badge-icon { font-style: normal; }
.spin { display: inline-block; animation: judging-spin 1.2s linear infinite; }
@keyframes judging-spin { to { transform: rotate(360deg); } }
</style>
