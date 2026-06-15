<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getTeam, updateTeam, resetInviteCode,
  getMembers, updateMember, removeMember,
  getRequests, approveRequest, rejectRequest, batchApprove,
  setContestPerm,
  searchStudent, addStudent, importTemplate, importStudents,
  getAnnouncements, createAnnouncement, updateAnnouncement, deleteAnnouncement,
  getAssignments, createAssignment, updateAssignment, deleteAssignment,
} from '@/api/team'
import { getQuestions } from '@/api/questions'

const route = useRoute()
const router = useRouter()
const teamId = Number(route.params.id)

const team = ref(null)
const members = ref([])
const requests = ref([])
const canManage = ref(false)   // false = 队长只读模式
const activeTab = ref('members')   // 'members' | 'requests' | 'add' | 'announcements' | 'assignments'
const loading = ref(false)
const msgBox = ref('')   // 操作反馈

// ── 申请审核 ─────────────────────────────────────────────────────
const selectedIds = ref(new Set())
const rejectModal = ref(false)
const rejectTarget = ref(null)
const rejectReason = ref('')

// ── 成员操作 ─────────────────────────────────────────────────────
const editModal = ref(false)
const editTarget = ref(null)
const editRemark = ref('')

// ── 重置邀请码 ────────────────────────────────────────────────────
const resetting = ref(false)

// ── 添加学生 ─────────────────────────────────────────────────────
const searchQ = ref('')
const searchResults = ref([])
const searching = ref(false)
const addingId = ref(null)   // 正在添加的 user_id

// Excel 导入
const importing = ref(false)
const importReport = ref(null)
const fileInput = ref(null)

async function doSearch() {
  if (!searchQ.value.trim()) { searchResults.value = []; return }
  searching.value = true
  try {
    const { data } = await searchStudent(teamId, searchQ.value.trim())
    searchResults.value = data
  } finally {
    searching.value = false
  }
}

async function doAddStudent(u) {
  if (u.already_member) return
  addingId.value = u.user_id
  try {
    const { data } = await addStudent(teamId, { user_id: u.user_id })
    members.value.push(data)
    if (team.value) team.value.member_count++
    u.already_member = true
    flash(`已添加 ${data.display_name}`)
  } catch (e) {
    flash(e.response?.data?.detail || '添加失败')
  } finally {
    addingId.value = null
  }
}

function downloadTemplate() {
  // 带 token 跳转下载
  const token = localStorage.getItem('access_token')
  const a = document.createElement('a')
  a.href = `/api/teams/${teamId}/import-template/`
  a.download = `import_template_${teamId}.xlsx`
  // 用 fetch 带鉴权下载
  fetch(a.href, { headers: { Authorization: `Bearer ${token}` } })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob)
      a.href = url
      a.click()
      URL.revokeObjectURL(url)
    })
}

