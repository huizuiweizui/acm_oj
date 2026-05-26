<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await userStore.login(username.value, password.value)
    router.push(router.currentRoute.value.query.next || '/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-card">
      <h2 class="auth-title">登录</h2>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <form @submit.prevent="submit" class="auth-form">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入用户名" autofocus />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" />
        </div>
        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p class="auth-footer">
        还没有账号？<RouterLink to="/register">立即注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  background: #16162a;
  border: 1px solid #2d2d4e;
  border-radius: 12px;
  padding: 2.5rem;
}
.auth-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 1.5rem;
  color: #e0e0f0;
}
.error-msg {
  background: #2d1520;
  border: 1px solid #7d2d3d;
  color: #ff8080;
  padding: 0.6rem 0.9rem;
  border-radius: 6px;
  font-size: 0.875rem;
  margin-bottom: 1.2rem;
}
.auth-form { display: flex; flex-direction: column; gap: 1.1rem; }
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-group label { font-size: 0.85rem; color: #a0a0c0; }
.form-group input {
  padding: 0.6rem 0.9rem;
  background: #1a1a30;
  border: 1px solid #3d3d5c;
  border-radius: 7px;
  color: #e0e0f0;
  font-size: 0.95rem;
}
.form-group input:focus {
  outline: none;
  border-color: #7c6af7;
  background: #1e1e38;
}
.btn-submit {
  margin-top: 0.5rem;
  padding: 0.65rem;
  background: #7c6af7;
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-submit:hover:not(:disabled) { background: #6c5ae7; }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
.auth-footer {
  margin-top: 1.5rem;
  text-align: center;
  font-size: 0.875rem;
  color: #888;
}
.auth-footer a { color: #a78bfa; }
.auth-footer a:hover { text-decoration: underline; }
</style>
