<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProblemList, updateProblemList, deleteProblemList } from '@/api/lists'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

const list = ref(null)
const loading = ref(true)
const errorMsg = ref('')

const progress = computed(() =>
  list.value && list.value.problem_count
    ? Math.round(list.value.solved_count / list.value.problem_count * 100) : 0)

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await getProblemList(id)
    list.value = data
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

// 编辑
const modal = ref(false)
const form = ref({ title: '', description: '', is_public: true, problems: [] })
const probSearch = ref('')
const probResults = ref([])
const searching = ref(false)
const saving = ref(false)

function openEdit() {
  form.value = {
    title: list.value.title,
    description: list.value.description,
    is_public: list.value.is_public,
    problems: list.value.items.map(it => ({ id: it.problem_id, title: it.title, difficulty: it.difficulty })),
  }
  probResults.value = []
  probSearch.value = ''
  modal.value = true
}
async function searchProb() {
  if (!probSearch.value.trim()) return
  searching.value = true
  try {
    const { default: api } = await import('@/api/index')
    const { data } = await api.get('/problems/', { params: { search: probSearch.value, limit: 10, is_published: true } })
    const ids = new Set(form.value.problems.map(p => p.id))
    probResults.value = (data.results || data).filter(p => !ids.has(p.id)).slice(0, 8)
  } finally {
    searching.value = false
  }
}
function addProb(p) {
  if (!form.value.problems.some(x => x.id === p.id)) {
    form.value.problems.push({ id: p.id, title: p.title, difficulty: p.difficulty })
  }
  probResults.value = probResults.value.filter(x => x.id !== p.id)
}
function removeProb(pid) { form.value.problems = form.value.problems.filter(p => p.id !== pid) }
async function save() {
  if (!form.value.title.trim()) return
  saving.value = true
  try {
    await updateProblemList(id, {
      title: form.value.title.trim(),
      description: form.value.description,
      is_public: form.value.is_public,
      problem_ids: form.value.problems.map(p => p.id),
    })
    modal.value = false
    load()
  } finally {
    saving.value = false
  }
}
async function doDelete() {
  if (!confirm(`删除题单「${list.value.title}」？`)) return
  await deleteProblemList(id)
  router.push('/problem-lists')
}

const DIFF_COLORS = {
  '暂无评定': '#bfbfbf', '入门': '#fe4c61', '普及-': '#f39c11', '普及/提高-': '#ffc116',
  '普及+/提高': '#52c41a', '提高+/省选-': '#3498db', '省选/NOI-': '#9d3dcf', 'NOI/NOI+/CTSC': '#0e1d69',
}
function diffColor(d) { return DIFF_COLORS[d] ?? '#6b7280' }

onMounted(load)
</script>

<template>
  <div class="pld" v-if="list">
    <div class="pld-header">
      <button class="btn-back" @click="router.push('/problem-lists')">← 题单</button>
      <div class="pld-titles">
        <h1 class="pld-title">
          {{ list.title }}
          <span :class="['vis-tag', list.is_public ? 'vis-pub' : 'vis-pri']">{{ list.is_public ? '公开' : '私有' }}</span>
        </h1>
        <p v-if="list.description" class="pld-desc">{{ list.description }}</p>
      </div>
      <div v-if="list.can_manage" class="pld-actions">
        <button class="btn-sm" @click="openEdit">编辑</button>
        <button class="btn-sm btn-danger" @click="doDelete">删除</button>
      </div>
    </div>

    <div class="prog-card">
      <div class="prog-num">{{ list.solved_count }} / {{ list.problem_count }}</div>
      <div class="prog-bar"><div class="prog-fill" :style="{ width: progress + '%' }"></div></div>
      <div class="prog-pct">{{ progress }}%</div>
    </div>

    <div v-if="list.items.length === 0" class="empty-tip">题单还没有题目{{ list.can_manage ? '，点「编辑」添加' : '' }}</div>
    <div v-else class="item-list">
      <a v-for="(it, i) in list.items" :key="it.problem_id"
         class="item-row" :class="{ done: it.ac }" :href="`/problems/${it.problem_id}`" target="_blank">
        <span class="item-idx">{{ i + 1 }}</span>
        <span class="item-check">{{ it.ac ? '✓' : '○' }}</span>
        <span class="item-title">#{{ it.problem_id }} {{ it.title }}</span>
        <span v-if="it.note" class="item-note">{{ it.note }}</span>
        <span class="item-diff" :style="{ color: diffColor(it.difficulty) }">{{ it.difficulty }}</span>
      </a>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="modal" class="modal-overlay" @click.self="modal = false">
      <div class="modal modal-wide">
        <h2 class="modal-title">编辑题单</h2>
        <input v-model="form.title" class="form-input" placeholder="题单标题" maxlength="200" />
        <textarea v-model="form.description" class="form-textarea" placeholder="简介（可选）" rows="2" />
        <label class="check-label"><input type="checkbox" v-model="form.is_public" /> 公开</label>

        <div class="pick-section">
          <div class="pick-head">题目（{{ form.problems.length }}）</div>
          <div class="search-row">
            <input v-model="probSearch" class="form-input" placeholder="搜索题目标题或 ID…" @keyup.enter="searchProb" />
            <button class="btn-primary srch-btn" :disabled="searching" @click="searchProb">{{ searching ? '…' : '搜索' }}</button>
          </div>
          <div v-if="probResults.length" class="result-list">
            <div v-for="p in probResults" :key="p.id" class="result-row">
              <span class="rr-name">#{{ p.id }} {{ p.title }}</span>
              <button class="btn-xs btn-success" @click="addProb(p)">添加</button>
            </div>
          </div>
          <div v-for="p in form.problems" :key="p.id" class="picked-row">
            <span class="pk-id">#{{ p.id }}</span>
            <span class="pk-title">{{ p.title }}</span>
            <button class="btn-xs btn-danger" @click="removeProb(p.id)">✕</button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-secondary" @click="modal = false">取消</button>
          <button class="btn-primary" :disabled="saving || !form.title.trim()" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="loading" class="empty-tip">加载中…</div>
  <div v-else class="empty-tip err">{{ errorMsg }}</div>