async function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  importing.value = true
  importReport.value = null
  try {
    const form = new FormData()
    form.append('file', file)
    const { data } = await importStudents(teamId, form)
    importReport.value = data
    // 刷新成员列表
    const { data: ml } = await getMembers(teamId)
    members.value = ml
    if (team.value) team.value.member_count = ml.length
    flash(`导入完成：成功 ${data.success} / 已存在 ${data.already_member} / 失败 ${data.failed}`)
  } catch (e) {
    flash(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

// ── 公告 ─────────────────────────────────────────────────────────
const announcements = ref([])
const annModal = ref(false)
const annEdit = ref(null)   // null = 新建，否则为编辑对象
const annForm = ref({ title: '', content: '', is_pinned: false })

async function loadAnnouncements() {
  const { data } = await getAnnouncements(teamId)
  announcements.value = data
}

function openAnnModal(a = null) {
  annEdit.value = a
  annForm.value = a
    ? { title: a.title, content: a.content, is_pinned: a.is_pinned }
    : { title: '', content: '', is_pinned: false }
  annModal.value = true
}

async function saveAnn() {
  if (!annForm.value.title.trim()) return
  if (annEdit.value) {
    const { data } = await updateAnnouncement(teamId, annEdit.value.id, annForm.value)
    const idx = announcements.value.findIndex(a => a.id === data.id)
    if (idx >= 0) announcements.value[idx] = data
  } else {
    const { data } = await createAnnouncement(teamId, annForm.value)
    announcements.value.unshift(data)
  }
  annModal.value = false
  flash(annEdit.value ? '公告已更新' : '公告已发布')
}

async function deleteAnn(a) {
  if (!confirm(`删除公告「${a.title}」？`)) return
  await deleteAnnouncement(teamId, a.id)
  announcements.value = announcements.value.filter(x => x.id !== a.id)
  flash('已删除')
}

async function togglePin(a) {
  const { data } = await updateAnnouncement(teamId, a.id, { is_pinned: !a.is_pinned })
  const idx = announcements.value.findIndex(x => x.id === data.id)
  if (idx >= 0) announcements.value[idx] = data
}

// ── 作业 / 考试 ───────────────────────────────────────────────────
const ASGN_CATEGORIES = [
  { value: 'practice', label: '练习' },
  { value: 'homework', label: '作业' },
  { value: 'exam', label: '考试' },
]
const assignments = ref([])
const asgnModal = ref(false)
const asgnEdit = ref(null)
const problemSearch = ref('')
const problemResults = ref([])
const problemSearching = ref(false)
const questionSearch = ref('')
const questionResults = ref([])
const questionSearching = ref(false)

function blankAsgnForm() {
  return {
    title: '', description: '', category: 'homework',
    deadline: '', start_time: '', end_time: '', duration_minutes: 0,
    shuffle: false, track_focus: false, hide_rank: false,
    is_active: true,
    problems: [],   // [{ id, title, difficulty, score }]
    questions: [],  // [{ id, title, qtype, qtype_display, score }]
  }
}
const asgnForm = ref(blankAsgnForm())
const asgnTotalScore = computed(() =>
  asgnForm.value.problems.reduce((s, p) => s + (Number(p.score) || 0), 0) +
  asgnForm.value.questions.reduce((s, q) => s + (Number(q.score) || 0), 0)
)

async function loadAssignments() {
  const { data } = await getAssignments(teamId)
  assignments.value = data
}

function dtLocal(s) { return s ? s.slice(0, 16) : '' }

function openAsgnModal(a = null) {
  asgnEdit.value = a
  if (a) {
    asgnForm.value = {
      title: a.title,
      description: a.description,
      category: a.category || 'homework',
      deadline: dtLocal(a.deadline),
      start_time: dtLocal(a.start_time),
      end_time: dtLocal(a.end_time),
      duration_minutes: a.duration_minutes || 0,
      shuffle: !!a.shuffle,
      track_focus: !!a.track_focus,
      hide_rank: !!a.hide_rank,
      is_active: a.is_active,
      problems: (a.problems || []).map(p => ({ id: p.id, title: p.title, difficulty: p.difficulty, score: p.score ?? 10 })),
      questions: (a.questions || []).map(q => ({ id: q.id, title: q.title, qtype: q.qtype, qtype_display: q.qtype_display, score: q.score ?? 5 })),
    }
  } else {
    asgnForm.value = blankAsgnForm()
  }
  problemResults.value = []
  questionResults.value = []
  problemSearch.value = ''
  questionSearch.value = ''
  asgnModal.value = true
}

async function searchProblems() {
  if (!problemSearch.value.trim()) return
  problemSearching.value = true
  try {
    const { default: api } = await import('@/api/index')
    const { data } = await api.get('/problems/', { params: { search: problemSearch.value, limit: 10, is_published: true } })
    const ids = new Set(asgnForm.value.problems.map(p => p.id))
    problemResults.value = (data.results || data).filter(p => !ids.has(p.id)).slice(0, 8)
  } finally {
    problemSearching.value = false
  }
}

async function searchQuestions() {
  if (!questionSearch.value.trim()) return
  questionSearching.value = true
  try {
    const { data } = await getQuestions({ q: questionSearch.value.trim(), is_published: 'true', page_size: 8 })
    const ids = new Set(asgnForm.value.questions.map(q => q.id))
    questionResults.value = (data.results || []).filter(q => !ids.has(q.id))
  } finally {
    questionSearching.value = false
  }
}

function addProblemToAssignment(p) {
  if (asgnForm.value.problems.some(x => x.id === p.id)) return
  asgnForm.value.problems.push({ id: p.id, title: p.title, difficulty: p.difficulty, score: 10 })
  problemResults.value = problemResults.value.filter(x => x.id !== p.id)
}
function removeProblemFromAssignment(pid) {
  asgnForm.value.problems = asgnForm.value.problems.filter(p => p.id !== pid)
}
function addQuestionToAssignment(q) {
  if (asgnForm.value.questions.some(x => x.id === q.id)) return
  asgnForm.value.questions.push({ id: q.id, title: q.title, qtype: q.qtype, qtype_display: q.qtype_display, score: 5 })
  questionResults.value = questionResults.value.filter(x => x.id !== q.id)
}
function removeQuestionFromAssignment(qid) {
  asgnForm.value.questions = asgnForm.value.questions.filter(q => q.id !== qid)
}

async function saveAssignment() {
  const f = asgnForm.value
  if (!f.title.trim()) return
  const payload = {
    title: f.title.trim(),
    description: f.description,
    category: f.category,
    deadline: f.deadline || null,
    is_active: f.is_active,
    problems: f.problems.map(p => ({ id: p.id, score: Number(p.score) || 0 })),
    questions: f.questions.map(q => ({ id: q.id, score: Number(q.score) || 0 })),
  }
  if (f.category === 'exam') {
    payload.start_time = f.start_time || null
    payload.end_time = f.end_time || null
    payload.duration_minutes = Number(f.duration_minutes) || 0
    payload.shuffle = f.shuffle
    payload.track_focus = f.track_focus
    payload.hide_rank = f.hide_rank
  }
  if (asgnEdit.value) {
    const { data } = await updateAssignment(teamId, asgnEdit.value.id, payload)
    const idx = assignments.value.findIndex(a => a.id === data.id)
    if (idx >= 0) assignments.value[idx] = data
  } else {
    const { data } = await createAssignment(teamId, payload)
    assignments.value.unshift(data)
  }
  asgnModal.value = false
  flash(asgnEdit.value ? '已保存' : '已创建')
}

async function deleteAsgn(a) {
  if (!confirm(`删除作业「${a.title}」？`)) return
  await deleteAssignment(teamId, a.id)
  assignments.value = assignments.value.filter(x => x.id !== a.id)
  flash('已删除')
}

async function load() {
  loading.value = true
  try {
    const [td, ml] = await Promise.all([getTeam(teamId), getMembers(teamId)])
    team.value = td.data
    canManage.value = !!td.data.can_manage
    members.value = ml.data.members ?? ml.data   // 兼容旧格式
  } finally {
    loading.value = false
  }
}

async function loadRequests() {
  const { data } = await getRequests(teamId, 'pending')
  requests.value = data
}

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'requests') loadRequests()
  if (tab === 'announcements') loadAnnouncements()
  if (tab === 'assignments') loadAssignments()
}

// ── 操作：成员 ────────────────────────────────────────────────────
function openEdit(ms) {
  editTarget.value = ms
  editRemark.value = ms.remark
  editModal.value = true
}

