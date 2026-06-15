<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  getQuestions, getQuestion, createQuestion, updateQuestion, deleteQuestion,
} from '@/api/questions'

const router = useRouter()

const QTYPES = [
  { value: 'single', label: '单选题' },
  { value: 'multiple', label: '多选题' },
  { value: 'judge', label: '判断题' },
  { value: 'fill', label: '填空题' },
]
const QTYPE_LABEL = Object.fromEntries(QTYPES.map(t => [t.value, t.label]))
const DIFFICULTIES = [
  '暂无评定', '入门', '普及-', '普及/提高-', '普及+/提高',
  '提高+/省选-', '省选/NOI-', 'NOI/NOI+/CTSC',
]
const LETTERS = 'ABCDEFGHIJKLMN'

// ── 列表 ──────────────────────────────────────────────────────────────
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filterType = ref('')
const filterPub = ref('')
const searchQ = ref('')
const loading = ref(false)
const msgBox = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function flash(m) { msgBox.value = m; setTimeout(() => { msgBox.value = '' }, 2500) }

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filterType.value) params.qtype = filterType.value
    if (filterPub.value) params.is_published = filterPub.value
    if (searchQ.value.trim()) params.q = searchQ.value.trim()
    const { data } = await getQuestions(params)
    list.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function go(p) { if (p < 1 || p > totalPages.value) return; page.value = p; load() }
function doSearch() { page.value = 1; load() }
watch([filterType, filterPub], () => { page.value = 1; load() })

// ── 弹窗表单 ──────────────────────────────────────────────────────────
const modal = ref(false)
const editId = ref(null)
const saving = ref(false)
const formErr = ref('')

const blankForm = () => ({
  qtype: 'single',
  title: '',
  content: '',
  options: ['', ''],     // 仅文本，key 按位置 A/B/C 推导
  correctIdx: 0,         // 单选：正确选项下标
  correctSet: [],        // 多选：正确选项下标集合
  judgeAnswer: 'T',      // 判断题
  blanks: [''],          // 填空：每空可接受答案（逗号分隔）
  blank_ignore_case: true,
  score: 5,
  difficulty: '暂无评定',
  explanation: '',
  is_published: false,
})
const form = ref(blankForm())

function openCreate() {
  editId.value = null
  form.value = blankForm()
  formErr.value = ''
  modal.value = true
}

async function openEdit(q) {
  formErr.value = ''
  const { data } = await getQuestion(q.id)
  const f = blankForm()
  f.qtype = data.qtype
  f.title = data.title
  f.content = data.content || ''
  f.score = data.score
  f.difficulty = data.difficulty
  f.explanation = data.explanation || ''
  f.is_published = data.is_published
  f.blank_ignore_case = data.blank_ignore_case
  if (data.qtype === 'single' || data.qtype === 'multiple') {
    const opts = (data.options && data.options.length) ? data.options : [{ key: 'A', text: '' }, { key: 'B', text: '' }]
    f.options = opts.map(o => o.text)
    const ans = (data.answer || []).map(a => String(a).toUpperCase())
    const idxs = opts.map((o, i) => i).filter(i => ans.includes(String(opts[i].key).toUpperCase()))
    f.correctIdx = idxs[0] ?? 0
    f.correctSet = idxs
  } else if (data.qtype === 'judge') {
    f.judgeAnswer = (data.answer && data.answer[0]) ? String(data.answer[0]).toUpperCase() : 'T'
  } else if (data.qtype === 'fill') {
    f.blanks = (data.answer || []).map(b => Array.isArray(b) ? b.join('，') : String(b))
    if (!f.blanks.length) f.blanks = ['']
  }
  form.value = f
  editId.value = q.id
  modal.value = true
}

// 选项操作（按下标，key 在保存时按位置推导）
function addOption() {
  if (form.value.options.length >= LETTERS.length) return
  form.value.options.push('')
}
function removeOption(i) {
  if (form.value.options.length <= 2) return
  form.value.options.splice(i, 1)
  if (form.value.correctIdx === i) form.value.correctIdx = 0
  else if (form.value.correctIdx > i) form.value.correctIdx--
  form.value.correctSet = form.value.correctSet.filter(x => x !== i).map(x => (x > i ? x - 1 : x))
}
function toggleCorrect(i) {
  const s = new Set(form.value.correctSet)
  s.has(i) ? s.delete(i) : s.add(i)
  form.value.correctSet = [...s]
}

