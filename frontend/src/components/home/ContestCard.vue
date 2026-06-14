<script setup>
import { useRouter } from 'vue-router'

/**
 * @typedef {Object} ContestItem
 * @property {number|string} id
 * @property {string} title
 * @property {string} startTime  — ISO 8601
 * @property {string} endTime    — ISO 8601
 * @property {string} mode       — 'ICPC' | 'IOI' | 'OI'
 */

defineProps({
  /** @type {ContestItem[]} */
  contests: { type: Array, default: () => [] }
})

const router = useRouter()

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const mo = d.getMonth() + 1
  const da = d.getDate()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${mo}/${da} ${hh}:${mm}`
}

function contestStatus(c) {
  const now = Date.now()
  const s = new Date(c.startTime).getTime()
  const e = new Date(c.endTime).getTime()
  if (now < s) return { label: '未开始', cls: 'cs-upcoming' }
  if (now > e) return { label: '已结束', cls: 'cs-ended' }
  return { label: '进行中', cls: 'cs-running' }
}
</script>

<template>
  <div class="contest-card card">
    <div class="card-head">
      <span class="card-title">近期比赛</span>
      <router-link :to="{ name: 'contest-list' }" class="view-all">全部 →</router-link>
    </div>

    <div v-if="contests.length" class="list">
      <div
        v-for="c in contests"
        :key="c.id"
        class="contest-row"
        @click="router.push({ name: 'contest-detail', params: { id: c.id } })"
      >
        <div class="contest-name">{{ c.title }}</div>
        <div class="contest-meta">
          <span class="mono time">{{ fmtDate(c.startTime) }}</span>
          <span class="mode-tag">{{ c.mode }}</span>
          <span class="cs-tag" :class="contestStatus(c).cls">{{ contestStatus(c).label }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty">暂无近期比赛</div>
  </div>
</template>

<style scoped>
.contest-card {
  padding: 16px 20px;
  height: 100%;
  box-sizing: border-box;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
.view-all {
  font-size: 12px;
  color: var(--home-accent);
  text-decoration: none;
}
.view-all:hover {
  text-decoration: underline;
}

.list {
  display: flex;
  flex-direction: column;
}
.contest-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}
.contest-row:last-child {
  border-bottom: none;
}
.contest-row:hover .contest-name {
  color: var(--home-accent);
}

.contest-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 5px;
  transition: color 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.contest-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.mono.time {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.mode-tag {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 4px;
}
.cs-tag {
  font-size: 11px;
  font-weight: 500;
}
.cs-upcoming { color: var(--text-muted); }
.cs-running  { color: var(--home-ac); }
.cs-ended    { color: #dc2626; }

.empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 28px 0;
  text-align: center;
}
</style>
