<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api/index'

const router = useRouter()
const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const myId = computed(() => userStore.user?.id)

const loading = ref(true)
const saving = ref(null)   // user id being saved
const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const roleFilter = ref('')
const apiError = ref('')

// transfer dialog state
const transferDialog = ref(false)
const transferTarget = ref(null)   // user object to receive super admin
const transferring = ref(false)
const transferError = ref('')

const ROLE_LABEL = { student: '学生', teacher: '教师', admin: '管理员' }
const ROLE_CLS   = { student: 'role-student', teacher: 'role-teacher', admin: 'role-admin' }

async function load() {
  loading.value = true
  apiError.value = ''
  try {
    const { data } = await api.get('/admin/users/', {
      params: { page: page.value, search: search.value, role: roleFilter.value },
    })
    users.value = data.users
    total.value = data.total
    pageSize.value = data.page_size
  } catch (e) {
    const status = e.response?.status
    apiError.value = status === 401 ? '登录已过期，请重新登录'
      : status === 403 ? '无权限访问用户列表'
      : `加载失败（${status ? 'HTTP ' + status : '网络错误'}）`
  } finally {
    loading.value = false
  }
}

onMounted(load)

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 350)
}
function onRoleFilter() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * pageSize.value < total.value) { page.value++; load() } }
const totalPages = () => Math.ceil(total.value / pageSize.value)

// 当前操作者能否修改该用户的角色
function canEdit(u) {
  if (u.id === myId.value) return false       // 不能改自己
  if (u.is_super_admin) return false          // 总管理员受保护
  // 普通管理员不能涉及 admin 角色
  if (!isSuperAdmin.value && u.role === 'admin') return false
  return true
}

// 当前操作者能看到的角色选项
function roleOptions() {
  if (isSuperAdmin.value) return ['student', 'teacher', 'admin']
  // 普通管理员：只能在 student/teacher 之间切换，且目标不能是 admin
  return ['student', 'teacher']
}

async function changeRole(u, newRole) {
  if (u.role === newRole || !canEdit(u)) return
  saving.value = u.id
  try {
    await api.patch(`/admin/users/${u.id}/`, { role: newRole })
    u.role = newRole
  } catch (e) {
    alert(e.response?.data?.detail || '修改失败')
  } finally {
    saving.value = null
  }
}

// 转让总管理员
function openTransfer(u) {
  transferTarget.value = u
  transferError.value = ''
  transferDialog.value = true
}

async function doTransfer() {
  transferring.value = true
  transferError.value = ''
  try {
    await api.post('/admin/transfer-super-admin/', { user_id: transferTarget.value.id })
    transferDialog.value = false
    // 刷新用户信息（自己已不是总管理员）
    await userStore.fetchMe()
    await load()
  } catch (e) {
    transferError.value = e.response?.data?.detail || '转让失败'
  } finally {
    transferring.value = false
  }
}
</script>