function addBlank() { form.value.blanks.push('') }
function removeBlank(i) { if (form.value.blanks.length > 1) form.value.blanks.splice(i, 1) }

function parseBlank(s) {
  return s.split(/[,，]/).map(x => x.trim()).filter(Boolean)
}

function validate() {
  const f = form.value
  if (!f.title.trim()) return '题干不能为空'
  if (f.qtype === 'single' || f.qtype === 'multiple') {
    if (f.options.length < 2) return '至少需要 2 个选项'
    if (f.options.some(t => !t.trim())) return '选项内容不能为空'
    if (f.qtype === 'multiple' && f.correctSet.length === 0) return '请至少勾选一个正确选项'
  }
  if (f.qtype === 'fill') {
    if (f.blanks.some(s => parseBlank(s).length === 0)) return '每个空至少填一个可接受答案'
  }
  return ''
}

function buildPayload() {
  const f = form.value
  const base = {
    qtype: f.qtype,
    title: f.title.trim(),
    content: f.content,
    score: Number(f.score) || 0,
    difficulty: f.difficulty,
    explanation: f.explanation,
    is_published: f.is_published,
  }
  if (f.qtype === 'single' || f.qtype === 'multiple') {
    base.options = f.options.map((t, i) => ({ key: LETTERS[i], text: t.trim() }))
    base.answer = f.qtype === 'single'
      ? [LETTERS[f.correctIdx]]
      : [...f.correctSet].sort((a, b) => a - b).map(i => LETTERS[i])
  } else if (f.qtype === 'judge') {
    base.answer = [f.judgeAnswer]
  } else {
    base.answer = f.blanks.map(parseBlank)
    base.blank_ignore_case = f.blank_ignore_case
  }
  return base
}

