<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createContest, getProblemPool } from '@/api/contests'

const router = useRouter()

// ===== 步骤 =====
const step = ref(1)

// ===== 第一步：基本信息 =====
const title = ref('')
const description = ref('')
const ruleType = ref('ICPC')
const startTime = ref('')
const endTime = ref('')
const errors = ref({})

function validateStep1() {
  const e = {}
  if (!title.value.trim()) e.title = '比赛名称不能为空'
  else if (title.value.length > 100) e.title = '不能超过 100 字符'

  if (!startTime.value) {
    e.start = '请选择开始时间'
  } else if (new Date(startTime.value) <= new Date()) {
    e.start = '开始时间不能早于当前时间'
  }

  if (!endTime.value) {
    e.end = '请选择结束时间'
  } else if (startTime.value) {
    const s = new Date(startTime.value), en = new Date(endTime.value)
    if (en <= s) e.end = '结束时间必须晚于开始时间'
    else if (en - s < 5 * 60 * 1000) e.end = '至少比开始时间晚 5 分钟'
  }

  errors.value = e
  return Object.keys(e).length === 0
}

function goStep2() {
  if (!validateStep1()) return
  step.value = 2
  fetchProblems()
}

// ===== 第二步：题目选择 =====
const problems = ref([])
const selectedProblems = ref([])
const poolLoading = ref(false)
const poolPage = ref(1)
const poolTotalPages = ref(1)
const poolTotal = ref(0)
const filterDiff = ref('')
const filterKeyword = ref('')
let keywordTimer = null

const selectedIds = computed(() => new Set(selectedProblems.value.map(p => p.id)))

async function fetchProblems() {
  poolLoading.value = true
  try {
    const { data } = await getProblemPool({
      page: poolPage.value,
      difficulty: filterDiff.value,
      keyword: filterKeyword.value,
    })
    problems.value = data.problems
    poolTotalPages.value = data.total_pages
    poolTotal.value = data.total_count
  } finally {
    poolLoading.value = false
  }
}

function setDiff(d) {
  filterDiff.value = d
  poolPage.value = 1
  fetchProblems()
}

function onKeywordInput(e) {
  clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => {
    filterKeyword.value = e.target.value.trim()
    poolPage.value = 1
    fetchProblems()
  }, 300)
}

function changePage(delta) {
  const next = poolPage.value + delta
  if (next < 1 || next > poolTotalPages.value) return
  poolPage.value = next
  fetchProblems()
}

function addProblem(p) {
  if (selectedIds.value.has(p.id)) return
  selectedProblems.value.push({ id: p.id, title: p.title, difficulty: p.difficulty })
}

function removeProblem(id) {
  selectedProblems.value = selectedProblems.value.filter(p => p.id !== id)
}

function moveUp(i) {
  if (i === 0) return
  const arr = selectedProblems.value
  ;[arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]
}

function moveDown(i) {
  const arr = selectedProblems.value
  if (i >= arr.length - 1) return
  ;[arr[i], arr[i + 1]] = [arr[i + 1], arr[i]]
}

const DIFF_COLORS = {
  '暂无评定': '#bfbfbf', '入门': '#fe4c61',
  '普及-': '#f39c11', '普及/提高-': '#ffc116', '普及+/提高': '#52c41a',
  '提高+/省选-': '#3498db', '省选/NOI-': '#9d3dcf', 'NOI/NOI+/CTSC': '#0e1d69',
}
function diffColor(d) { return DIFF_COLORS[d] ?? '#bfbfbf' }

// ===== 提交 =====
const submitting = ref(false)
const submitError = ref('')
const showEmptyModal = ref(false)

function handleSubmit() {
  if (selectedProblems.value.length === 0) {
    showEmptyModal.value = true
    return
  }
  doSubmit()
}

async function doSubmit() {
  showEmptyModal.value = false
  submitting.value = true
  submitError.value = ''
  try {
    const { data } = await createContest({
      title: title.value.trim(),
      description: description.value.trim(),
      start_time: new Date(startTime.value).toISOString(),
      end_time: new Date(endTime.value).toISOString(),
      rule_type: ruleType.value,
      problem_ids: selectedProblems.value.map(p => p.id),
    })
    router.push(`/contests/${data.id}`)
  } catch (e) {
    submitError.value = e.response?.data?.detail || '创建失败，请重试'
    submitting.value = false
  }
}

const diffs = ['入门', '普及-', '普及/提高-', '普及+/提高', '提高+/省选-', '省选/NOI-', 'NOI+']
</script>

