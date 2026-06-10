<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api/index'

const router = useRouter()
const userStore = useUserStore()

const oldPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (newPassword.value !== newPassword2.value) { error.value = '两次密码不一致'; return }
  if (newPassword.value.length < 6) { error.value = '新密码至少 6 位'; return }
  loading.value = true
  try {
    await api.post('/auth/password/', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    // 刷新用户信息（must_change_password 已被后端清除）
    await userStore.fetchMe()
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.old_password?.[0] || '修改失败，请检查原密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="cp-wrap">
    <div class="cp-card">
      <div class="cp-icon">🔒</div>
      <h1 class="cp-title">修改初始密码</h1>
      <p class="cp-hint">您的账号正在使用初始密码，请立即修改以保障账号安全。</p>

      <div v-if="error" class="cp-error">{{ error }}</div>

      <form class="cp-form" @submit.prevent="submit">
        <label class="cp-label">原密码（初始密码为学号）</label>
        <input
          v-model="oldPassword"
          type="password"
          class="cp-input"
          placeholder="请输入原密码"
          autocomplete="current-password"
          required
        />

        <label class="cp-label">新密码</label>
        <input
          v-model="newPassword"
          type="password"
          class="cp-input"
          placeholder="至少 6 位"
          autocomplete="new-password"
          required
        />

        <label class="cp-label">确认新密码</label>
        <input
          v-model="newPassword2"
          type="password"
          class="cp-input"
          placeholder="再次输入新密码"
          autocomplete="new-password"
          required
        />

        <button type="submit" class="cp-btn" :disabled="loading">
          {{ loading ? '提交中…' : '修改密码' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.cp-wrap {
  min-height: 80vh; display: flex; align-items: center; justify-content: center; padding: 2rem;
}
.cp-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 2.5rem; width: 380px; max-width: 95vw;
  display: flex; flex-direction: column; gap: 1rem;
}
.cp-icon { font-size: 2rem; text-align: center; }
.cp-title { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); text-align: center; margin: 0; }
.cp-hint { font-size: 0.85rem; color: var(--text-muted); text-align: center; margin: 0; }
.cp-error {
  background: #ef444422; border: 1px solid #f87171; color: #f87171;
  border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.875rem;
}
.cp-form { display: flex; flex-direction: column; gap: 0.6rem; }
.cp-label { font-size: 0.82rem; color: var(--text-secondary); }
.cp-input {
  background: var(--input-bg, rgba(255,255,255,0.05)); border: 1px solid var(--border);
  border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary);
  font-size: 0.9rem; width: 100%; box-sizing: border-box;
}
.cp-input:focus { outline: none; border-color: var(--accent); }
.cp-btn {
  background: var(--accent); color: #fff; border: none; border-radius: 6px;
  padding: 0.6rem; font-size: 0.95rem; cursor: pointer; margin-top: 0.5rem;
  transition: opacity 0.15s;
}
.cp-btn:disabled { opacity: 0.5; cursor: default; }
.cp-btn:hover:not(:disabled) { opacity: 0.85; }
</style>
