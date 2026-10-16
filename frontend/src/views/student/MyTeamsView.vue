<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTeams, previewTeam, joinTeam, leaveTeam, getMyRequests } from '@/api/team'

const router = useRouter()

const myTeams = ref([])
const myRequests = ref([])
const loading = ref(false)

// 加入团队流程
const step = ref('input')   // 'input' | 'preview' | 'remark'
const inviteCode = ref('')
const previewData = ref(null)
const remark = ref('')
const previewing = ref(false)
const joining = ref(false)
const joinError = ref('')

const showJoinPanel = ref(false)

async function load() {
  loading.value = true
  try {
    const [teams, reqs] = await Promise.all([getTeams(), getMyRequests()])
    myTeams.value = teams.data
    myRequests.value = reqs.data
  } finally {
    loading.value = false
  }
}

function openJoin() {
  step.value = 'input'
  inviteCode.value = ''
  previewData.value = null
  remark.value = ''
  joinError.value = ''
  showJoinPanel.value = true
}

async function doPreview() {
  joinError.value = ''
  if (!inviteCode.value.trim()) { joinError.value = '请输入邀请码'; return }
  previewing.value = true
  try {
    const { data } = await previewTeam(inviteCode.value.trim())
    previewData.value = data
    if (data.already_member) {
      joinError.value = '你已经是该团队成员'
      return
    }
    if (data.pending_request) {
      joinError.value = '你已有待审核的申请，请等待教师处理'
      return
    }
    step.value = 'remark'
  } catch (e) {
    joinError.value = e.response?.data?.detail || '邀请码无效'
  } finally {
    previewing.value = false
  }
}

async function doJoin() {
  joinError.value = ''
  if (!remark.value.trim()) { joinError.value = '备注不能为空，请填写如「2023级 张三」'; return }
  joining.value = true
  try {
    await joinTeam({ invite_code: inviteCode.value.trim(), remark: remark.value.trim() })
    showJoinPanel.value = false
    await load()
  } catch (e) {
    joinError.value = e.response?.data?.detail || '申请失败'
  } finally {
    joining.value = false
  }
}

async function doLeave(team) {
  if (!confirm(`确定退出团队「${team.name}」？`)) return
  try {
    await leaveTeam(team.id)
    myTeams.value = myTeams.value.filter(t => t.id !== team.id)
  } catch (e) {
    alert(e.response?.data?.detail || '退出失败')
  }
}

function statusLabel(s) {
  return { pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] || s
}
function statusClass(s) {
  return { pending: 'status-pending', approved: 'status-ok', rejected: 'status-bad' }[s] || ''
}
function fmt(dt) {
  return dt ? new Date(dt).toLocaleDateString('zh-CN') : ''
}

onMounted(load)
</script>

<template>
  <div class="my-teams-page">
    <div class="page-header">
      <h1 class="page-title">我的团队</h1>
      <button class="btn-primary" @click="openJoin">＋ 加入团队</button>
    </div>

    <div v-if="loading" class="loading-tip">加载中…</div>

    <template v-else>
      <!-- 已加入的团队 -->
      <section>
        <h2 class="section-title">已加入（{{ myTeams.length }}）</h2>
        <div v-if="myTeams.length === 0" class="empty-tip">还没有加入任何团队</div>
        <div v-else class="team-list">
          <div v-for="t in myTeams" :key="t.id" class="team-row">
            <div class="team-row-left">
              <span class="t-name">{{ t.name }}</span>
              <span v-if="t.my_role === 'captain'" class="role-cap">👑 队长</span>
              <span class="t-teacher">by {{ t.creator_username }}</span>
            </div>
            <div class="team-row-right">
              <span class="t-remark" v-if="t.my_remark">备注：{{ t.my_remark }}</span>
              <span class="t-rank" v-if="t.my_rank" title="团队内 AC 排名">
                第 <b>{{ t.my_rank }}</b> / {{ t.member_count }} 名 · AC {{ t.my_ac }}
              </span>
              <span class="t-count" v-else>{{ t.member_count }} 人</span>
              <button class="btn-view" @click="router.push(`/my-teams/${t.id}`)">公告/作业</button>
              <button class="btn-leave" @click="doLeave(t)">退出</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 我的申请记录 -->
      <section v-if="myRequests.length > 0" style="margin-top:2rem">
        <h2 class="section-title">申请记录</h2>
        <div class="req-list">
          <div v-for="r in myRequests" :key="r.id" class="req-row">
            <div class="req-left">
              <span class="t-name">{{ r.team_name }}</span>
              <span class="req-remark">备注：{{ r.remark }}</span>
            </div>
            <div class="req-right">
              <span :class="['req-status', statusClass(r.status)]">{{ statusLabel(r.status) }}</span>
              <span v-if="r.reject_reason" class="reject-reason">理由：{{ r.reject_reason }}</span>
              <span class="t-count">{{ fmt(r.created_at) }}</span>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- 加入团队弹窗 -->
    <div v-if="showJoinPanel" class="modal-overlay" @click.self="showJoinPanel = false">
      <div class="modal">
        <h2 class="modal-title">加入团队</h2>

        <!-- Step 1: 输入邀请码 -->
        <template v-if="step === 'input'">
          <div class="form-group">
            <label>邀请码</label>
            <div class="input-row">
              <input
                v-model="inviteCode"
                class="form-input"
                placeholder="请输入 8 位邀请码"
                maxlength="8"
                @keyup.enter="doPreview"
              />
              <button class="btn-primary" :disabled="previewing" @click="doPreview">
                {{ previewing ? '查询…' : '查询' }}
              </button>
            </div>
          </div>
          <p v-if="joinError" class="form-error">{{ joinError }}</p>
        </template>

        <!-- Step 2: 确认团队 + 填备注 -->
        <template v-if="step === 'remark' && previewData">
          <div class="preview-box">
            <p class="preview-name">{{ previewData.name }}</p>
            <p class="preview-sub">创建教师：{{ previewData.creator_username }}</p>
            <p v-if="previewData.description" class="preview-sub">{{ previewData.description }}</p>
            <p class="preview-sub">
              {{ previewData.need_review ? '加入需教师审核' : '直接入队，无需审核' }}
            </p>
          </div>
          <div class="form-group">
            <label>申请备注 <span class="required">*</span></label>
            <input
              v-model="remark"
              class="form-input"
              placeholder="如「2023级 张三」，教师将以此识别你"
              maxlength="100"
            />
            <p class="hint">备注将自动作为你的团队内备注</p>
          </div>
          <p v-if="joinError" class="form-error">{{ joinError }}</p>
          <div class="modal-actions">
            <button class="btn-secondary" @click="step = 'input'">← 重新输入</button>
            <button class="btn-primary" :disabled="joining" @click="doJoin">
              {{ joining ? '提交中…' : (previewData.need_review ? '提交申请' : '立即加入') }}
            </button>
          </div>
        </template>

        <div v-if="step === 'input'" class="modal-actions">
          <button class="btn-secondary" @click="showJoinPanel = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.my-teams-page { max-width: 760px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.page-title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-secondary); margin: 0 0 0.75rem; }

