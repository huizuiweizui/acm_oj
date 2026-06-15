<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getGradebook, exportGradebook, getStudentResult } from '@/api/exam'

const route = useRoute()
const router = useRouter()
const aid = Number(route.params.aid)

const board = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const exporting = ref(false)

const STATUS = { not_started: '未开始', in_progress: '进行中', submitted: '已交卷', graded: '已批改' }
const STATUS_CLASS = { not_started: 'st-none', in_progress: 'st-doing', submitted: 'st-done', graded: 'st-done' }

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await getGradebook(aid)
    board.value = data
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '加载失败（需教师/管理员权限）'
  } finally {
    loading.value = false
  }
}

async function doExport() {
  exporting.value = true
  try {
    const { data: blob } = await exportGradebook(aid)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gradebook_${aid}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

// 单生作答详情
const detail = ref(null)
const detailLoading = ref(false)
async function viewStudent(row) {
  detail.value = { row }
  detailLoading.value = true
  try {
    const { data } = await getStudentResult(aid, row.user_id)
    detail.value = { ...data, row }
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function fmtTime(dt) {
  return dt ? new Date(dt).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'
}

onMounted(load)
</script>

<template>
  <div class="gradebook">
    <div class="gb-header">
      <button class="btn-back" @click="router.back()">← 返回</button>
      <div class="gb-titles">
        <h1 class="gb-title">{{ board?.assignment?.title || '成绩单' }}</h1>
        <p v-if="board" class="gb-sub">
          满分 {{ board.max_score }} · {{ board.member_count }} 人 · 已交 {{ board.submitted_count }}
        </p>
      </div>
      <div style="display:flex; gap:0.6rem; align-items:center">
        <button class="btn-secondary" @click="router.push(`/teacher/assignments/${aid}/plagiarism`)">🔍 代码查重</button>
        <button class="btn-primary" :disabled="exporting || !board" @click="doExport">
          {{ exporting ? '导出中…' : '↓ 导出 Excel' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="empty-tip">加载中…</div>
    <div v-else-if="errorMsg" class="empty-tip err">{{ errorMsg }}</div>
    <div v-else-if="board" class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>排名</th><th>姓名</th><th>学号</th>
            <th>客观</th><th>编程</th><th>总分</th>
            <th>状态</th><th>切屏</th><th>交卷时间</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in board.rows" :key="r.user_id">
            <td class="rank">{{ i + 1 }}</td>
            <td class="name">{{ r.display_name }}</td>
            <td class="muted">{{ r.student_id || '—' }}</td>
            <td>{{ r.objective_score }}</td>
            <td>{{ r.programming_score }}</td>
            <td class="total">{{ r.total_score }}</td>
            <td><span :class="['st-tag', STATUS_CLASS[r.status]]">{{ STATUS[r.status] }}</span></td>
            <td :class="r.focus_loss_count > 0 ? 'focus-hot' : 'muted'">{{ r.focus_loss_count }}</td>
            <td class="muted">{{ fmtTime(r.submitted_at) }}</td>
            <td><button class="btn-xs" @click="viewStudent(r)">详情</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 单生详情弹窗 -->
    <div v-if="detail" class="modal-overlay" @click.self="detail = null">
      <div class="modal">
        <h2 class="modal-title">{{ detail.row.display_name }} 的作答</h2>
        <div v-if="detailLoading" class="empty-tip">加载中…</div>
        <template v-else-if="detail.total_score !== undefined">
          <div class="d-score">
            {{ detail.total_score }}<span class="d-max"> / {{ detail.max_score }}</span>
            <span class="d-break">（客观 {{ detail.objective_score }} · 编程 {{ detail.programming_score }}）</span>
          </div>

          <div v-if="detail.questions.length" class="d-sec">
            <div class="d-sec-t">客观题</div>
            <div v-for="q in detail.questions" :key="q.id" class="d-row" :class="q.correct ? 'ok' : 'no'">
              <span class="d-mark">{{ q.correct ? '✓' : '✗' }}</span>
              <span class="d-title">{{ q.title }}</span>
              <span class="d-pts">{{ q.got_score }} / {{ q.score }}</span>
            </div>
          </div>

          <div v-if="detail.problems.length" class="d-sec">
            <div class="d-sec-t">编程题</div>
            <div v-for="p in detail.problems" :key="p.id" class="d-row" :class="p.ac ? 'ok' : (p.got_score > 0 ? 'part' : 'no')">
              <span class="d-mark">{{ p.ac ? '✓' : (p.got_score > 0 ? '◐' : '✗') }}</span>
              <span class="d-title">#{{ p.id }} {{ p.title }}</span>
              <span class="d-pts">{{ p.got_score }} / {{ p.score }}<span v-if="!p.ac && p.ratio > 0" class="d-ratio"> ({{ Math.round(p.ratio * 100) }}%)</span></span>
            </div>
          </div>
        </template>
        <div class="modal-actions">
          <button class="btn-secondary" @click="detail = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gradebook { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
.gb-header { display: flex; align-items: center; gap: 1rem; }
.btn-back { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; flex-shrink: 0; }
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.gb-titles { flex: 1; }
.gb-title { font-size: 1.35rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.gb-sub { font-size: 0.85rem; color: var(--text-muted); margin: 0.2rem 0 0; }
.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th { text-align: left; padding: 0.6rem 0.75rem; color: var(--text-muted); font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap; }
.data-table td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); }
.rank { color: var(--text-muted); font-family: monospace; }
.name { color: var(--text-primary); font-weight: 500; }
.total { font-weight: 700; color: var(--accent); }
.muted { color: var(--text-muted); }
.focus-hot { color: #f87171; font-weight: 600; }
.st-tag { font-size: 0.72rem; padding: 0.1rem 0.5rem; border-radius: 10px; white-space: nowrap; }
.st-none { background: rgba(100,100,100,0.1); color: var(--text-muted); border: 1px solid var(--border); }
.st-doing { background: #f59e0b22; color: #f59e0b; }
.st-done { background: #10b98122; color: #10b981; }
.btn-xs { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem; }
.btn-xs:hover { border-color: var(--accent); color: var(--accent); }

.empty-tip { text-align: center; padding: 3rem; color: var(--text-muted); }
.empty-tip.err { color: #f87171; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; width: 480px; max-width: 95vw; max-height: 88vh; overflow-y: auto; display: flex; flex-direction: column; gap: 0.85rem; }
.modal-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.d-score { font-size: 1.6rem; font-weight: 800; color: var(--accent); }
.d-max { font-size: 0.95rem; color: var(--text-muted); font-weight: 500; }
.d-break { font-size: 0.82rem; color: var(--text-secondary); font-weight: 400; margin-left: 0.4rem; }
.d-sec { display: flex; flex-direction: column; gap: 0.35rem; }
.d-sec-t { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }
.d-row { display: flex; align-items: center; gap: 0.6rem; padding: 0.35rem 0.5rem; border-radius: 5px; font-size: 0.85rem; }
.d-row.ok { background: #10b98112; }
.d-row.no { background: #ef444412; }
.d-row.part { background: #f59e0b12; }
.d-mark { width: 1.1rem; text-align: center; font-weight: 700; }
.d-row.ok .d-mark { color: #10b981; }
.d-row.no .d-mark { color: #f87171; }
.d-row.part .d-mark { color: #f59e0b; }
.d-title { flex: 1; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.d-pts { font-family: monospace; color: var(--text-secondary); white-space: nowrap; }
.d-ratio { color: var(--text-muted); }
.modal-actions { display: flex; justify-content: flex-end; }
.btn-secondary { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
</style>
