<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/index'

const router = useRouter()
const loading = ref(true)
const saving = ref(null)   // user id currently being saved

const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const roleFilter = ref('')

const ROLE_LABEL = { student: '学生', teacher: '教师', admin: '管理员' }
const ROLE_CLS = { student: 'role-student', teacher: 'role-teacher', admin: 'role-admin' }

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/users/', {
      params: { page: page.value, search: search.value, role: roleFilter.value },
    })
    users.value = data.users
    total.value = data.total
    pageSize.value = data.page_size
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

async function changeRole(user, newRole) {
  if (user.role === newRole) return
  saving.value = user.id
  try {
    await api.patch(`/admin/users/${user.id}/`, { role: newRole })
    user.role = newRole
  } finally {
    saving.value = null
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
              <th>AC 数</th>
              <th>注册日期</th>
              <th>角色</th>
            </tr>
          </thead>
          <tbody v-if="!loading">
            <tr v-for="u in users" :key="u.id">
              <td>
                <span class="user-link" @click="router.push(`/users/${u.id}`)">{{ u.username }}</span>
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
                <div class="role-select-wrap">
                  <select
                    :value="u.role"
                    :disabled="saving === u.id"
                    :class="['inline-role-select', ROLE_CLS[u.role]]"
                    @change="changeRole(u, $event.target.value)"
                  >
                    <option value="student">学生</option>
                    <option value="teacher">教师</option>
                    <option value="admin">管理员</option>
                  </select>
                  <span v-if="saving === u.id" class="saving-dot">…</span>
                </div>
              </td>
            </tr>
            <tr v-if="users.length === 0">
              <td colspan="7" class="empty-td">没有找到匹配的用户</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr><td colspan="7" class="empty-td">加载中…</td></tr>
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
.user-link { color: var(--accent); cursor: pointer; }
.user-link:hover { text-decoration: underline; }
.text-muted { color: var(--text-muted); }
.col-num { text-align: right; }
.empty-td { text-align: center; padding: 2.5rem; color: var(--text-muted); }

.role-select-wrap { display: flex; align-items: center; gap: 0.4rem; }
.inline-role-select {
  border-radius: 5px; padding: 0.2rem 0.5rem;
  font-size: 0.78rem; font-weight: 500; cursor: pointer; border: 1px solid transparent;
  outline: none; transition: all 0.15s;
}
.inline-role-select.role-student { background: var(--accent-light); color: var(--accent-text); border-color: rgba(99,102,241,0.3); }
.inline-role-select.role-teacher { background: #10b98122; color: #10b981; border-color: #10b98144; }
.inline-role-select.role-admin { background: #f59e0b22; color: #f59e0b; border-color: #f59e0b44; }
.inline-role-select:disabled { opacity: 0.5; cursor: default; }
.saving-dot { font-size: 0.8rem; color: var(--text-muted); }

.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.pg-btn {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  transition: all 0.15s;
}
.pg-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pg-btn:disabled { opacity: 0.35; cursor: default; }
.pg-info { font-size: 0.875rem; color: var(--text-muted); }
</style>