<template>
  <div class="create-wrap">

    <!-- 步骤条 -->
    <div class="steps-bar">
      <div class="step-item" :class="step === 1 ? 'active' : 'done'">
        <div class="step-circle">{{ step > 1 ? '✓' : '1' }}</div>
        <span class="step-label">比赛信息</span>
      </div>
      <div class="step-connector" :class="{ done: step > 1 }"></div>
      <div class="step-item" :class="{ active: step === 2 }">
        <div class="step-circle">2</div>
        <span class="step-label">选择题目</span>
      </div>
    </div>

    <!-- ===== 第一步 ===== -->
    <div v-if="step === 1" class="card">
      <div class="form-group">
        <label class="label">比赛名称<span class="req">*</span></label>
        <input
          v-model="title"
          class="input"
          :class="{ error: errors.title }"
          placeholder="请输入比赛名称（最多 100 字符）"
          maxlength="100"
          @input="delete errors.title"
        />
        <div v-if="errors.title" class="field-error">{{ errors.title }}</div>
      </div>

      <div class="form-group">
        <label class="label">比赛描述</label>
        <textarea v-model="description" class="textarea" rows="3" placeholder="简要说明比赛规则或考察方向（选填）"></textarea>
      </div>

      <div class="form-group">
        <label class="label">赛制<span class="req">*</span></label>
        <div class="rule-group">
          <div
            class="rule-card"
            :class="{ selected: ruleType === 'ICPC' }"
            @click="ruleType = 'ICPC'"
          >
            <div class="rule-badge icpc">ICPC</div>
            <div class="rule-title">ICPC 赛制</div>
            <div class="rule-desc">以 AC 题数排名，罚时（提交时间 + 错误 × 20 分钟）为辅</div>
          </div>
          <div
            class="rule-card"
            :class="{ selected: ruleType === 'IOI' }"
            @click="ruleType = 'IOI'"
          >
            <div class="rule-badge ioi">IOI</div>
            <div class="rule-title">IOI 赛制</div>
            <div class="rule-desc">以总分排名，每题 AC 得 100 分，无罚时限制</div>
          </div>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group" style="margin-bottom:0">
          <label class="label">开始时间<span class="req">*</span></label>
          <input
            v-model="startTime"
            type="datetime-local"
            class="input"
            :class="{ error: errors.start }"
            @change="delete errors.start"
          />
          <div v-if="errors.start" class="field-error">{{ errors.start }}</div>
        </div>
        <div class="form-group" style="margin-bottom:0">
          <label class="label">结束时间<span class="req">*</span></label>
          <input
            v-model="endTime"
            type="datetime-local"
            class="input"
            :class="{ error: errors.end }"
            @change="delete errors.end"
          />
          <div v-if="errors.end" class="field-error">{{ errors.end }}</div>
        </div>
      </div>

      <div class="step-actions">
        <button class="btn-outline" @click="router.push('/contests')">取消</button>
        <button class="btn-primary" @click="goStep2">
          下一步：选择题目
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>
    </div>

    <!-- ===== 第二步 ===== -->
    <div v-if="step === 2" class="card">
      <div class="selector-wrap">
        <!-- 左：题目池 -->
        <div class="selector-panel">
          <div class="panel-header">
            <div class="panel-title">题目池</div>
            <!-- 难度筛选 -->
            <div class="diff-row">
              <span
                class="diff-chip"
                :class="{ active: filterDiff === '' }"
                @click="setDiff('')"
              >全部</span>
              <span
                v-for="d in diffs" :key="d"
                class="diff-chip"
                :class="{ active: filterDiff === d }"
                @click="setDiff(d)"
              >{{ d }}</span>
            </div>
            <!-- 关键词搜索 -->
            <input class="search-input" placeholder="搜索题目标题..." @input="onKeywordInput" />
          </div>

          <div class="panel-body">
            <div v-if="poolLoading" class="empty-tip">加载中...</div>
            <div v-else-if="problems.length === 0" class="empty-tip">没有符合条件的题目</div>
            <div
              v-for="p in problems" :key="p.id"
              class="pool-item"
              :class="{ added: selectedIds.has(p.id) }"
            >
              <div class="prob-info">
                <div class="prob-title">{{ p.title }}</div>
                <div class="prob-meta">
                  <span class="diff-badge" :style="{ background: diffColor(p.difficulty), color: '#fff' }">{{ p.difficulty }}</span>
                  <span v-for="t in p.tags.slice(0,3)" :key="t" class="tag-mini">{{ t }}</span>
                </div>
              </div>
              <button
                class="btn-add"
                :disabled="selectedIds.has(p.id)"
                @click="addProblem(p)"
              >{{ selectedIds.has(p.id) ? '已添加' : '添加' }}</button>
            </div>
          </div>

          <div class="panel-footer">
            <span>共 {{ poolTotal }} 道</span>
            <div class="pager">
              <button class="pager-btn" :disabled="poolPage <= 1" @click="changePage(-1)">‹</button>
              <span>{{ poolPage }} / {{ poolTotalPages || 1 }}</span>
              <button class="pager-btn" :disabled="poolPage >= poolTotalPages" @click="changePage(1)">›</button>
            </div>
          </div>
        </div>

        <!-- 右：已选 -->
        <div class="selector-panel">
          <div class="panel-header">
            <div class="panel-title">已选题目（{{ selectedProblems.length }}）</div>
          </div>
          <div class="panel-body">
            <div v-if="selectedProblems.length === 0" class="empty-tip">暂未选择题目，从左侧添加</div>
            <div v-for="(p, i) in selectedProblems" :key="p.id" class="selected-item">
              <div class="sel-order">{{ String.fromCharCode(65 + i) }}</div>
              <div class="prob-info">
                <div class="prob-title">{{ p.title }}</div>
                <span class="diff-badge" :style="{ background: diffColor(p.difficulty), color: '#fff' }">{{ p.difficulty }}</span>
              </div>
              <div class="arrows">
                <button class="arrow-btn" :disabled="i === 0" @click="moveUp(i)">▲</button>
                <button class="arrow-btn" :disabled="i === selectedProblems.length - 1" @click="moveDown(i)">▼</button>
              </div>
              <button class="btn-remove" @click="removeProblem(p.id)">移除</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="submitError" class="submit-error">{{ submitError }}</div>

      <div class="step-actions">
        <button class="btn-outline" @click="step = 1">上一步</button>
        <button class="btn-primary" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '创建中...' : '创建比赛' }}
        </button>
      </div>
    </div>

    <!-- 空题目确认弹窗 -->
    <div v-if="showEmptyModal" class="modal-overlay" @click.self="showEmptyModal = false">
      <div class="modal-box">
        <div class="modal-title">尚未选择题目</div>
        <div class="modal-desc">确定要创建一场没有题目的比赛吗？</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="showEmptyModal = false">取消</button>
          <button class="btn-primary" @click="doSubmit">确定创建</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.create-wrap { max-width: 960px; margin: 0 auto; padding: 0.5rem 0 3rem; }

