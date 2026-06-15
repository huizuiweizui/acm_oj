<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getTeams, createTeam } from '@/api/team'

const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.user?.role === 'admin')

const teams = ref([])
const loading = ref(true)
const apiError = ref('')
const showCreate = ref(false)

const form = ref({ name: '', description: '', need_review: true })
const creating = ref(false)
const formError = ref('')

async function load() {
  loading.value = true
  apiError.value = ''
  try {
    const { data } = await getTeams()
    teams.value = data
  } catch (e) {
    const status = e.response?.status
    if (status === 401) apiError.value = '登录已过期，请重新登录'
    else if (status === 403) apiError.value = '无权限访问教学管理'
    else apiError.value = `加载失败（${status ? 'HTTP ' + status : '网络错误'}）`
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  formError.value = ''
  if (!form.value.name.trim()) { formError.value = '团队名称不能为空'; return }
  creating.value = true
  try {
    const { data } = await createTeam(form.value)
    teams.value.unshift(data)
    showCreate.value = false
    form.value = { name: '', description: '', need_review: true }
  } catch (e) {
    formError.value = e.response?.data?.detail || '创建失败'
  } finally {
    creating.value = false
  }
}

function copyCode(code) {
  navigator.clipboard.writeText(code).catch(() => {})
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleDateString('zh-CN') : ''
}

onMounted(load)
</script>

<template>
  <div class="teach-dash">
    <div class="page-header">
      <div>
        <h1 class="page-title">教学管理</h1>
        <p class="page-sub">{{ isAdmin ? '查看所有教师的团队与班级（管理员视图）' : '管理你创建的团队与班级' }}</p>
      </div>
      <div class="header-actions" style="display:flex;gap:0.6rem;align-items:center">
        <button class="btn-secondary" @click="router.push('/teacher/questions')">📚 题库</button>
        <button class="btn-primary" @click="showCreate = true">＋ 创建团队</button>
      </div>
    </div>

    <!-- 团队卡片列表 -->
    <div v-if="loading" class="loading-tip">加载中…</div>
    <div v-else-if="apiError" class="error-tip">
      <span>{{ apiError }}</span>
      <button class="btn-retry" @click="load">重试</button>
    </div>
    <div v-else-if="teams.length === 0" class="empty-tip">
      还没有团队，点击右上角「创建团队」开始。
    </div>
    <div v-else class="team-grid">
      <div v-for="t in teams" :key="t.id" class="team-card" @click="router.push(`/teacher/teams/${t.id}`)">
        <div class="card-top">
          <span class="team-name">{{ t.name }}</span>
          <span v-if="t.pending_count > 0" class="badge-pending">{{ t.pending_count }} 待审</span>
        </div>
        <p v-if="t.description" class="team-desc">{{ t.description }}</p>
        <div class="card-meta">
          <span>{{ t.member_count }} 人</span>
          <span v-if="isAdmin" class="creator-tag">{{ t.creator_username }}</span>
          <span>创建于 {{ fmt(t.created_at) }}</span>
        </div>
        <div class="invite-row" @click.stop>
          <span class="invite-label">邀请码</span>
          <code class="invite-code">{{ t.invite_code }}</code>
          <button class="btn-copy" @click="copyCode(t.invite_code)">复制</button>
        </div>
        <div class="card-actions" @click.stop>
          <button class="btn-manage" @click="router.push(`/teacher/teams/${t.id}`)">管理 →</button>
          <button class="btn-dashboard" @click="router.push(`/teacher/teams/${t.id}/dashboard`)">总览</button>
        </div>
      </div>
    </div>

    <!-- 创建团队弹窗 -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h2 class="modal-title">创建团队</h2>
        <div class="form-group">
          <label>团队名称 <span class="required">*</span></label>
          <input v-model="form.name" class="form-input" placeholder="如：2023算法竞赛班" maxlength="100" />
        </div>
        <div class="form-group">
          <label>简介（可选）</label>
          <textarea v-model="form.description" class="form-textarea" placeholder="团队说明…" rows="3" maxlength="300" />
        </div>
        <div class="form-group form-check">
          <label class="check-label">
            <input type="checkbox" v-model="form.need_review" />
            <span>加入需教师审核</span>
          </label>
          <p class="check-hint">关闭后学生输入邀请码直接入队，无需审核</p>
        </div>
        <p v-if="formError" class="form-error">{{ formError }}</p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreate = false">取消</button>
          <button class="btn-primary" :disabled="creating" @click="submitCreate">
            {{ creating ? '创建中…' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.teach-dash { max-width: 960px; margin: 0 auto; }
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 2rem;
}
.page-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.25rem; }
.page-sub { color: var(--text-muted); font-size: 0.875rem; margin: 0; }

/* Grid */
.team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; }
.team-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
  display: flex; flex-direction: column; gap: 0.75rem;
}
.team-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.card-top { display: flex; justify-content: space-between; align-items: center; }
.team-name { font-weight: 600; font-size: 1rem; color: var(--text-primary); }
.badge-pending {
  background: #f59e0b22; color: #f59e0b;
  border: 1px solid #f59e0b44;
  border-radius: 12px; padding: 0.1rem 0.6rem; font-size: 0.75rem; font-weight: 600;
}
.team-desc { color: var(--text-muted); font-size: 0.85rem; margin: 0; line-height: 1.4; }
.card-meta { display: flex; gap: 1rem; font-size: 0.8rem; color: var(--text-muted); flex-wrap: wrap; }
.creator-tag { color: var(--accent); font-weight: 500; }
.invite-row {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--bg-secondary); border-radius: 6px; padding: 0.4rem 0.75rem;
}
.invite-label { font-size: 0.75rem; color: var(--text-muted); }
.invite-code { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: var(--accent); letter-spacing: 0.1em; flex: 1; }
.btn-copy {
  font-size: 0.75rem; padding: 0.15rem 0.5rem;
  background: none; border: 1px solid var(--border); border-radius: 4px;
  color: var(--text-secondary); cursor: pointer; transition: border-color 0.15s;
}
.btn-copy:hover { border-color: var(--accent); color: var(--accent); }
.card-actions { display: flex; gap: 0.5rem; }
.btn-manage {
  flex: 1; padding: 0.4rem; border-radius: 6px; border: 1px solid var(--accent);
  background: none; color: var(--accent); cursor: pointer; font-size: 0.85rem; transition: background 0.15s;
}
.btn-manage:hover { background: var(--accent); color: #fff; }
.btn-dashboard {
  padding: 0.4rem 0.75rem; border-radius: 6px; border: 1px solid var(--border);
  background: none; color: var(--text-secondary); cursor: pointer; font-size: 0.85rem;
}
.btn-dashboard:hover { border-color: var(--text-secondary); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 2rem; width: 440px; max-width: 95vw; display: flex; flex-direction: column; gap: 1rem;
}
.modal-title { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-group label { font-size: 0.875rem; color: var(--text-secondary); }
.required { color: #f87171; }
.form-input, .form-textarea {
  background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.9rem;
  transition: border-color 0.15s; width: 100%; box-sizing: border-box;
}
.form-input:focus, .form-textarea:focus { outline: none; border-color: var(--accent); }
.form-textarea { resize: vertical; font-family: inherit; }
.form-check { gap: 0.25rem; }
.check-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.9rem; color: var(--text-primary); }
.check-hint { font-size: 0.78rem; color: var(--text-muted); margin: 0; }
.form-error { color: #f87171; font-size: 0.875rem; margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }

/* Buttons */
.btn-primary {
  background: var(--accent); color: #fff; border: none;
  padding: 0.5rem 1.25rem; border-radius: 6px; cursor: pointer; font-size: 0.9rem;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.5rem 1.25rem; border-radius: 6px; cursor: pointer; font-size: 0.9rem;
}
.btn-secondary:hover { border-color: var(--text-secondary); }

.loading-tip, .empty-tip { text-align: center; padding: 3rem; color: var(--text-muted); }
.error-tip {
  display: flex; align-items: center; justify-content: center; gap: 1rem;
  padding: 3rem; color: #f87171; font-size: 0.9rem;
}
.btn-retry {
  background: none; border: 1px solid #f87171; color: #f87171;
  padding: 0.3rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem;
  transition: background 0.15s;
}
.btn-retry:hover { background: #f871711a; }
</style>