async function save() {
  const err = validate()
  if (err) { formErr.value = err; return }
  saving.value = true
  try {
    const payload = buildPayload()
    if (editId.value) {
      await updateQuestion(editId.value, payload)
      flash('题目已更新')
    } else {
      await createQuestion(payload)
      flash('题目已创建')
    }
    modal.value = false
    load()
  } catch (e) {
    formErr.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove(q) {
  if (!confirm(`删除题目「${q.title}」？`)) return
  await deleteQuestion(q.id)
  flash('已删除')
  if (list.value.length === 1 && page.value > 1) page.value--
  load()
}

onMounted(load)
</script>

<template>
  <div class="qbank">
    <div class="page-header">
      <div class="ph-left">
        <button class="btn-back" @click="router.push('/teacher')">← 返回</button>
        <div>
          <h1 class="page-title">客观题题库</h1>
          <p class="page-sub">单选 / 多选 / 判断 / 填空，用于作业与考试</p>
        </div>
      </div>
      <button class="btn-primary" @click="openCreate">＋ 新建题目</button>
    </div>

    <Transition name="fade"><div v-if="msgBox" class="msg-box">{{ msgBox }}</div></Transition>

    <!-- 筛选 -->
    <div class="filter-bar">
      <select v-model="filterType" class="form-input filter-sel">
        <option value="">全部题型</option>
        <option v-for="t in QTYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
      </select>
      <select v-model="filterPub" class="form-input filter-sel">
        <option value="">全部状态</option>
        <option value="true">已发布</option>
        <option value="false">未发布</option>
      </select>
      <div class="search-row">
        <input v-model="searchQ" class="form-input" placeholder="搜索题干…" @keyup.enter="doSearch" />
        <button class="btn-secondary" @click="doSearch">搜索</button>
      </div>
    </div>

    <div v-if="loading" class="empty-tip">加载中…</div>
    <div v-else-if="list.length === 0" class="empty-tip">暂无题目，点击右上角「新建题目」。</div>
    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr><th>题型</th><th>题干</th><th>难度</th><th>分值</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="q in list" :key="q.id">
            <td><span :class="['qtype-tag', 'qt-' + q.qtype]">{{ q.qtype_display || QTYPE_LABEL[q.qtype] }}</span></td>
            <td class="q-title">{{ q.title }}</td>
            <td class="text-muted">{{ q.difficulty }}</td>
            <td class="text-muted">{{ q.score }}</td>
            <td>
              <span :class="['pub-tag', q.is_published ? 'pub-on' : 'pub-off']">
                {{ q.is_published ? '已发布' : '未发布' }}
              </span>
            </td>
            <td class="actions-cell">
              <button class="btn-xs" @click="openEdit(q)">编辑</button>
              <button class="btn-xs btn-danger" @click="remove(q)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pager">
      <button class="btn-sm" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <span class="pager-info">第 {{ page }} / {{ totalPages }} 页 · 共 {{ total }} 题</span>
      <button class="btn-sm" :disabled="page >= totalPages" @click="go(page + 1)">下一页</button>
    </div>

    <!-- 出题弹窗 -->
    <div v-if="modal" class="modal-overlay" @click.self="modal = false">
      <div class="modal modal-wide">
        <h2 class="modal-title">{{ editId ? '编辑题目' : '新建题目' }}</h2>

        <div class="form-row">
          <label class="form-label">题型</label>
          <div class="qtype-pills">
            <button
              v-for="t in QTYPES" :key="t.value"
              :class="['pill', form.qtype === t.value && 'pill-on']"
              @click="form.qtype = t.value"
            >{{ t.label }}</button>
          </div>
        </div>

        <input v-model="form.title" class="form-input" placeholder="题干" maxlength="300" />
        <textarea v-model="form.content" class="form-textarea" placeholder="题目详情（可选，支持 Markdown）" rows="2" />

        <!-- 单选 / 多选 -->
        <div v-if="form.qtype === 'single' || form.qtype === 'multiple'" class="editor-block">
          <div class="eb-label">
            选项（{{ form.qtype === 'single' ? '点圆圈选正确项' : '勾选正确项，可多选' }}）
          </div>
          <div v-for="(opt, i) in form.options" :key="i" class="opt-row">
            <input
              v-if="form.qtype === 'single'"
              type="radio" :value="i" v-model="form.correctIdx" class="opt-mark"
            />
            <input
              v-else
              type="checkbox" :checked="form.correctSet.includes(i)" @change="toggleCorrect(i)" class="opt-mark"
            />
            <span class="opt-key">{{ LETTERS[i] }}</span>
            <input v-model="form.options[i]" class="form-input opt-text" :placeholder="`选项 ${LETTERS[i]}`" />
            <button class="btn-xs btn-danger" :disabled="form.options.length <= 2" @click="removeOption(i)">✕</button>
          </div>
          <button class="btn-sm" :disabled="form.options.length >= LETTERS.length" @click="addOption">＋ 添加选项</button>
        </div>

        <!-- 判断 -->
        <div v-else-if="form.qtype === 'judge'" class="editor-block">
          <div class="eb-label">正确答案</div>
          <div class="judge-pills">
            <button :class="['pill', form.judgeAnswer === 'T' && 'pill-on']" @click="form.judgeAnswer = 'T'">✓ 正确（T）</button>
            <button :class="['pill', form.judgeAnswer === 'F' && 'pill-on']" @click="form.judgeAnswer = 'F'">✗ 错误（F）</button>
          </div>
        </div>

        <!-- 填空 -->
        <div v-else class="editor-block">
          <div class="eb-label">各空可接受答案（多个写法用逗号分隔，任一匹配即得分）</div>
          <div v-for="(b, i) in form.blanks" :key="i" class="opt-row">
            <span class="opt-key">空{{ i + 1 }}</span>
            <input v-model="form.blanks[i]" class="form-input opt-text" placeholder="如：链表，linked list" />
            <button class="btn-xs btn-danger" :disabled="form.blanks.length <= 1" @click="removeBlank(i)">✕</button>
          </div>
          <button class="btn-sm" @click="addBlank">＋ 添加空</button>
          <label class="check-label" style="margin-top:0.5rem">
            <input type="checkbox" v-model="form.blank_ignore_case" /> 判定忽略大小写与首尾空格
          </label>
        </div>

        <div class="form-grid">
          <div class="form-row">
            <label class="form-label">分值</label>
            <input v-model.number="form.score" type="number" min="0" class="form-input" />
          </div>
          <div class="form-row">
            <label class="form-label">难度</label>
            <select v-model="form.difficulty" class="form-input">
              <option v-for="d in DIFFICULTIES" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
        </div>

        <textarea v-model="form.explanation" class="form-textarea" placeholder="答案解析（可选）" rows="2" />
        <label class="check-label"><input type="checkbox" v-model="form.is_published" /> 立即发布（可被加入作业/考试）</label>

        <p v-if="formErr" class="form-error">{{ formErr }}</p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="modal = false">取消</button>
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : (editId ? '保存' : '创建') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.qbank { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.ph-left { display: flex; align-items: flex-start; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; flex-shrink: 0;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.page-title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.2rem; }
.page-sub { color: var(--text-muted); font-size: 0.85rem; margin: 0; }

.msg-box { background: #10b98122; border: 1px solid #10b98166; color: #10b981; border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.875rem; text-align: center; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.filter-bar { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
.filter-sel { width: auto; min-width: 8rem; }
.search-row { display: flex; gap: 0.5rem; margin-left: auto; }

/* 表格 */
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th { text-align: left; padding: 0.6rem 0.75rem; color: var(--text-muted); font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap; }
.data-table td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.text-muted { color: var(--text-muted); }
.q-title { color: var(--text-primary); max-width: 460px; }
.actions-cell { display: flex; gap: 0.4rem; }
.qtype-tag { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 10px; font-size: 0.75rem; white-space: nowrap; }
.qt-single { background: rgba(99,102,241,0.12); color: var(--accent); border: 1px solid rgba(99,102,241,0.3); }
.qt-multiple { background: #8b5cf622; color: #a78bfa; border: 1px solid #8b5cf644; }
.qt-judge { background: #10b98122; color: #10b981; border: 1px solid #10b98144; }
.qt-fill { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; }
.pub-tag { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 10px; font-size: 0.75rem; }
.pub-on { background: #10b98122; color: #10b981; border: 1px solid #10b98144; }
.pub-off { background: rgba(100,100,100,0.1); color: var(--text-muted); border: 1px solid var(--border); }

.pager { display: flex; align-items: center; justify-content: center; gap: 1rem; }
.pager-info { font-size: 0.85rem; color: var(--text-muted); }

/* 按钮 */
.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.5rem 1.25rem; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.45rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
.btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.3rem 0.7rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-sm:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn-sm:disabled { opacity: 0.4; cursor: default; }
.btn-xs { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem; white-space: nowrap; }
.btn-xs:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn-xs:disabled { opacity: 0.4; cursor: default; }
.btn-xs.btn-danger { border-color: #f8717144; color: #f87171; }
.btn-xs.btn-danger:hover:not(:disabled) { border-color: #f87171; }

/* 弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.75rem; width: 560px; max-width: 95vw; display: flex; flex-direction: column; gap: 0.85rem; }
.modal-wide { max-height: 90vh; overflow-y: auto; }
.modal-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.form-input, .form-textarea {
  background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px;
  padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.9rem; width: 100%; box-sizing: border-box;
}
.form-input:focus, .form-textarea:focus { outline: none; border-color: var(--accent); }
.form-textarea { resize: vertical; font-family: inherit; line-height: 1.5; }
.form-row { display: flex; flex-direction: column; gap: 0.3rem; }
.form-label { font-size: 0.8rem; color: var(--text-secondary); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }
.check-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-secondary); cursor: pointer; }
.form-error { color: #f87171; font-size: 0.875rem; margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }

/* 题型/判断切换 pill */
.qtype-pills, .judge-pills { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.pill { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.35rem 0.85rem; border-radius: 20px; cursor: pointer; font-size: 0.85rem; }
.pill:hover { border-color: var(--accent); }
.pill-on { background: var(--accent); color: #fff; border-color: var(--accent); }

/* 答案编辑器 */
.editor-block { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem; display: flex; flex-direction: column; gap: 0.6rem; }
.eb-label { font-size: 0.8rem; color: var(--text-muted); }
.opt-row { display: flex; align-items: center; gap: 0.6rem; }
.opt-mark { width: 1.1rem; height: 1.1rem; flex-shrink: 0; cursor: pointer; accent-color: var(--accent); }
.opt-key { font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--accent); width: 2.2rem; flex-shrink: 0; }
.opt-text { flex: 1; }

.empty-tip { text-align: center; padding: 2.5rem; color: var(--text-muted); }
</style>