<template>
  <div class="user-manage">
    <div class="page-header">
      <button class="btn-back" @click="router.push('/admin')">← 管理后台</button>
      <h1 class="page-title">用户管理</h1>
      <span class="total-hint">共 {{ total }} 名用户</span>
    </div>

    <!-- 权限说明 -->
    <div v-if="isSuperAdmin" class="perm-banner super-banner">
      你是 <strong>总管理员</strong>，可授予 / 撤销所有人的管理员权限，并可转让总管理员身份。
    </div>
    <div v-else class="perm-banner">
      你是 <strong>管理员</strong>，可在学生 / 教师之间切换角色；授予管理员权限需由总管理员操作。
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <input
        v-model="search"
        class="search-input"
        placeholder="搜索用户名 / 姓名 / 学号"
        @input="onSearchInput"
      />
      <select v-model="roleFilter" class="role-select" @change="onRoleFilter">
        <option value="">全部角色</option>
        <option value="student">学生</option>
        <option value="teacher">教师</option>
        <option value="admin">管理员</option>
      </select>
    </div>

    <!-- 错误 -->
    <div v-if="apiError" class="error-tip">{{ apiError }}</div>

    <!-- 用户表格 -->
    <div class="section-card">
      <div class="table-wrap">
        <table class="user-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>姓名</th>
              <th>学号</th>
              <th>专业 / 年级</th>
              <th class="col-num">AC 数</th>
              <th>注册日期</th>
              <th>角色</th>
              <th v-if="isSuperAdmin">操作</th>
            </tr>
          </thead>
          <tbody v-if="!loading">
            <tr v-for="u in users" :key="u.id" :class="{ 'row-me': u.id === myId, 'row-super': u.is_super_admin }">
              <td>
                <span class="user-link" @click="router.push(`/users/${u.id}`)">{{ u.username }}</span>
                <span v-if="u.is_super_admin" class="super-badge" title="总管理员">★</span>
                <span v-if="u.id === myId" class="me-badge">我</span>
              </td>
              <td class="text-muted">{{ u.display_name || '—' }}</td>
              <td class="text-muted">{{ u.student_id || '—' }}</td>
              <td class="text-muted">
                <span v-if="u.major || u.grade">{{ u.major }}<span v-if="u.major && u.grade"> · </span>{{ u.grade }}</span>
                <span v-else>—</span>
              </td>
              <td class="col-num">{{ u.ac_count }}</td>
              <td class="text-muted">{{ u.date_joined }}</td>
              <td>
                <div class="role-cell">
                  <select
                    v-if="canEdit(u)"
                    :value="u.role"
                    :disabled="saving === u.id"
                    :class="['inline-role-select', ROLE_CLS[u.role]]"
                    @change="changeRole(u, $event.target.value)"
                  >
                    <option v-for="r in roleOptions()" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
                  </select>
                  <span v-else :class="['role-tag', ROLE_CLS[u.role]]">{{ ROLE_LABEL[u.role] }}</span>
                  <span v-if="saving === u.id" class="saving-dot">…</span>
                </div>
              </td>
              <!-- 转让按钮：仅总管理员可见，目标必须是其他 admin 且非总管理员 -->
              <td v-if="isSuperAdmin">
                <button
                  v-if="u.role === 'admin' && !u.is_super_admin && u.id !== myId"
                  class="btn-transfer"
                  @click="openTransfer(u)"
                >转让总管理员</button>
              </td>
            </tr>
            <tr v-if="users.length === 0">
              <td :colspan="isSuperAdmin ? 8 : 7" class="empty-td">没有找到匹配的用户</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr><td :colspan="isSuperAdmin ? 8 : 7" class="empty-td">加载中…</td></tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="total > pageSize">
        <button class="pg-btn" :disabled="page === 1" @click="prevPage">‹ 上一页</button>
        <span class="pg-info">{{ page }} / {{ totalPages() }}</span>
        <button class="pg-btn" :disabled="page >= totalPages()" @click="nextPage">下一页 ›</button>
      </div>
    </div>

    <!-- 转让总管理员确认弹窗 -->
    <div v-if="transferDialog" class="modal-overlay" @click.self="transferDialog = false">
      <div class="modal">
        <h2 class="modal-title">转让总管理员</h2>
        <p class="modal-body">
          确定将总管理员身份转让给 <strong>{{ transferTarget?.username }}</strong> 吗？<br/>
          转让后，你将恢复为普通管理员，无法再设置或撤销管理员权限。
        </p>
        <p v-if="transferError" class="modal-error">{{ transferError }}</p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="transferDialog = false">取消</button>
          <button class="btn-danger" :disabled="transferring" @click="doTransfer">
            {{ transferring ? '转让中…' : '确认转让' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-manage { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }

.page-header { display: flex; align-items: center; gap: 1rem; }
.btn-back {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  flex-shrink: 0; transition: border-color 0.15s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.page-title { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0; flex: 1; }
.total-hint { font-size: 0.82rem; color: var(--text-muted); flex-shrink: 0; }

.perm-banner {
  font-size: 0.85rem; color: var(--text-secondary);
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 0.6rem 1rem;
}
.super-banner { border-color: #f59e0b55; background: #f59e0b0c; color: var(--text-primary); }
.super-banner strong { color: #f59e0b; }

.filter-bar { display: flex; gap: 0.75rem; }
.search-input {
  flex: 1; background: var(--bg-input); border: 1px solid var(--border);
  color: var(--text-primary); padding: 0.5rem 0.9rem; border-radius: 8px;
  font-size: 0.875rem; outline: none; transition: border-color 0.15s;
}
.search-input:focus { border-color: var(--accent); }
.role-select {
  background: var(--bg-input); border: 1px solid var(--border);
  color: var(--text-secondary); padding: 0.5rem 0.75rem; border-radius: 8px;
  font-size: 0.875rem; cursor: pointer; outline: none;
}
.error-tip { color: #f87171; font-size: 0.875rem; padding: 0.5rem 0; }

.section-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.25rem;
}
.table-wrap { overflow-x: auto; }
.user-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.user-table th {
  padding: 0.5rem 0.75rem; text-align: left; color: var(--text-muted);
  font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap;
}
.user-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
.user-table tr:last-child td { border-bottom: none; }
.row-super td:first-child { background: #f59e0b05; }

.user-link { color: var(--accent); cursor: pointer; }
.user-link:hover { text-decoration: underline; }
.super-badge {
  margin-left: 0.3rem; color: #f59e0b; font-size: 0.75rem;
  background: #f59e0b1a; border: 1px solid #f59e0b44;
  border-radius: 4px; padding: 0.05rem 0.35rem;
}
.me-badge {
  margin-left: 0.3rem; font-size: 0.72rem; color: var(--accent);
  background: var(--accent-light); border-radius: 4px; padding: 0.05rem 0.3rem;
}
.text-muted { color: var(--text-muted); }
.col-num { text-align: right; }
.empty-td { text-align: center; padding: 2.5rem; color: var(--text-muted); }

.role-cell { display: flex; align-items: center; gap: 0.4rem; }
.inline-role-select {
  border-radius: 5px; padding: 0.2rem 0.5rem;
  font-size: 0.78rem; font-weight: 500; cursor: pointer; border: 1px solid transparent;
  outline: none; transition: all 0.15s;
}
.role-tag {
  display: inline-block; border-radius: 5px; padding: 0.2rem 0.5rem;
  font-size: 0.78rem; font-weight: 500; border: 1px solid transparent;
}
.role-student, .inline-role-select.role-student { background: var(--accent-light, #ede9ff); color: var(--accent, #534AB7); border-color: rgba(83,74,183,0.25); }
.role-teacher, .inline-role-select.role-teacher { background: #10b98122; color: #10b981; border-color: #10b98144; }
.role-admin,   .inline-role-select.role-admin   { background: #f59e0b22; color: #f59e0b;  border-color: #f59e0b44; }
.inline-role-select:disabled { opacity: 0.5; cursor: default; }
.saving-dot { font-size: 0.8rem; color: var(--text-muted); }

.btn-transfer {
  font-size: 0.78rem; padding: 0.2rem 0.6rem; border-radius: 5px;
  background: none; border: 1px solid #f59e0b66; color: #f59e0b;
  cursor: pointer; white-space: nowrap; transition: background 0.15s;
}
.btn-transfer:hover { background: #f59e0b1a; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.pg-btn {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  transition: all 0.15s;
}
.pg-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pg-btn:disabled { opacity: 0.35; cursor: default; }
.pg-info { font-size: 0.875rem; color: var(--text-muted); }

/* Transfer modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 2rem; width: 420px; max-width: 95vw;
  display: flex; flex-direction: column; gap: 1rem;
}
.modal-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-body { font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; margin: 0; }
.modal-body strong { color: var(--text-primary); }
.modal-error { color: #f87171; font-size: 0.875rem; margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-secondary {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-secondary:hover { border-color: var(--text-secondary); }
.btn-danger {
  background: #ef4444; color: #fff; border: none;
  padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  transition: opacity 0.15s;
}
.btn-danger:hover:not(:disabled) { opacity: 0.88; }
.btn-danger:disabled { opacity: 0.5; cursor: default; }
</style>
