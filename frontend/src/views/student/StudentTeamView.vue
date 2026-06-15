<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getTeam, getAnnouncements, getAssignments, getTeamContests, createTeamContest,
} from '@/api/team'
import { getProblemPool } from '@/api/contests'

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)

const team = ref(null)
const announcements = ref([])
const assignments = ref([])
const contests = ref([])
const loading = ref(true)
const activeTab = ref('announcements')

const isCaptain = computed(() => team.value?.my_role === 'captain')
const canCreate = computed(() => isCaptain.value || team.value?.my_role === 'creator')

onMounted(async () => {
  try {
    const [td, ann, asgn, cts] = await Promise.all([
      getTeam(teamId),
      getAnnouncements(teamId),
      getAssignments(teamId),
      getTeamContests(teamId),
    ])
    team.value = td.data
    announcements.value = ann.data
    assignments.value = asgn.data
    contests.value = cts.data
  } finally {
    loading.value = false
  }
})

const pinnedAnn = computed(() => announcements.value.filter(a => a.is_pinned))
const normalAnn = computed(() => announcements.value.filter(a => !a.is_pinned))

const DIFF_COLORS = {
  '暂无评定': '#bfbfbf', '入门': '#fe4c61',
  '普及-': '#f39c11', '普及/提高-': '#ffc116', '普及+/提高': '#52c41a',
  '提高+/省选-': '#3498db', '省选/NOI-': '#9d3dcf', 'NOI/NOI+/CTSC': '#0e1d69',
}
function diffColor(d) { return DIFF_COLORS[d] ?? '#6b7280' }

function fmt(dt) { return dt ? new Date(dt).toLocaleDateString('zh-CN') : '' }
function fmtDeadline(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const now = new Date()
  const diff = d - now
  if (diff < 0) return '已截止'
  if (diff < 86400000) return `${Math.ceil(diff / 3600000)} 小时后截止`
  return `${Math.ceil(diff / 86400000)} 天后截止`
}
function deadlineClass(dt) {
  if (!dt) return ''
  const diff = new Date(dt) - new Date()
  if (diff < 0) return 'dl-over'
  if (diff < 86400000) return 'dl-urgent'
  return 'dl-ok'
}
function catLabel(c) {
  return ({ practice: '练习', homework: '作业', exam: '考试' })[c] || '作业'
}

