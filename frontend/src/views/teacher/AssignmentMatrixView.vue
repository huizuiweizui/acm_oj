<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAssignmentMatrix, exportAssignmentMatrix, saveBlobResponse } from '@/api/team'
import { diffColor } from '@/utils/difficulty'

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)
const aid = Number(route.params.aid)

const loading = ref(true)
const data = ref(null)
const apiError = ref('')
const exporting = ref(false)

onMounted(async () => {
  try {
    const { data: d } = await getAssignmentMatrix(teamId, aid)
    data.value = d
  } catch (e) {
    const s = e.response?.status
    apiError.value = s === 403 ? '无权限查看完成情况（仅团队创建者、队长和管理员可访问）'
      : s === 404 ? '作业不存在' : '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
})

const asgn = computed(() => data.value?.assignment ?? {})
const columns = computed(() => data.value?.columns ?? [])
const rows = computed(() => data.value?.rows ?? [])
const memberCount = computed(() => rows.value.length)
const fullDone = computed(() => rows.value.filter(r => columns.value.length && r.done === columns.value.length).length)

const CELL = {
  ontime: { icon: '✅', cls: 'c-ontime', tip: '按时完成' },
  late: { icon: '🕐', cls: 'c-late', tip: '补交完成' },
  tried: { icon: '❌', cls: 'c-tried', tip: '尝试未通过' },
  none: { icon: '·', cls: 'c-none', tip: '未提交' },
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '不限'
}

function openCell(row, col) {
  router.push({ path: '/submissions', query: { user_id: row.user_id, problem_id: col.id } })
}

async function doExport() {
  exporting.value = true
  try {
    const resp = await exportAssignmentMatrix(teamId, aid)
    saveBlobResponse(resp, `${asgn.value.title}_完成情况.xlsx`)
  } catch {
    alert('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="matrix-page" v-if="!loading && data">
    <div class="mx-head">
      <button class="btn-back" @click="router.push(`/teacher/teams/${teamId}`)">← {{ data.team.name }}</button>
      <div class="head-info">
        <h1 class="mx-title">
          {{ asgn.title }}
          <span v-if="!asgn.is_active" class="draft">草稿</span>
        </h1>
        <p class="mx-sub">
          开始 {{ fmt(asgn.start_at) }} · 截止 {{ fmt(asgn.deadline) }} · {{ columns.length }} 道题
          <span v-if="!data.can_manage"> · 只读（队长）</span>
        </p>
      </div>
      <button class="btn-export" :disabled="exporting" @click="doExport">
        {{ exporting ? '导出中…' : '↓ 导出 Excel' }}
      </button>
    </div>

    <p v-if="asgn.description" class="mx-desc">{{ asgn.description }}</p>

    <div class="summary">
      <span>成员 <b>{{ memberCount }}</b></span>
      <span>全部完成 <b class="ok">{{ fullDone }}</b></span>
      <span class="legend">
        <span v-for="(c, k) in CELL" :key="k" class="legend-item"><span :class="['cell-dot', c.cls]">{{ c.icon }}</span>{{ c.tip }}</span>
      </span>
    </div>

    <div v-if="columns.length === 0" class="empty-tip">该作业还没有题目</div>
    <div v-else class="table-wrap">
      <table class="mx-table">
        <thead>
          <tr>
            <th class="sticky-col">成员</th>
            <th class="col-num">完成</th>
            <th
              v-for="(c, i) in columns" :key="c.id"
              class="col-prob" :title="`#${c.id} ${c.title}（${c.difficulty}）`"
            >
              <RouterLink :to="`/problems/${c.id}`" class="prob-head">
                <span class="prob-label" :style="{ borderColor: diffColor(c.difficulty) }">{{ String.fromCharCode(65 + (i % 26)) }}</span>
                <span class="prob-name">{{ c.title }}</span>
              </RouterLink>
              <span class="prob-done">{{ c.done_count }}/{{ memberCount }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.user_id">
            <td class="sticky-col">
              <span class="m-name">{{ r.display_name }}</span>
              <span v-if="r.role === 'captain'" class="crown">👑</span>
              <span v-if="r.student_id" class="m-sid">{{ r.student_id }}</span>
            </td>
            <td class="col-num">
              <b>{{ r.done }}</b><span class="text-muted">/{{ columns.length }}</span>
              <span v-if="r.late" class="late-tag">补{{ r.late }}</span>
            </td>
            <td
              v-for="(cell, i) in r.cells" :key="i"
              :class="['cell', CELL[cell.state].cls]"
              :title="`${CELL[cell.state].tip}${cell.attempts ? `（${cell.attempts} 次提交）` : ''}`"
              @click="cell.attempts && openCell(r, columns[i])"
            >
              <span>{{ CELL[cell.state].icon }}</span>
              <span v-if="cell.state === 'tried'" class="attempts">{{ cell.attempts }}</span>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td :colspan="2 + columns.length" class="empty-tip">团队暂无成员</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>
  <div v-else class="loading-tip error-tip">
    {{ apiError }}
    <button class="btn-back" @click="router.back()">← 返回</button>
  </div>
</template>

<style scoped>
.matrix-page { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 1rem; }
.mx-head { display: flex; align-items: center; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; flex-shrink: 0;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.head-info { flex: 1; min-width: 0; }
.mx-title { font-size: 1.35rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.15rem; display: flex; align-items: center; gap: 0.5rem; }
.mx-sub { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
.draft { font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 4px; background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; font-weight: 500; }
.btn-export {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; flex-shrink: 0;
}
.btn-export:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn-export:disabled { opacity: 0.4; cursor: default; }
.mx-desc { margin: 0; font-size: 0.875rem; color: var(--text-secondary); white-space: pre-wrap; }

.summary { display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-secondary); }
.summary b { color: var(--text-primary); }
.summary b.ok { color: var(--status-ac-text); }
.legend { margin-left: auto; display: flex; gap: 0.9rem; flex-wrap: wrap; }
.legend-item { display: inline-flex; align-items: center; gap: 0.3rem; color: var(--text-muted); font-size: 0.78rem; }
.cell-dot { display: inline-flex; width: 1.4rem; height: 1.4rem; align-items: center; justify-content: center; border-radius: 4px; font-size: 0.75rem; }

.table-wrap { overflow-x: auto; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; }
.mx-table { border-collapse: separate; border-spacing: 0; font-size: 0.85rem; min-width: 100%; }
.mx-table th, .mx-table td { border-bottom: 1px solid var(--border); padding: 0.45rem 0.6rem; }
.mx-table tr:last-child td { border-bottom: none; }
.mx-table th { color: var(--text-muted); font-weight: 500; vertical-align: bottom; background: var(--bg-card); }
.sticky-col { position: sticky; left: 0; background: var(--bg-card); z-index: 1; min-width: 140px; text-align: left; }
.col-num { text-align: right; white-space: nowrap; }
.col-prob { min-width: 64px; max-width: 110px; text-align: center; }
.prob-head { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; text-decoration: none; color: var(--text-secondary); }
.prob-head:hover { color: var(--accent-text); }
.prob-label {
  font-family: var(--font-mono); font-weight: 700; color: var(--text-primary);
  border-bottom: 2px solid; padding: 0 0.2rem;
}
.prob-name { font-size: 0.72rem; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prob-done { display: block; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.15rem; font-family: var(--font-mono); }

.m-name { color: var(--text-primary); font-weight: 500; }
.crown { margin-left: 0.2rem; font-size: 0.8rem; }
.m-sid { display: block; font-size: 0.72rem; color: var(--text-muted); }
.late-tag { margin-left: 0.3rem; font-size: 0.7rem; color: var(--status-tle-text); background: var(--status-tle-bg); padding: 0 0.3rem; border-radius: 3px; }
.text-muted { color: var(--text-muted); }

.cell { text-align: center; position: relative; }
.cell.c-ontime, .cell.c-late, .cell.c-tried { cursor: pointer; }
.cell:hover { filter: brightness(0.96); }
.c-ontime { background: var(--status-ac-bg); }
.c-late { background: var(--status-tle-bg); }
.c-tried { background: var(--status-wa-bg); }
.c-none { color: var(--text-muted); }
.attempts { position: absolute; right: 4px; bottom: 2px; font-size: 0.65rem; color: var(--status-wa-text); font-family: var(--font-mono); }

.empty-tip, .loading-tip { text-align: center; padding: 3rem 2rem; color: var(--text-muted); }
.error-tip { color: #f87171; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
</style>