</template>

<style scoped>
.pld { max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
.pld-header { display: flex; align-items: flex-start; gap: 1rem; }
.btn-back { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; flex-shrink: 0; }
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.pld-titles { flex: 1; }
.pld-title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0; display: flex; align-items: center; gap: 0.6rem; }
.pld-desc { color: var(--text-muted); font-size: 0.875rem; margin: 0.25rem 0 0; }
.pld-actions { display: flex; gap: 0.4rem; flex-shrink: 0; }
.vis-tag { font-size: 0.7rem; padding: 0.1rem 0.45rem; border-radius: 4px; }
.vis-pub { background: #10b98122; color: #10b981; }
.vis-pri { background: rgba(100,100,100,0.12); color: var(--text-muted); border: 1px solid var(--border); }

.prog-card { display: flex; align-items: center; gap: 1rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.25rem; }
.prog-num { font-family: monospace; font-weight: 700; color: var(--text-primary); }
.prog-bar { flex: 1; height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden; }
.prog-fill { height: 100%; background: #10b981; border-radius: 4px; transition: width 0.3s; }
.prog-pct { font-family: monospace; color: #10b981; font-weight: 700; }

.item-list { display: flex; flex-direction: column; gap: 0.4rem; }
.item-row { display: flex; align-items: center; gap: 0.7rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 0.9rem; text-decoration: none; transition: border-color 0.15s; }
.item-row:hover { border-color: var(--accent); }
.item-idx { width: 1.6rem; color: var(--text-muted); font-family: monospace; font-size: 0.8rem; text-align: center; }
.item-check { width: 1.2rem; text-align: center; color: var(--text-muted); }
.item-row.done .item-check { color: #10b981; }
.item-title { flex: 1; color: var(--text-primary); font-size: 0.9rem; }
.item-row.done .item-title { color: var(--text-secondary); }
.item-note { font-size: 0.78rem; color: var(--text-muted); }
.item-diff { font-size: 0.78rem; white-space: nowrap; }

.empty-tip { text-align: center; padding: 3rem; color: var(--text-muted); }
.empty-tip.err { color: #f87171; }

/* 按钮 */
.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
.btn-sm { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.3rem 0.7rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-sm:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm.btn-danger { border-color: #f8717144; color: #f87171; }
.btn-xs { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem; }
.btn-xs.btn-danger { border-color: #f8717144; color: #f87171; }
.btn-xs.btn-success { border-color: #10b98144; color: #10b981; }
.srch-btn { white-space: nowrap; }

/* 弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.75rem; width: 520px; max-width: 95vw; max-height: 90vh; overflow-y: auto; display: flex; flex-direction: column; gap: 0.85rem; }
.modal-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.form-input, .form-textarea { background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.9rem; width: 100%; box-sizing: border-box; }
.form-input:focus, .form-textarea:focus { outline: none; border-color: var(--accent); }
.form-textarea { resize: vertical; font-family: inherit; }
.check-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-secondary); cursor: pointer; }
.pick-section { display: flex; flex-direction: column; gap: 0.5rem; border-top: 1px solid var(--border); padding-top: 0.75rem; }
.pick-head { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); }
.search-row { display: flex; gap: 0.5rem; }
.result-list { display: flex; flex-direction: column; gap: 0.4rem; }
.result-row { display: flex; align-items: center; justify-content: space-between; padding: 0.4rem 0.6rem; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 6px; }
.rr-name { font-size: 0.85rem; color: var(--text-primary); }
.picked-row { display: flex; align-items: center; gap: 0.5rem; }
.pk-id { color: var(--text-muted); font-family: monospace; font-size: 0.82rem; }
.pk-title { flex: 1; font-size: 0.85rem; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
</style>