// ── 比赛状态 ──
const STATUS_LABEL = { upcoming: '未开始', running: '进行中', ended: '已结束' }
const STATUS_CLASS = { upcoming: 'st-upcoming', running: 'st-running', ended: 'st-ended' }
function fmtTime(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// ── 创建比赛弹窗 ──
const showCreateContest = ref(false)
const createStep = ref(1)

const ctTitle = ref('')
const ctDesc = ref('')
const ctRule = ref('ICPC')
const ctStart = ref('')
const ctEnd = ref('')
const ctErrors = ref({})

const poolProblems = ref([])
const selectedProblems = ref([])
const poolLoading = ref(false)
const poolPage = ref(1)
const poolTotalPages = ref(1)
const poolTotal = ref(0)
const poolDiff = ref('')
const poolKeyword = ref('')
let kwTimer = null

const selectedIds = computed(() => new Set(selectedProblems.value.map(p => p.id)))

const submitting = ref(false)
const createError = ref('')

function openCreate() {
  createStep.value = 1
  ctTitle.value = ''; ctDesc.value = ''; ctRule.value = 'ICPC'
  ctStart.value = ''; ctEnd.value = ''
  ctErrors.value = {}
  selectedProblems.value = []
  poolProblems.value = []
  poolPage.value = 1; poolDiff.value = ''; poolKeyword.value = ''
  createError.value = ''
  showCreateContest.value = true
}

function validateStep1() {
  const e = {}
  if (!ctTitle.value.trim()) e.title = '比赛名称不能为空'
  else if (ctTitle.value.length > 100) e.title = '不能超过 100 字符'
  if (!ctStart.value) e.start = '请选择开始时间'
  else if (new Date(ctStart.value) <= new Date()) e.start = '开始时间不能早于当前时间'
  if (!ctEnd.value) e.end = '请选择结束时间'
  else if (ctStart.value) {
    const s = new Date(ctStart.value), en = new Date(ctEnd.value)
    if (en <= s) e.end = '结束时间必须晚于开始时间'
    else if (en - s < 5 * 60 * 1000) e.end = '至少比开始时间晚 5 分钟'
  }
  ctErrors.value = e
  return Object.keys(e).length === 0
}

async function goStep2() {
  if (!validateStep1()) return
  createStep.value = 2
  await fetchPool()
}

async function fetchPool() {
  poolLoading.value = true
  try {
    const { data } = await getProblemPool({
      page: poolPage.value,
      difficulty: poolDiff.value,
      keyword: poolKeyword.value,
    })
    poolProblems.value = data.problems
    poolTotalPages.value = data.total_pages
    poolTotal.value = data.total_count
  } finally {
    poolLoading.value = false
  }
}

function setDiff(d) { poolDiff.value = d; poolPage.value = 1; fetchPool() }
function onKwInput(e) {
  clearTimeout(kwTimer)
  kwTimer = setTimeout(() => { poolKeyword.value = e.target.value.trim(); poolPage.value = 1; fetchPool() }, 300)
}
function changePage(delta) {
  const next = poolPage.value + delta
  if (next < 1 || next > poolTotalPages.value) return
  poolPage.value = next; fetchPool()
}
function addProblem(p) {
  if (selectedIds.value.has(p.id)) return
  selectedProblems.value.push({ id: p.id, title: p.title, difficulty: p.difficulty })
}
function removeProblem(id) { selectedProblems.value = selectedProblems.value.filter(p => p.id !== id) }
function moveUp(i) {
  if (i === 0) return
  const arr = selectedProblems.value;[arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]
}
function moveDown(i) {
  const arr = selectedProblems.value
  if (i >= arr.length - 1) return;[arr[i], arr[i + 1]] = [arr[i + 1], arr[i]]
}

async function doCreateContest() {
  submitting.value = true; createError.value = ''
  try {
    const { data } = await createTeamContest(teamId, {
      title: ctTitle.value.trim(),
      description: ctDesc.value.trim(),
      start_time: new Date(ctStart.value).toISOString(),
      end_time: new Date(ctEnd.value).toISOString(),
      rule_type: ctRule.value,
      problem_ids: selectedProblems.value.map(p => p.id),
    })
    showCreateContest.value = false
    router.push(`/contests/${data.id}`)
  } catch (e) {
    createError.value = e.response?.data?.detail || '创建失败，请重试'
  } finally {
    submitting.value = false
  }
}

const diffs = ['入门', '普及-', '普及/提高-', '普及+/提高', '提高+/省选-', '省选/NOI-', 'NOI+']
</script>

<template>
  <div class="st-view" v-if="!loading && team">

    <!-- 顶部 -->
    <div class="st-header">
      <button class="btn-back" @click="router.push('/my-teams')">← 我的团队</button>
      <div class="header-info">
        <h1 class="st-name">
          {{ team.name }}
          <span v-if="isCaptain" class="captain-badge">👑 队长</span>
        </h1>
        <p v-if="team.description" class="st-desc">{{ team.description }}</p>
      </div>
      <div v-if="isCaptain" class="captain-nav">
        <button class="btn-captain" @click="router.push(`/teacher/teams/${teamId}`)">成员管理</button>
        <button class="btn-captain" @click="router.push(`/teacher/teams/${teamId}/dashboard`)">团队排行 →</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button :class="['tab', activeTab === 'announcements' && 'tab-active']" @click="activeTab = 'announcements'">
        公告
        <span v-if="pinnedAnn.length > 0" class="tab-badge">{{ pinnedAnn.length }}</span>
      </button>
      <button :class="['tab', activeTab === 'assignments' && 'tab-active']" @click="activeTab = 'assignments'">
        作业（{{ assignments.length }}）
      </button>
      <button :class="['tab', activeTab === 'contests' && 'tab-active']" @click="activeTab = 'contests'">
        比赛（{{ contests.length }}）
      </button>
    </div>

    <!-- 公告 Tab -->
    <div v-if="activeTab === 'announcements'">
      <div v-if="announcements.length === 0" class="empty-tip">暂无公告</div>
      <div v-else class="ann-list">
        <div v-for="a in pinnedAnn" :key="a.id" class="ann-card ann-pinned">
          <div class="ann-head">
            <span class="ann-pin-icon">📌</span>
            <span class="ann-title">{{ a.title }}</span>
            <span class="ann-date text-muted">{{ fmt(a.created_at) }}</span>
          </div>
          <div v-if="a.content" class="ann-content">{{ a.content }}</div>
        </div>
        <div v-for="a in normalAnn" :key="a.id" class="ann-card">
          <div class="ann-head">
            <span class="ann-title">{{ a.title }}</span>
            <span class="ann-date text-muted">{{ fmt(a.created_at) }}</span>
          </div>
          <div v-if="a.content" class="ann-content">{{ a.content }}</div>
        </div>
      </div>
    </div>

    <!-- 作业 Tab -->
    <div v-if="activeTab === 'assignments'">
      <div v-if="assignments.length === 0" class="empty-tip">暂无作业</div>
      <div v-else class="asgn-list">
        <div v-for="a in assignments" :key="a.id" class="asgn-card">
          <div class="asgn-head">
            <div class="asgn-title-wrap">
              <span :class="['asgn-cat', 'cat-' + (a.category || 'homework')]">{{ catLabel(a.category) }}</span>
              <span class="asgn-title">{{ a.title }}</span>
            </div>
            <div class="asgn-right">
              <span v-if="a.category !== 'exam'" class="asgn-progress">
                <span class="prog-done">{{ a.problems.filter(p => p.ac).length }}</span>
                <span class="prog-sep">/</span>
                <span class="prog-total">{{ a.problem_count }}</span>
              </span>
              <span v-if="a.category === 'exam' && a.start_time" :class="['asgn-deadline', deadlineClass(a.end_time)]">
                {{ fmtTime(a.start_time) }} 开考
              </span>
              <span v-else-if="a.deadline" :class="['asgn-deadline', deadlineClass(a.deadline)]">
                {{ fmtDeadline(a.deadline) }}
              </span>
              <button class="btn-enter" @click="router.push(`/exam/${a.id}`)">进入 →</button>
            </div>
          </div>
          <div v-if="a.category !== 'exam'" class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: a.problem_count ? (a.problems.filter(p=>p.ac).length / a.problem_count * 100) + '%' : '0%' }"
            ></div>
          </div>
          <p v-if="a.description" class="asgn-desc text-muted">{{ a.description }}</p>
          <div class="asgn-meta text-muted">{{ a.problem_count }} 编程 · {{ a.question_count || 0 }} 客观 · 满分 {{ a.total_score ?? 0 }}</div>
          <div v-if="a.category !== 'exam' && a.problems.length > 0" class="prob-list">
            <a
              v-for="p in a.problems" :key="p.id"
              class="prob-item" :class="{ 'prob-ac': p.ac }"
              :href="`/problems/${p.id}?assignment=${a.id}`" target="_blank"
            >
              <span class="prob-check">{{ p.ac ? '✓' : '○' }}</span>
              <span class="prob-title">#{{ p.id }} {{ p.title }}</span>
              <span class="prob-diff" :style="{ color: diffColor(p.difficulty) }">{{ p.difficulty }}</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- 比赛 Tab -->
    <div v-if="activeTab === 'contests'">
      <div class="section-header">
        <span></span>
        <button v-if="isCaptain" class="btn-create-contest" @click="openCreate">＋ 创建比赛</button>
      </div>
      <div v-if="contests.length === 0" class="empty-tip">暂无团队比赛</div>
      <div v-else class="contest-list">
        <div
          v-for="c in contests" :key="c.id"
          class="contest-card"
          @click="router.push(`/contests/${c.id}`)"
        >
          <div class="contest-main">
            <div class="contest-title">{{ c.title }}</div>
            <div class="contest-meta">
              <span :class="['contest-status', STATUS_CLASS[c.status]]">{{ STATUS_LABEL[c.status] }}</span>
              <span class="contest-rule">{{ c.rule_type }}</span>
              <span class="contest-count">{{ c.problem_count }} 题</span>
            </div>
          </div>
          <div class="contest-times">
            <span class="time-item">{{ fmtTime(c.start_time) }} → {{ fmtTime(c.end_time) }}</span>
          </div>
        </div>
      </div>
    </div>

  </div>
  <div v-else-if="loading" class="loading-tip">加载中…</div>

  <!-- 创建比赛弹窗 -->
  <div v-if="showCreateContest" class="modal-overlay" @click.self="showCreateContest = false">
    <div class="create-modal">
      <!-- 步骤条 -->
      <div class="modal-steps">
        <div class="mstep" :class="createStep === 1 ? 'mstep-active' : 'mstep-done'">
          <div class="mstep-circle">{{ createStep > 1 ? '✓' : '1' }}</div>
          <span>比赛信息</span>
        </div>
        <div class="mstep-line" :class="{ done: createStep > 1 }"></div>
        <div class="mstep" :class="{ 'mstep-active': createStep === 2 }">
          <div class="mstep-circle">2</div>
          <span>选择题目</span>
        </div>
      </div>

      <!-- Step 1 -->
      <template v-if="createStep === 1">
        <div class="mform-group">
          <label>比赛名称 <span class="req">*</span></label>
          <input v-model="ctTitle" class="mform-input" :class="{ error: ctErrors.title }"
            placeholder="最多 100 字符" maxlength="100" @input="delete ctErrors.title" />
          <div v-if="ctErrors.title" class="field-err">{{ ctErrors.title }}</div>
        </div>
        <div class="mform-group">
          <label>比赛描述</label>
          <textarea v-model="ctDesc" class="mform-input mform-textarea" rows="2" placeholder="选填"></textarea>
        </div>
        <div class="mform-group">
          <label>赛制 <span class="req">*</span></label>
          <div class="rule-row">
            <div class="rule-opt" :class="{ selected: ctRule === 'ICPC' }" @click="ctRule = 'ICPC'">
              <span class="rule-badge icpc">ICPC</span> AC 题数 + 罚时
            </div>
            <div class="rule-opt" :class="{ selected: ctRule === 'IOI' }" @click="ctRule = 'IOI'">
              <span class="rule-badge ioi">IOI</span> 总分制
            </div>
          </div>
        </div>
        <div class="mform-row">
          <div class="mform-group" style="margin-bottom:0">
            <label>开始时间 <span class="req">*</span></label>
            <input v-model="ctStart" type="datetime-local" class="mform-input" :class="{ error: ctErrors.start }" @change="delete ctErrors.start" />
            <div v-if="ctErrors.start" class="field-err">{{ ctErrors.start }}</div>
          </div>
          <div class="mform-group" style="margin-bottom:0">
            <label>结束时间 <span class="req">*</span></label>
            <input v-model="ctEnd" type="datetime-local" class="mform-input" :class="{ error: ctErrors.end }" @change="delete ctErrors.end" />
            <div v-if="ctErrors.end" class="field-err">{{ ctErrors.end }}</div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreateContest = false">取消</button>
          <button class="btn-primary" @click="goStep2">下一步</button>
        </div>
      </template>

      <!-- Step 2 -->
      <template v-if="createStep === 2">
        <div class="selector-wrap">
          <!-- 题目池 -->
          <div class="selector-panel">
            <div class="panel-hd">
              <div class="panel-title">题目池（{{ poolTotal }}）</div>
              <div class="diff-row">
                <span class="diff-chip" :class="{ active: poolDiff === '' }" @click="setDiff('')">全部</span>
                <span v-for="d in diffs" :key="d" class="diff-chip" :class="{ active: poolDiff === d }" @click="setDiff(d)">{{ d }}</span>
              </div>
              <input class="search-input" placeholder="搜索题目..." @input="onKwInput" />
            </div>
            <div class="panel-body">
              <div v-if="poolLoading" class="empty-tip">加载中…</div>
              <div v-else-if="poolProblems.length === 0" class="empty-tip">无符合条件题目</div>
              <div v-for="p in poolProblems" :key="p.id" class="pool-item" :class="{ added: selectedIds.has(p.id) }">
                <div class="prob-info">
                  <div class="prob-title-s">{{ p.title }}</div>
                  <span class="diff-badge" :style="{ background: diffColor(p.difficulty), color: '#fff' }">{{ p.difficulty }}</span>
                </div>
                <button class="btn-add" :disabled="selectedIds.has(p.id)" @click="addProblem(p)">
                  {{ selectedIds.has(p.id) ? '已加' : '添加' }}
                </button>
              </div>
            </div>
            <div class="panel-ft">
              <button class="pager-btn" :disabled="poolPage <= 1" @click="changePage(-1)">‹</button>
              <span>{{ poolPage }} / {{ poolTotalPages || 1 }}</span>
              <button class="pager-btn" :disabled="poolPage >= poolTotalPages" @click="changePage(1)">›</button>
            </div>
          </div>

          <!-- 已选 -->
          <div class="selector-panel">
            <div class="panel-hd">
              <div class="panel-title">已选（{{ selectedProblems.length }}）</div>
            </div>
            <div class="panel-body">
              <div v-if="selectedProblems.length === 0" class="empty-tip">从左侧添加题目</div>
              <div v-for="(p, i) in selectedProblems" :key="p.id" class="selected-item">
                <div class="sel-order">{{ String.fromCharCode(65 + i) }}</div>
                <div class="prob-info">
                  <div class="prob-title-s">{{ p.title }}</div>
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

        <div v-if="createError" class="create-err">{{ createError }}</div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="createStep = 1">上一步</button>
          <button class="btn-primary" :disabled="submitting" @click="doCreateContest">
            {{ submitting ? '创建中…' : '创建比赛' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.st-view { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }

.st-header { display: flex; align-items: flex-start; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; margin-top: 0.2rem; transition: border-color 0.15s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.header-info { flex: 1; }
.st-name { font-size: 1.35rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.2rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.st-desc { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
.captain-badge { font-size: 0.78rem; background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; border-radius: 4px; padding: 0.1rem 0.5rem; }
.captain-nav { display: flex; flex-direction: column; gap: 0.4rem; flex-shrink: 0; }
.btn-captain {
  background: none; border: 1px solid rgba(99,102,241,0.4); color: var(--accent);
  padding: 0.3rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem;
  white-space: nowrap; transition: all 0.15s;
}
.btn-captain:hover { background: rgba(99,102,241,0.1); border-color: var(--accent); }

.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); }
.tab {
  background: none; border: none; border-bottom: 2px solid transparent;
  padding: 0.6rem 1.25rem; color: var(--text-secondary); cursor: pointer;
  font-size: 0.9rem; display: flex; align-items: center; gap: 0.4rem;
  transition: color 0.15s, border-color 0.15s;
}
.tab:hover { color: var(--text-primary); }
.tab-active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-badge {
  background: #f59e0b; color: #fff; border-radius: 10px;
  padding: 0 0.4rem; font-size: 0.7rem; font-weight: 700; line-height: 1.4;
}

/* Announcements */
.ann-list { display: flex; flex-direction: column; gap: 0.75rem; }
.ann-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
.ann-pinned { border-color: #f59e0b55; background: rgba(245,158,11,0.04); }
.ann-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
.ann-pin-icon { font-size: 0.9rem; }
.ann-title { flex: 1; font-weight: 600; color: var(--text-primary); }
.ann-date { font-size: 0.78rem; }
.ann-content { font-size: 0.875rem; color: var(--text-secondary); white-space: pre-wrap; line-height: 1.6; margin: 0; }

/* Assignments */
.asgn-list { display: flex; flex-direction: column; gap: 1rem; }
.asgn-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 1.1rem; display: flex; flex-direction: column; gap: 0.6rem; }
.asgn-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.asgn-title { font-weight: 600; color: var(--text-primary); font-size: 1rem; }
.asgn-right { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }
.asgn-progress { font-size: 0.9rem; font-family: monospace; }
.prog-done { color: #10b981; font-weight: 700; }
.prog-sep { color: var(--text-muted); }
.prog-total { color: var(--text-muted); }
.asgn-deadline { font-size: 0.78rem; padding: 0.1rem 0.5rem; border-radius: 4px; font-weight: 500; }
.dl-ok { background: #10b98122; color: #10b981; }
.dl-urgent { background: #f59e0b22; color: #f59e0b; }
.dl-over { background: #f8717122; color: #f87171; }
.progress-bar { height: 4px; background: var(--bg-secondary); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: #10b981; border-radius: 2px; transition: width 0.3s; }
.asgn-desc { font-size: 0.85rem; margin: 0; }
.prob-list { display: flex; flex-direction: column; gap: 0.3rem; border-top: 1px solid var(--border); padding-top: 0.6rem; }
.prob-item { display: flex; align-items: center; gap: 0.6rem; padding: 0.3rem 0.4rem; border-radius: 4px; text-decoration: none; transition: background 0.1s; }
.prob-item:hover { background: var(--bg-hover); }
.prob-check { font-size: 0.85rem; width: 1.1rem; text-align: center; color: var(--text-muted); }
.prob-ac .prob-check { color: #10b981; }
.prob-ac .prob-title { color: var(--text-secondary); }
.prob-title { flex: 1; font-size: 0.875rem; color: var(--text-primary); }
.prob-diff { font-size: 0.78rem; white-space: nowrap; }
.asgn-title-wrap { display: flex; align-items: center; gap: 0.5rem; min-width: 0; }
.asgn-cat { font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 4px; flex-shrink: 0; }
.cat-practice { background: rgba(100,100,100,0.12); color: var(--text-muted); border: 1px solid var(--border); }
.cat-homework { background: rgba(99,102,241,0.12); color: var(--accent); border: 1px solid rgba(99,102,241,0.3); }
.cat-exam { background: #ef444422; color: #f87171; border: 1px solid #ef444444; }
.btn-enter { background: var(--accent); color: #fff; border: none; padding: 0.3rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; font-weight: 600; white-space: nowrap; }
.btn-enter:hover { background: var(--accent-hover); }
.asgn-meta { font-size: 0.8rem; }

/* Contests */
.section-header { display: flex; justify-content: flex-end; margin-bottom: 0.75rem; }
.btn-create-contest {
  background: var(--accent); color: #fff; border: none;
  padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600;
  transition: opacity 0.15s;
}
.btn-create-contest:hover { opacity: 0.85; }

.contest-list { display: flex; flex-direction: column; gap: 0.6rem; }
.contest-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem 1.2rem; cursor: pointer; transition: border-color 0.15s;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}
.contest-card:hover { border-color: var(--accent); }
.contest-main { display: flex; flex-direction: column; gap: 0.4rem; }
.contest-title { font-weight: 600; color: var(--text-primary); font-size: 0.95rem; }
.contest-meta { display: flex; align-items: center; gap: 0.6rem; }
.contest-status { font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 10px; font-weight: 600; }
.st-upcoming { background: #3b82f622; color: #3b82f6; }
.st-running  { background: #10b98122; color: #10b981; }
.st-ended    { background: var(--bg-secondary); color: var(--text-muted); }
.contest-rule { font-size: 0.75rem; color: var(--text-muted); border: 1px solid var(--border); border-radius: 4px; padding: 0.1rem 0.4rem; }
.contest-count { font-size: 0.78rem; color: var(--text-muted); }
.contest-times { font-size: 0.78rem; color: var(--text-muted); flex-shrink: 0; }

/* Misc */
.text-muted { color: var(--text-muted); }
.empty-tip { text-align: center; padding: 3rem 2rem; color: var(--text-muted); }
.loading-tip { text-align: center; padding: 4rem 2rem; color: var(--text-muted); }

/* ── 创建比赛弹窗 ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center; z-index: 300;
}
.create-modal {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px;
  padding: 1.75rem; width: 820px; max-width: 96vw; max-height: 90vh;
  overflow-y: auto; display: flex; flex-direction: column; gap: 1rem;
}

.modal-steps { display: flex; align-items: center; justify-content: center; gap: 0; margin-bottom: 0.5rem; }
.mstep { display: flex; align-items: center; gap: 6px; }
.mstep-circle {
  width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 0.78rem; font-weight: 700; border: 2px solid var(--border); color: var(--text-muted); background: var(--bg-card);
}
.mstep span { font-size: 0.82rem; color: var(--text-muted); }
.mstep-line { width: 50px; height: 2px; background: var(--border); margin: 0 8px; }
.mstep-line.done { background: #22c55e; }
.mstep-active .mstep-circle { border-color: var(--accent); background: var(--accent); color: #fff; }
.mstep-active span { color: var(--text-primary); font-weight: 600; }
.mstep-done .mstep-circle { border-color: #22c55e; background: #22c55e; color: #fff; }

.mform-group { display: flex; flex-direction: column; gap: 0.3rem; }
.mform-group label { font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); }
.req { color: #ef4444; }
.mform-input {
  background: var(--bg-input); border: 1px solid var(--border); border-radius: 7px;
  padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--text-primary);
  outline: none; width: 100%; box-sizing: border-box; font-family: inherit;
}
.mform-input:focus { border-color: var(--accent); }
.mform-input.error { border-color: #ef4444; }
.mform-textarea { resize: vertical; min-height: 60px; }
.mform-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.field-err { font-size: 0.75rem; color: #ef4444; }

.rule-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.rule-opt {
  border: 2px solid var(--border); border-radius: 8px; padding: 0.6rem 0.8rem;
  cursor: pointer; font-size: 0.82rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.5rem;
  transition: all 0.15s;
}
.rule-opt:hover { border-color: var(--accent); }
.rule-opt.selected { border-color: var(--accent); background: rgba(99,102,241,.06); color: var(--text-primary); }
.rule-badge { font-size: 0.68rem; font-weight: 700; padding: 1px 7px; border-radius: 8px; }
.rule-badge.icpc { background: rgba(99,102,241,.15); color: var(--accent); }
.rule-badge.ioi  { background: rgba(234,179,8,.15); color: #ca8a04; }

/* Selector */
.selector-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; min-height: 360px; }
.selector-panel { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.panel-hd { padding: 10px 12px 8px; border-bottom: 1px solid var(--border); background: var(--bg-card); display: flex; flex-direction: column; gap: 6px; }
.panel-title { font-size: 0.85rem; font-weight: 700; color: var(--text-primary); }
.diff-row { display: flex; flex-wrap: wrap; gap: 4px; }
.diff-chip { padding: 2px 8px; border-radius: 20px; font-size: 0.68rem; font-weight: 500; cursor: pointer; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text-muted); transition: all 0.15s; }
.diff-chip:hover, .diff-chip.active { border-color: var(--accent); background: var(--accent); color: #fff; }
.search-input { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 6px; padding: 5px 9px; font-size: 0.78rem; color: var(--text-primary); outline: none; width: 100%; box-sizing: border-box; }
.search-input:focus { border-color: var(--accent); }
.panel-body { flex: 1; overflow-y: auto; padding: 4px 0; }
.pool-item { display: flex; align-items: center; padding: 7px 10px; gap: 8px; border-bottom: 1px solid var(--border); }
.pool-item:last-child { border-bottom: none; }
.pool-item.added { opacity: 0.35; pointer-events: none; }
.selected-item { display: flex; align-items: center; padding: 7px 10px; gap: 8px; border-bottom: 1px solid var(--border); }
.selected-item:last-child { border-bottom: none; }
.prob-info { flex: 1; min-width: 0; }
.prob-title-s { font-size: 0.82rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-primary); }
.diff-badge { font-size: 0.65rem; font-weight: 600; padding: 1px 6px; border-radius: 8px; }
.sel-order { width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 0.68rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.arrows { display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }
.arrow-btn { width: 20px; height: 16px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-muted); border-radius: 3px; cursor: pointer; font-size: 0.6rem; display: flex; align-items: center; justify-content: center; }
.arrow-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.arrow-btn:disabled { opacity: 0.25; cursor: not-allowed; }
.btn-add { flex-shrink: 0; padding: 3px 8px; border-radius: 5px; font-size: 0.72rem; font-weight: 600; cursor: pointer; border: none; background: var(--accent); color: #fff; }
.btn-add:disabled { background: var(--bg-input); color: var(--text-muted); cursor: default; }
.btn-remove { flex-shrink: 0; padding: 3px 8px; border-radius: 5px; font-size: 0.72rem; font-weight: 600; cursor: pointer; border: none; background: rgba(239,68,68,.12); color: #ef4444; }
.panel-ft { padding: 5px 10px; border-top: 1px solid var(--border); background: var(--bg-card); display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 0.75rem; color: var(--text-muted); }
.pager-btn { padding: 2px 7px; border-radius: 4px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text-muted); cursor: pointer; font-size: 0.72rem; }
.pager-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.create-err { color: #ef4444; font-size: 0.82rem; }

.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 600; transition: opacity 0.15s; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-secondary { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
</style>
