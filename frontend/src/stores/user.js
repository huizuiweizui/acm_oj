import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister, getMe, logout as apiLogout } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')

  const isLoggedIn = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isTeacher = computed(() => user.value?.role === 'teacher')
  const isTeacherOrAdmin = computed(() => ['teacher', 'admin'].includes(user.value?.role))
  const isSuperAdmin = computed(() => isAdmin.value && !!user.value?.is_super_admin)
  const canCreateContest = computed(() =>
    isTeacherOrAdmin.value || !!user.value?.can_create_contest
  )

  function _saveTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  async function login(username, password) {
    const { data } = await apiLogin(username, password)
    _saveTokens(data.access, data.refresh)
    user.value = data.user
  }

  async function register(username, password, password2) {
    const { data } = await apiRegister(username, password, password2)
    _saveTokens(data.access, data.refresh)
    user.value = data.user
  }

  async function fetchMe() {
    if (!accessToken.value) return
    try {
      const { data } = await getMe()
      user.value = data
    } catch {
      logout()
    }
  }

  function logout() {
    // 服务端拉黑 refresh token（失败不影响本地退出）
    if (refreshToken.value && accessToken.value) {
      apiLogout(refreshToken.value, accessToken.value).catch(() => {})
    }
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { user, accessToken, isLoggedIn, isAdmin, isTeacher, isTeacherOrAdmin, isSuperAdmin, canCreateContest, login, register, fetchMe, logout }
})