async function saveRemark() {
  await updateMember(teamId, editTarget.value.user_id, { remark: editRemark.value })
  editTarget.value.remark = editRemark.value
  editModal.value = false
  flash('备注已保存')
}

async function toggleCaptain(ms) {
  const newRole = ms.role === 'captain' ? 'member' : 'captain'
  if (newRole === 'captain' && !confirm(`将 ${ms.display_name} 设为队长？（每团队仅一名）`)) return
  await updateMember(teamId, ms.user_id, { role: newRole })
  // 本地更新
  members.value.forEach(m => { if (m.role === 'captain') m.role = 'member' })
  ms.role = newRole
  flash(newRole === 'captain' ? `已设 ${ms.display_name} 为队长` : '已取消队长身份')
}

async function toggleAssistant(ms) {
  const target = ms.role === 'assistant' ? 'member' : 'assistant'
  await updateMember(teamId, ms.user_id, { role: target })
  ms.role = target
  flash(target === 'assistant' ? `已设 ${ms.display_name} 为助教` : '已取消助教身份')
}

async function doRemove(ms) {
  if (!confirm(`确定移除 ${ms.display_name}？`)) return
  await removeMember(teamId, ms.user_id)
  members.value = members.value.filter(m => m.user_id !== ms.user_id)
  if (team.value) team.value.member_count--
  flash('已移除')
}

// ── 操作：申请 ────────────────────────────────────────────────────
function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selectedIds.value = s
}

function toggleAll() {
  if (selectedIds.value.size === requests.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(requests.value.map(r => r.id))
  }
}

async function doApprove(req) {
  await approveRequest(teamId, req.id)
  requests.value = requests.value.filter(r => r.id !== req.id)
  if (team.value) team.value.pending_count = Math.max(0, (team.value.pending_count || 0) - 1)
  flash('已通过')
}

async function doBatchApprove() {
  if (selectedIds.value.size === 0) return
  const { data } = await batchApprove(teamId, [...selectedIds.value])
  requests.value = requests.value.filter(r => !selectedIds.value.has(r.id))
  selectedIds.value = new Set()
  if (team.value) team.value.pending_count = requests.value.length
  flash(`已批量通过 ${data.success} 人`)
}

function openReject(req) {
  rejectTarget.value = req
  rejectReason.value = ''
  rejectModal.value = true
}

async function doReject() {
  await rejectRequest(teamId, rejectTarget.value.id, rejectReason.value)
  requests.value = requests.value.filter(r => r.id !== rejectTarget.value.id)
  if (team.value) team.value.pending_count = Math.max(0, (team.value.pending_count || 0) - 1)
  rejectModal.value = false
  flash('已拒绝')
}

// ── 重置邀请码 ────────────────────────────────────────────────────
async function doResetCode() {
  if (!confirm('重置后旧邀请码立即失效，确定？')) return
  resetting.value = true
  try {
    const { data } = await resetInviteCode(teamId)
    team.value.invite_code = data.invite_code
    flash('邀请码已重置')
  } finally {
    resetting.value = false
  }
}

function copyCode() {
  navigator.clipboard.writeText(team.value?.invite_code || '').catch(() => {})
  flash('已复制')
}

async function toggleContestPerm(ms) {
  const next = !ms.can_create_contest
  await setContestPerm(ms.user_id, next)
  ms.can_create_contest = next
  flash(next ? `已授权 ${ms.display_name} 创建比赛` : `已撤销 ${ms.display_name} 的创建比赛权限`)
}

function flash(msg) {
  msgBox.value = msg
  setTimeout(() => { msgBox.value = '' }, 2500)
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleDateString('zh-CN') : ''
}

function catLabel(c) {
  return ({ practice: '练习', homework: '作业', exam: '考试' })[c] || '作业'
}

onMounted(load)
</script>