/* Team list */
.team-list { display: flex; flex-direction: column; gap: 0.5rem; }
.team-row {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 0.85rem 1.25rem; gap: 1rem;
}
.team-row-left { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.team-row-right { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }
.t-name { font-weight: 600; color: var(--text-primary); font-size: 0.95rem; }
.role-cap { background: #f59e0b22; color: #f59e0b; border-radius: 10px; padding: 0.1rem 0.5rem; font-size: 0.75rem; }
.t-teacher, .t-remark, .t-count { font-size: 0.8rem; color: var(--text-muted); }
.t-rank { font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; }
.t-rank b { color: var(--accent); font-size: 0.9rem; }

/* Request list */
.req-list { display: flex; flex-direction: column; gap: 0.5rem; }
.req-row {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 0.75rem 1.25rem; gap: 1rem;
}
.req-left { display: flex; align-items: center; gap: 0.75rem; }
.req-right { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }
.req-remark { font-size: 0.8rem; color: var(--text-muted); }
.req-status { font-size: 0.78rem; padding: 0.15rem 0.5rem; border-radius: 10px; }
.status-pending { background: #f59e0b22; color: #f59e0b; }
.status-ok { background: #10b98122; color: #10b981; }
.status-bad { background: #f8717122; color: #f87171; }
.reject-reason { font-size: 0.78rem; color: #f87171; }

/* Buttons */
.btn-view {
  background: none; border: 1px solid rgba(99,102,241,0.4); color: var(--accent);
  padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem;
}
.btn-view:hover { border-color: var(--accent); }
.btn-leave {
  background: none; border: 1px solid #f8717144; color: #f87171;
  padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem;
}
.btn-leave:hover { border-color: #f87171; }
.btn-primary {
  background: var(--accent); color: #fff; border: none;
  padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  transition: background 0.15s; white-space: nowrap;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 1.75rem; width: 420px; max-width: 95vw; display: flex; flex-direction: column; gap: 1rem;
}
.modal-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-group label { font-size: 0.875rem; color: var(--text-secondary); }
.required { color: #f87171; }
.input-row { display: flex; gap: 0.5rem; }
.form-input {
  flex: 1; background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.9rem;
  width: 100%; box-sizing: border-box; transition: border-color 0.15s;
}
.form-input:focus { outline: none; border-color: var(--accent); }
.hint { font-size: 0.78rem; color: var(--text-muted); margin: 0; }
.form-error { color: #f87171; font-size: 0.875rem; margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }

.preview-box {
  background: rgba(124,106,247,0.08); border: 1px solid rgba(124,106,247,0.25);
  border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; gap: 0.3rem;
}
.preview-name { font-weight: 700; color: var(--text-primary); font-size: 1.05rem; margin: 0; }
.preview-sub { font-size: 0.83rem; color: var(--text-muted); margin: 0; }

.loading-tip, .empty-tip { text-align: center; padding: 2rem; color: var(--text-muted); }
</style>