/* 步骤条 */
.steps-bar {
  display: flex; align-items: center; justify-content: center;
  gap: 0; margin-bottom: 1.8rem;
}
.step-item { display: flex; align-items: center; gap: 8px; }
.step-circle {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.82rem; font-weight: 700;
  border: 2px solid var(--border); color: var(--text-muted);
  background: var(--bg-card); flex-shrink: 0;
}
.step-label { font-size: 0.875rem; font-weight: 500; color: var(--text-muted); white-space: nowrap; }
.step-connector { width: 60px; height: 2px; background: var(--border); margin: 0 10px; flex-shrink: 0; }
.step-connector.done { background: #22c55e; }
.step-item.active .step-circle { border-color: var(--accent); background: var(--accent); color: #fff; }
.step-item.active .step-label { color: var(--text-primary); font-weight: 600; }
.step-item.done .step-circle { border-color: #22c55e; background: #22c55e; color: #fff; }

/* 卡片 */
.card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 2rem 2.2rem;
}

/* 表单 */
.form-group { margin-bottom: 1.4rem; }
.label {
  display: block; font-size: 0.875rem; font-weight: 600;
  color: var(--text-primary); margin-bottom: 6px;
}
.req { color: #ef4444; margin-left: 2px; }
.input, .textarea {
  width: 100%; background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.6rem 0.9rem; font-size: 0.9rem;
  color: var(--text-primary); outline: none; box-sizing: border-box;
  font-family: inherit; transition: border-color 0.15s;
}
.input:focus, .textarea:focus { border-color: var(--accent); }
.input.error { border-color: #ef4444; }
.textarea { resize: vertical; min-height: 80px; }
.field-error { font-size: 0.78rem; color: #ef4444; margin-top: 4px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; }

/* 赛制 */
.rule-group { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.rule-card {
  border: 2px solid var(--border); border-radius: 10px; padding: 1rem;
  cursor: pointer; transition: border-color 0.15s, background 0.15s;
}
.rule-card:hover { border-color: var(--accent); }
.rule-card.selected { border-color: var(--accent); background: rgba(99,102,241,.06); }
.rule-badge {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.72rem; font-weight: 700; margin-bottom: 6px;
}
.rule-badge.icpc { background: rgba(99,102,241,.15); color: var(--accent); }
.rule-badge.ioi  { background: rgba(234,179,8,.15); color: #ca8a04; }
.rule-title { font-size: 0.875rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.rule-desc  { font-size: 0.8rem; color: var(--text-muted); line-height: 1.4; }

/* 底部按钮 */
.step-actions {
  display: flex; justify-content: flex-end; gap: 10px;
  margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid var(--border);
}
.btn-primary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0.55rem 1.3rem; background: var(--accent); color: #fff;
  border: none; border-radius: 8px; font-size: 0.9rem; font-weight: 600;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-outline {
  padding: 0.55rem 1.2rem; background: transparent;
  border: 1px solid var(--border); color: var(--text-primary);
  border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.btn-outline:hover { background: var(--bg-secondary); }

/* 选择器 */
.selector-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; min-height: 460px; }
.selector-panel {
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 10px; display: flex; flex-direction: column; overflow: hidden;
}
.panel-header { padding: 12px 14px 10px; border-bottom: 1px solid var(--border); background: var(--bg-card); }
.panel-title { font-size: 0.9rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.diff-row { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
.diff-chip {
  padding: 3px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 500;
  cursor: pointer; border: 1px solid var(--border); background: var(--bg-secondary);
  color: var(--text-muted); transition: all 0.15s;
}
.diff-chip:hover { border-color: var(--accent); color: var(--accent); }
.diff-chip.active { border-color: var(--accent); background: var(--accent); color: #fff; }
.search-input {
  width: 100%; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 7px; padding: 6px 10px; font-size: 0.82rem; color: var(--text-primary);
  outline: none; box-sizing: border-box;
}
.search-input:focus { border-color: var(--accent); }

.panel-body { flex: 1; overflow-y: auto; padding: 6px 0; }
.empty-tip { text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); font-size: 0.85rem; }

.pool-item {
  display: flex; align-items: center; padding: 9px 12px; gap: 8px;
  border-bottom: 1px solid var(--border); transition: background 0.1s;
}
.pool-item:last-child { border-bottom: none; }
.pool-item:hover { background: var(--bg-card); }
.pool-item.added { opacity: 0.4; pointer-events: none; }

.selected-item {
  display: flex; align-items: center; padding: 9px 12px; gap: 8px;
  border-bottom: 1px solid var(--border);
}
.selected-item:last-child { border-bottom: none; }
.sel-order {
  width: 24px; height: 24px; border-radius: 50%; background: var(--accent);
  color: #fff; font-size: 0.72rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

.prob-info { flex: 1; min-width: 0; }
.prob-title {
  font-size: 0.85rem; font-weight: 500; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.prob-meta { display: flex; gap: 4px; margin-top: 3px; flex-wrap: wrap; }

.diff-badge {
  font-size: 0.68rem; font-weight: 600; padding: 1px 7px; border-radius: 10px; color: #fff;
}

.tag-mini {
  font-size: 0.68rem; padding: 1px 6px; border-radius: 8px;
  background: var(--bg-secondary); color: var(--text-muted); border: 1px solid var(--border);
}

.btn-add {
  flex-shrink: 0; padding: 4px 10px; border-radius: 6px;
  font-size: 0.75rem; font-weight: 600; cursor: pointer;
  border: none; background: var(--accent); color: #fff; transition: opacity 0.15s;
}
.btn-add:hover:not(:disabled) { opacity: 0.85; }
.btn-add:disabled { background: var(--bg-input); color: var(--text-muted); cursor: default; }

.arrows { display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }
.arrow-btn {
  width: 22px; height: 18px; border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text-muted); border-radius: 4px; cursor: pointer; font-size: 0.68rem;
  display: flex; align-items: center; justify-content: center;
}
.arrow-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.arrow-btn:disabled { opacity: 0.25; cursor: not-allowed; }

.btn-remove {
  flex-shrink: 0; padding: 4px 10px; border-radius: 6px;
  font-size: 0.75rem; font-weight: 600; cursor: pointer;
  border: none; background: rgba(239,68,68,.12); color: #ef4444;
}
.btn-remove:hover { background: rgba(239,68,68,.22); }

.panel-footer {
  padding: 7px 12px; border-top: 1px solid var(--border); background: var(--bg-card);
  display: flex; align-items: center; justify-content: space-between;
  font-size: 0.78rem; color: var(--text-muted);
}
.pager { display: flex; align-items: center; gap: 6px; }
.pager-btn {
  padding: 2px 8px; border-radius: 5px; border: 1px solid var(--border);
  background: var(--bg-secondary); color: var(--text-muted); cursor: pointer; font-size: 0.75rem;
}
.pager-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pager-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.submit-error { color: #ef4444; font-size: 0.85rem; margin-top: 1rem; }

/* 弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.55);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-box {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 1.8rem 2rem; max-width: 380px; width: 90%;
}
.modal-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.modal-desc { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 1.5rem; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }

@media (max-width: 700px) {
  .selector-wrap { grid-template-columns: 1fr; }
  .rule-group { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; }
  .card { padding: 1.2rem 1rem; }
}
</style>