<template>
  <div class="team-detail" v-if="team">
    <!-- 顶部 -->
    <div class="detail-header">
      <button class="btn-back" @click="router.push('/teacher')">← 返回</button>
      <div class="header-info">
        <h1 class="team-name">{{ team.name }}</h1>
        <p v-if="team.description" class="team-desc">{{ team.description }}</p>
      </div>
      <button class="btn-dashboard" @click="router.push(`/teacher/teams/${teamId}/dashboard`)">
        查看总览 →
      </button>
    </div>

    <!-- 邀请码栏（仅教师可见） -->
    <div v-if="canManage" class="invite-bar">
      <span class="ib-label">邀请码</span>
      <code class="ib-code">{{ team.invite_code }}</code>
      <button class="btn-sm" @click="copyCode">复制</button>
      <button class="btn-sm btn-warn" :disabled="resetting" @click="doResetCode">
        {{ resetting ? '…' : '重置' }}
      </button>
      <span class="ib-stat">{{ team.member_count }} 人</span>
      <span v-if="team.pending_count > 0" class="badge-pending">{{ team.pending_count }} 待审</span>
    </div>
    <!-- 队长简要状态栏 -->
    <div v-else class="invite-bar">
      <span class="ib-stat">{{ team.member_count }} 人</span>
      <span class="ib-label" style="margin-left:auto;">只读模式（队长）</span>
    </div>

    <!-- 操作反馈 -->
    <Transition name="fade">
      <div v-if="msgBox" class="msg-box">{{ msgBox }}</div>
    </Transition>

    <!-- Tab -->
    <div class="tabs">
      <button :class="['tab', activeTab === 'members' && 'tab-active']" @click="switchTab('members')">
        成员列表（{{ members.length }}）
      </button>
      <template v-if="canManage">
        <button :class="['tab', activeTab === 'requests' && 'tab-active']" @click="switchTab('requests')">
          加入申请
          <span v-if="team.pending_count > 0" class="tab-badge">{{ team.pending_count }}</span>
        </button>
        <button :class="['tab', activeTab === 'add' && 'tab-active']" @click="switchTab('add')">
          添加学生
        </button>
        <button :class="['tab', activeTab === 'announcements' && 'tab-active']" @click="switchTab('announcements')">
          公告
        </button>
        <button :class="['tab', activeTab === 'assignments' && 'tab-active']" @click="switchTab('assignments')">
          作业
        </button>
      </template>
    </div>

    <!-- ── 成员列表 Tab ── -->
    <div v-if="activeTab === 'members'">
      <div v-if="members.length === 0" class="empty-tip">暂无成员</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>备注（姓名）</th><th>用户名</th><th>学号</th><th>专业/年级</th>
              <th>角色</th><th>加入时间</th><th v-if="canManage">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ms in members" :key="ms.user_id">
              <td>
                <span class="display-name">{{ ms.display_name }}</span>
                <span v-if="ms.role === 'captain'" class="crown" title="队长">👑</span>
              </td>
              <td class="text-muted">{{ ms.username }}</td>
              <td class="text-muted">{{ ms.student_id || '—' }}</td>
              <td class="text-muted">{{ [ms.major, ms.grade].filter(Boolean).join(' / ') || '—' }}</td>
              <td>
                <span :class="['role-tag', ms.role === 'captain' ? 'role-captain' : (ms.role === 'assistant' ? 'role-ta' : 'role-member')]">
                  {{ ms.role === 'captain' ? '队长' : (ms.role === 'assistant' ? '助教' : '队员') }}
                </span>
              </td>
              <td class="text-muted">{{ fmt(ms.joined_at) }}</td>
              <td v-if="canManage" class="actions-cell">
                <button class="btn-xs" @click="openEdit(ms)">改备注</button>
                <button class="btn-xs" @click="toggleCaptain(ms)">
                  {{ ms.role === 'captain' ? '取消队长' : '设队长' }}
                </button>
                <button class="btn-xs" @click="toggleAssistant(ms)">
                  {{ ms.role === 'assistant' ? '取消助教' : '设助教' }}
                </button>
                <button
                  class="btn-xs"
                  :class="ms.can_create_contest ? 'btn-perm-on' : 'btn-perm-off'"
                  :title="ms.can_create_contest ? '撤销创建比赛权限' : '授予创建比赛权限'"
                  @click="toggleContestPerm(ms)"
                >{{ ms.can_create_contest ? '✓ 可建赛' : '建赛权限' }}</button>
                <button class="btn-xs btn-danger" @click="doRemove(ms)">移除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── 申请审核 Tab ── -->
    <div v-if="activeTab === 'requests'">
      <div class="req-toolbar" v-if="requests.length > 0">
        <label class="check-all">
          <input type="checkbox" :checked="selectedIds.size === requests.length" @change="toggleAll" />
          全选
        </label>
        <button class="btn-sm btn-primary" :disabled="selectedIds.size === 0" @click="doBatchApprove">
          批量通过（{{ selectedIds.size }}）
        </button>
      </div>
      <div v-if="requests.length === 0" class="empty-tip">暂无待审核申请</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:2.5rem"></th>
              <th>申请人</th><th>学号</th><th>申请备注</th><th>申请时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in requests" :key="req.id">
              <td>
                <input type="checkbox" :checked="selectedIds.has(req.id)" @change="toggleSelect(req.id)" />
              </td>
              <td>{{ req.username }}<span v-if="req.real_name" class="text-muted">（{{ req.real_name }}）</span></td>
              <td class="text-muted">{{ req.student_id || '—' }}</td>
              <td class="req-remark">{{ req.remark }}</td>
              <td class="text-muted">{{ fmt(req.created_at) }}</td>
              <td class="actions-cell">
                <button class="btn-xs btn-success" @click="doApprove(req)">通过</button>
                <button class="btn-xs btn-danger" @click="openReject(req)">拒绝</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <!-- ── 添加学生 Tab ── -->
    <div v-if="activeTab === 'add'" class="add-section">

      <!-- 搜索直接添加 -->
      <div class="add-card">
        <h3 class="add-card-title">按学号 / 用户名搜索</h3>
        <div class="search-row">
          <input
            v-model="searchQ"
            class="form-input"
            placeholder="输入学号或用户名…"
            @keyup.enter="doSearch"
          />
          <button class="btn-primary add-search-btn" :disabled="searching" @click="doSearch">
            {{ searching ? '搜索中…' : '搜索' }}
          </button>
        </div>
        <div v-if="searchResults.length > 0" class="search-result-list">
          <div v-for="u in searchResults" :key="u.user_id" class="search-result-row">
            <div class="sr-info">
              <span class="sr-name">{{ u.real_name || u.username }}</span>
              <span class="sr-meta text-muted">{{ u.username }} · {{ u.student_id || '无学号' }}</span>
            </div>
            <span v-if="u.already_member" class="sr-tag-in">已在团队</span>
            <button
              v-else
              class="btn-xs btn-success"
              :disabled="addingId === u.user_id"
              @click="doAddStudent(u)"
            >{{ addingId === u.user_id ? '添加中…' : '添加' }}</button>
          </div>
        </div>
        <p v-else-if="searchQ && !searching" class="empty-tip" style="padding: 0.5rem 0">未找到匹配用户</p>
      </div>

      <!-- Excel 批量导入 -->
      <div class="add-card">
        <h3 class="add-card-title">Excel 批量导入</h3>
        <p class="add-card-hint">按模板填写学号列，系统自动匹配或创建账号（初始密码=学号，首次登录需改密）</p>
        <div class="import-row">
          <button class="btn-secondary" @click="downloadTemplate">↓ 下载模板</button>
          <label class="btn-primary import-label" :class="{ disabled: importing }">
            {{ importing ? '导入中…' : '选择文件并导入' }}
            <input
              ref="fileInput"
              type="file"
              accept=".xlsx,.xls"
              style="display:none"
              :disabled="importing"
              @change="onFileChange"
            />
          </label>
        </div>

        <!-- 导入结果报告 -->
        <div v-if="importReport" class="import-report">
          <div class="ir-summary">
            <span class="ir-ok">✓ 成功 {{ importReport.success }}</span>
            <span class="ir-skip">↺ 已在团队 {{ importReport.already_member }}</span>
            <span class="ir-fail">✗ 失败 {{ importReport.failed }}</span>
          </div>
          <div v-if="importReport.errors?.length > 0" class="ir-errors">
            <div v-for="(e, i) in importReport.errors" :key="i" class="ir-error-row">
              第 {{ e.row }} 行（{{ e.student_id }}）：{{ e.reason }}
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ── 公告 Tab ── -->
    <div v-if="activeTab === 'announcements'" class="ann-section">
      <div class="ann-toolbar">
        <button class="btn-primary btn-sm-solid" @click="openAnnModal()">+ 发布公告</button>
      </div>
      <div v-if="announcements.length === 0" class="empty-tip">暂无公告</div>
      <div v-else class="ann-list">
        <div v-for="a in announcements" :key="a.id" class="ann-card">
          <div class="ann-head">
            <span class="ann-pin" v-if="a.is_pinned" title="已置顶">📌</span>
            <span class="ann-title">{{ a.title }}</span>
            <div class="ann-actions">
              <button class="btn-xs" @click="togglePin(a)">{{ a.is_pinned ? '取消置顶' : '置顶' }}</button>
              <button class="btn-xs" @click="openAnnModal(a)">编辑</button>
              <button class="btn-xs btn-danger" @click="deleteAnn(a)">删除</button>
            </div>
          </div>
          <p v-if="a.content" class="ann-content">{{ a.content }}</p>
          <div class="ann-meta text-muted">{{ a.created_by }} · {{ fmt(a.created_at) }}</div>
        </div>
      </div>
    </div>

    <!-- ── 作业 Tab ── -->
    <div v-if="activeTab === 'assignments'" class="asgn-section">
      <div class="asgn-toolbar">
        <button class="btn-primary btn-sm-solid" @click="openAsgnModal()">+ 创建作业</button>
      </div>
      <div v-if="assignments.length === 0" class="empty-tip">暂无作业</div>
      <div v-else class="asgn-list">
        <div v-for="a in assignments" :key="a.id" class="asgn-card">
          <div class="asgn-head">
            <div class="asgn-info">
              <span :class="['asgn-cat', 'cat-' + (a.category || 'homework')]">{{ catLabel(a.category) }}</span>
              <span class="asgn-title">{{ a.title }}</span>
              <span v-if="!a.is_active" class="asgn-draft">草稿</span>
            </div>
            <div class="asgn-actions">
              <button v-if="canManage" class="btn-xs" @click="router.push(`/teacher/assignments/${a.id}/gradebook`)">成绩</button>
              <button class="btn-xs" @click="openAsgnModal(a)">编辑</button>
              <button class="btn-xs btn-danger" @click="deleteAsgn(a)">删除</button>
            </div>
          </div>
          <p v-if="a.description" class="asgn-desc text-muted">{{ a.description }}</p>
          <div class="asgn-footer text-muted">
            <span>{{ a.problem_count }} 编程 · {{ a.question_count || 0 }} 客观</span>
            <span> · 满分 {{ a.total_score ?? 0 }}</span>
            <span v-if="a.category === 'exam' && a.start_time"> · 开考 {{ fmt(a.start_time) }}</span>
            <span v-else-if="a.deadline"> · 截止 {{ fmt(a.deadline) }}</span>
            <span> · {{ a.created_by }}</span>
          </div>
        </div>
      </div>
    </div>

  </div>

  <div v-else-if="loading" class="loading-tip">加载中…</div>

  <!-- 公告弹窗 -->
  <div v-if="annModal" class="modal-overlay" @click.self="annModal = false">
    <div class="modal modal-wide">
      <h2 class="modal-title">{{ annEdit ? '编辑公告' : '发布公告' }}</h2>
      <input v-model="annForm.title" class="form-input" placeholder="公告标题" maxlength="200" />
      <textarea v-model="annForm.content" class="form-textarea" placeholder="公告内容（可选，支持换行）" rows="5"></textarea>
      <label class="check-label">
        <input type="checkbox" v-model="annForm.is_pinned" />
        置顶此公告
      </label>
      <div class="modal-actions">
        <button class="btn-secondary" @click="annModal = false">取消</button>
        <button class="btn-primary" :disabled="!annForm.title.trim()" @click="saveAnn">
          {{ annEdit ? '保存' : '发布' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 作业 / 考试弹窗 -->
  <div v-if="asgnModal" class="modal-overlay" @click.self="asgnModal = false">
    <div class="modal modal-wide">
      <h2 class="modal-title">{{ asgnEdit ? '编辑' : '创建' }}{{ catLabel(asgnForm.category) }}</h2>

      <div class="form-row">
        <label class="form-label">类型</label>
        <div class="cat-pills">
          <button
            v-for="c in ASGN_CATEGORIES" :key="c.value"
            :class="['pill', asgnForm.category === c.value && 'pill-on']"
            @click="asgnForm.category = c.value"
          >{{ c.label }}</button>
        </div>
      </div>

      <input v-model="asgnForm.title" class="form-input" placeholder="名称" maxlength="200" />
      <textarea v-model="asgnForm.description" class="form-textarea" placeholder="说明（可选）" rows="2"></textarea>

      <!-- 非考试：截止时间 -->
      <div v-if="asgnForm.category !== 'exam'" class="form-row">
        <label class="form-label">截止时间（可选）</label>
        <input v-model="asgnForm.deadline" type="datetime-local" class="form-input" />
      </div>

      <!-- 考试配置 -->
      <div v-else class="exam-config">
        <div class="exam-grid">
          <div class="form-row">
            <label class="form-label">开始时间</label>
            <input v-model="asgnForm.start_time" type="datetime-local" class="form-input" />
          </div>
          <div class="form-row">
            <label class="form-label">结束时间</label>
            <input v-model="asgnForm.end_time" type="datetime-local" class="form-input" />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">个人限时（分钟，0 = 用整个窗口）</label>
          <input v-model.number="asgnForm.duration_minutes" type="number" min="0" class="form-input" />
        </div>
        <div class="exam-flags">
          <label class="check-label"><input type="checkbox" v-model="asgnForm.shuffle" /> 打乱题序</label>
          <label class="check-label"><input type="checkbox" v-model="asgnForm.hide_rank" /> 隐藏排名/他人</label>
          <label class="check-label"><input type="checkbox" v-model="asgnForm.track_focus" /> 记录切屏</label>
        </div>
      </div>

      <label class="check-label">
        <input type="checkbox" v-model="asgnForm.is_active" />
        立即发布（取消则保存为草稿）
      </label>

      <!-- 编程题 -->
      <div class="pick-section">
        <div class="pick-head">编程题（{{ asgnForm.problems.length }}）</div>
        <div class="search-row">
          <input v-model="problemSearch" class="form-input" placeholder="搜索题目标题或 ID…" @keyup.enter="searchProblems" />
          <button class="btn-primary add-search-btn" :disabled="problemSearching" @click="searchProblems">{{ problemSearching ? '…' : '搜索' }}</button>
        </div>
        <div v-if="problemResults.length > 0" class="search-result-list">
          <div v-for="p in problemResults" :key="p.id" class="search-result-row">
            <div class="sr-info"><span class="sr-name">#{{ p.id }} {{ p.title }}</span><span class="sr-meta text-muted">{{ p.difficulty }}</span></div>
            <button class="btn-xs btn-success" @click="addProblemToAssignment(p)">添加</button>
          </div>
        </div>
        <div v-for="p in asgnForm.problems" :key="p.id" class="picked-row">
          <span class="pk-tag prob">#{{ p.id }}</span>
          <span class="pk-title">{{ p.title }}</span>
          <input v-model.number="p.score" type="number" min="0" class="pk-score" title="分值" />
          <button class="btn-xs btn-danger" @click="removeProblemFromAssignment(p.id)">✕</button>
        </div>
      </div>

      <!-- 客观题 -->
      <div class="pick-section">
        <div class="pick-head">客观题（{{ asgnForm.questions.length }}）</div>
        <div class="search-row">
          <input v-model="questionSearch" class="form-input" placeholder="搜索客观题题干…" @keyup.enter="searchQuestions" />
          <button class="btn-primary add-search-btn" :disabled="questionSearching" @click="searchQuestions">{{ questionSearching ? '…' : '搜索' }}</button>
        </div>
        <div v-if="questionResults.length > 0" class="search-result-list">
          <div v-for="q in questionResults" :key="q.id" class="search-result-row">
            <div class="sr-info"><span class="sr-name">{{ q.title }}</span><span class="sr-meta text-muted">{{ q.qtype_display }} · {{ q.difficulty }}</span></div>
            <button class="btn-xs btn-success" @click="addQuestionToAssignment(q)">添加</button>
          </div>
        </div>
        <p v-if="!asgnForm.questions.length && !questionResults.length" class="pick-hint text-muted">
          客观题来自<a class="pick-link" @click="router.push('/teacher/questions')">题库</a>，需先在题库创建并发布
        </p>
        <div v-for="q in asgnForm.questions" :key="q.id" class="picked-row">
          <span class="pk-tag ques">{{ q.qtype_display || q.qtype }}</span>
          <span class="pk-title">{{ q.title }}</span>
          <input v-model.number="q.score" type="number" min="0" class="pk-score" title="分值" />
          <button class="btn-xs btn-danger" @click="removeQuestionFromAssignment(q.id)">✕</button>
        </div>
      </div>

      <div class="total-bar">满分合计：<strong>{{ asgnTotalScore }}</strong> 分</div>

      <div class="modal-actions">
        <button class="btn-secondary" @click="asgnModal = false">取消</button>
        <button class="btn-primary" :disabled="!asgnForm.title.trim()" @click="saveAssignment">
          {{ asgnEdit ? '保存' : '创建' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 改备注弹窗 -->
  <div v-if="editModal" class="modal-overlay" @click.self="editModal = false">
    <div class="modal">
      <h2 class="modal-title">修改备注</h2>
      <p class="modal-sub">{{ editTarget?.display_name }}（{{ editTarget?.username }}）</p>
      <input v-model="editRemark" class="form-input" placeholder="团队内备注（如：张三）" maxlength="50" />
      <div class="modal-actions">
        <button class="btn-secondary" @click="editModal = false">取消</button>
        <button class="btn-primary" @click="saveRemark">保存</button>
      </div>
    </div>
  </div>

  <!-- 拒绝弹窗 -->
  <div v-if="rejectModal" class="modal-overlay" @click.self="rejectModal = false">
    <div class="modal">
      <h2 class="modal-title">拒绝申请</h2>
      <p class="modal-sub">{{ rejectTarget?.username }} 的申请备注：<em>{{ rejectTarget?.remark }}</em></p>
      <input v-model="rejectReason" class="form-input" placeholder="拒绝理由（可选）" maxlength="200" />
      <div class="modal-actions">
        <button class="btn-secondary" @click="rejectModal = false">取消</button>
        <button class="btn-danger-solid" @click="doReject">确认拒绝</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.team-detail { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }

/* Header */
.detail-header { display: flex; align-items: flex-start; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; transition: border-color 0.15s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.header-info { flex: 1; }
.team-name { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.25rem; }
.team-desc { color: var(--text-muted); font-size: 0.875rem; margin: 0; }
.btn-dashboard {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0;
}
.btn-dashboard:hover { border-color: var(--accent); color: var(--accent); }

/* Invite bar */
.invite-bar {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 0.75rem 1rem;
}
.ib-label { font-size: 0.8rem; color: var(--text-muted); }
.ib-code { font-family: 'JetBrains Mono', monospace; font-size: 1rem; color: var(--accent); letter-spacing: 0.12em; }
.ib-stat { margin-left: auto; font-size: 0.85rem; color: var(--text-muted); }
.badge-pending {
  background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44;
  border-radius: 12px; padding: 0.1rem 0.6rem; font-size: 0.75rem; font-weight: 600;
}

/* Msg */
.msg-box {
  background: #10b98122; border: 1px solid #10b98166; color: #10b981;
  border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.875rem; text-align: center;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Tabs */
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

/* Table */
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th {
  text-align: left; padding: 0.6rem 0.75rem;
  color: var(--text-muted); font-weight: 500; border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.data-table td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.data-table tr:last-child td { border-bottom: none; }
.text-muted { color: var(--text-muted); }
.display-name { color: var(--text-primary); font-weight: 500; }
.crown { margin-left: 0.25rem; }
.role-tag { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 10px; font-size: 0.75rem; }
.role-captain { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; }
.role-member { background: rgba(100,100,100,0.1); color: var(--text-muted); border: 1px solid var(--border); }
.role-ta { background: rgba(99,102,241,0.12); color: var(--accent); border: 1px solid rgba(99,102,241,0.3); }
.req-remark { color: var(--text-primary); max-width: 200px; word-break: break-word; }
.actions-cell { display: flex; gap: 0.4rem; flex-wrap: nowrap; }

/* Toolbar */
.req-toolbar { display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0; }
.check-all { display: flex; align-items: center; gap: 0.4rem; font-size: 0.875rem; color: var(--text-secondary); cursor: pointer; }

/* Buttons */
.btn-sm {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.25rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
  transition: border-color 0.15s;
}
.btn-sm:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm:disabled { opacity: 0.4; cursor: default; }
.btn-warn { border-color: #f5972244; color: #f59e0b; }
.btn-warn:hover { border-color: #f59e0b; }

.btn-xs {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem;
  white-space: nowrap; transition: border-color 0.15s;
}
.btn-xs:hover { border-color: var(--accent); color: var(--accent); }
.btn-xs.btn-danger { border-color: #f8717144; color: #f87171; }
.btn-xs.btn-danger:hover { border-color: #f87171; }
.btn-xs.btn-success { border-color: #10b98144; color: #10b981; }
.btn-xs.btn-success:hover { border-color: #10b981; }
.btn-xs.btn-perm-on { border-color: #22c55e88; color: #22c55e; }
.btn-xs.btn-perm-on:hover { border-color: #22c55e; }
.btn-xs.btn-perm-off { border-color: var(--border); color: var(--text-muted); }
.btn-xs.btn-perm-off:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm.btn-primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn-sm.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 1.75rem; width: 400px; max-width: 95vw; display: flex; flex-direction: column; gap: 1rem;
}
.modal-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-sub { color: var(--text-muted); font-size: 0.875rem; margin: 0; }
.form-input {
  background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.9rem;
  width: 100%; box-sizing: border-box; transition: border-color 0.15s;
}
.form-input:focus { outline: none; border-color: var(--accent); }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-primary {
  background: var(--accent); color: #fff; border: none;
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-danger-solid {
  background: #ef4444; color: #fff; border: none;
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-danger-solid:hover { background: #dc2626; }

.loading-tip, .empty-tip { text-align: center; padding: 2rem; color: var(--text-muted); }

/* Announcement tab */
.ann-section, .asgn-section { display: flex; flex-direction: column; gap: 1rem; padding-top: 0.5rem; }
.ann-toolbar, .asgn-toolbar { display: flex; justify-content: flex-end; }
.btn-sm-solid {
  background: var(--accent); color: #fff; border: none;
  padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-sm-solid:hover { opacity: 0.85; }
.ann-list, .asgn-list { display: flex; flex-direction: column; gap: 0.75rem; }
.ann-card, .asgn-card {
  background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem;
}
.ann-head, .asgn-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
.ann-pin { font-size: 0.9rem; }
.ann-title, .asgn-title { flex: 1; font-weight: 600; color: var(--text-primary); font-size: 0.95rem; }
.ann-content {
  font-size: 0.875rem; color: var(--text-secondary); white-space: pre-wrap;
  margin: 0.3rem 0 0.5rem; line-height: 1.6;
}
.ann-meta, .asgn-footer { font-size: 0.78rem; }
.ann-actions, .asgn-actions { display: flex; gap: 0.35rem; flex-shrink: 0; }
.asgn-info { flex: 1; display: flex; align-items: center; gap: 0.5rem; }
.asgn-desc { font-size: 0.875rem; margin: 0.2rem 0 0.5rem; }
.asgn-draft {
  font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 4px;
  background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44;
}
.asgn-problems { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.6rem; }
.asgn-prob-tag {
  font-size: 0.78rem; padding: 0.15rem 0.5rem; border-radius: 4px;
  background: rgba(99,102,241,0.1); color: var(--accent); border: 1px solid rgba(99,102,241,0.25);
}

/* Modal wide */
.modal-wide { width: 520px; max-height: 90vh; overflow-y: auto; }
.form-textarea {
  background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.875rem;
  width: 100%; box-sizing: border-box; resize: vertical; font-family: inherit; line-height: 1.5;
}
.form-textarea:focus { outline: none; border-color: var(--accent); }
.form-row { display: flex; flex-direction: column; gap: 0.3rem; }
.form-label { font-size: 0.8rem; color: var(--text-secondary); }
.check-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-secondary); cursor: pointer; }
.prob-search-section { display: flex; flex-direction: column; gap: 0.5rem; border-top: 1px solid var(--border); padding-top: 0.75rem; }
.selected-problems { display: flex; flex-direction: column; gap: 0.35rem; }
.sp-label { font-size: 0.8rem; margin-bottom: 0.2rem; }
.sp-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
.sp-id { color: var(--text-muted); font-family: monospace; }
.sp-title { flex: 1; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Add-student tab */
.add-section { display: flex; flex-direction: column; gap: 1.25rem; padding-top: 0.5rem; }
.add-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
}
.add-card-title { font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.add-card-hint { font-size: 0.82rem; color: var(--text-muted); margin: 0; }
.search-row { display: flex; gap: 0.6rem; }
.add-search-btn { padding: 0.45rem 1rem; font-size: 0.875rem; border: none; border-radius: 6px; cursor: pointer; white-space: nowrap; }
.add-search-btn:disabled { opacity: 0.5; cursor: default; }
.search-result-list { display: flex; flex-direction: column; gap: 0.5rem; }
.search-result-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.5rem 0.75rem; background: var(--bg-secondary);
  border: 1px solid var(--border); border-radius: 6px;
}
.sr-info { display: flex; flex-direction: column; gap: 0.1rem; }
.sr-name { font-size: 0.875rem; color: var(--text-primary); font-weight: 500; }
.sr-meta { font-size: 0.78rem; }
.sr-tag-in { font-size: 0.78rem; color: var(--text-muted); border: 1px solid var(--border); border-radius: 4px; padding: 0.1rem 0.5rem; }
.import-row { display: flex; gap: 0.75rem; align-items: center; }
.import-label {
  display: inline-block; padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer;
  font-size: 0.875rem; user-select: none;
}
.import-label.disabled { opacity: 0.5; cursor: default; pointer-events: none; }
.import-report {
  background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 6px;
  padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem;
}
.ir-summary { display: flex; gap: 1.25rem; flex-wrap: wrap; }
.ir-ok { color: #10b981; font-size: 0.875rem; font-weight: 600; }
.ir-skip { color: #f59e0b; font-size: 0.875rem; }
.ir-fail { color: #f87171; font-size: 0.875rem; }
.ir-errors { display: flex; flex-direction: column; gap: 0.25rem; }
.ir-error-row { font-size: 0.8rem; color: #f87171; padding-left: 0.5rem; border-left: 2px solid #f87171; }

/* 作业/考试增强 */
.cat-pills { display: flex; gap: 0.5rem; }
.pill {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.3rem 0.85rem; border-radius: 20px; cursor: pointer; font-size: 0.85rem;
}
.pill:hover { border-color: var(--accent); }
.pill-on { background: var(--accent); color: #fff; border-color: var(--accent); }
.exam-config {
  background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px;
  padding: 0.85rem; display: flex; flex-direction: column; gap: 0.75rem;
}
.exam-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.exam-flags { display: flex; gap: 1.25rem; flex-wrap: wrap; }
.pick-section {
  display: flex; flex-direction: column; gap: 0.5rem;
  border-top: 1px solid var(--border); padding-top: 0.75rem;
}
.pick-head { font-size: 0.85rem; color: var(--text-secondary); font-weight: 600; }
.pick-hint { font-size: 0.8rem; margin: 0; }
.pick-link { color: var(--accent); cursor: pointer; }
.picked-row { display: flex; align-items: center; gap: 0.5rem; }
.pk-tag { font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 4px; flex-shrink: 0; white-space: nowrap; }
.pk-tag.prob { background: rgba(99,102,241,0.12); color: var(--accent); border: 1px solid rgba(99,102,241,0.3); font-family: monospace; }
.pk-tag.ques { background: #8b5cf622; color: #a78bfa; border: 1px solid #8b5cf644; }
.pk-title { flex: 1; font-size: 0.85rem; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pk-score {
  width: 4rem; flex-shrink: 0; background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 4px; padding: 0.2rem 0.4rem; color: var(--text-primary); font-size: 0.8rem;
}
.total-bar { text-align: right; font-size: 0.875rem; color: var(--text-secondary); padding-top: 0.5rem; border-top: 1px solid var(--border); }
.total-bar strong { color: var(--accent); font-size: 1.05rem; }
.asgn-cat { font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 4px; flex-shrink: 0; }
.cat-practice { background: rgba(100,100,100,0.12); color: var(--text-muted); border: 1px solid var(--border); }
.cat-homework { background: rgba(99,102,241,0.12); color: var(--accent); border: 1px solid rgba(99,102,241,0.3); }
.cat-exam { background: #ef444422; color: #f87171; border: 1px solid #ef444444; }
</style>
