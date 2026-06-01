<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const isAuthPage = computed(() => route.name === 'login' || route.name === 'register')
const isDark = ref(true)

function applyTheme(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  localStorage.setItem('theme', dark ? 'dark' : 'light')
}

function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme(isDark.value)
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  isDark.value = saved !== 'light'
  applyTheme(isDark.value)
})

function logout() {
  userStore.logout()
  router.push('/')
}
</script>

<template>
  <div id="app">
    <nav v-if="!isAuthPage" class="navbar">
      <div class="nav-inner">
        <RouterLink to="/" class="brand">
          <span class="brand-icon">&lt;/&gt;</span>
          <span class="brand-text">ACM OJ</span>
        </RouterLink>
        <div class="nav-links">
          <RouterLink to="/problems">题库</RouterLink>
          <RouterLink to="/contests">比赛</RouterLink>
          <RouterLink to="/submissions">评测记录</RouterLink>
          <RouterLink to="/rank">排行榜</RouterLink>
          <RouterLink to="/discussions">讨论</RouterLink>
          <RouterLink to="/learn">算法学习</RouterLink>
          <RouterLink to="/learn/graph">知识图谱</RouterLink>
        </div>
        <div class="nav-user">
          <!-- 主题切换 -->
          <button class="theme-btn" @click="toggleTheme" :title="isDark ? '切换亮色模式' : '切换暗色模式'">
            <!-- 月亮（暗色时显示） -->
            <svg v-if="isDark" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            <!-- 太阳（亮色时显示） -->
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
          </button>

          <template v-if="userStore.isLoggedIn">
            <RouterLink :to="`/users/${userStore.user?.id}`" class="nav-avatar-wrap">
              <span
                class="nav-avatar"
                :style="{ background: userStore.user?.avatar_color || '#4F46E5' }"
              >{{ (userStore.user?.username || '?')[0].toUpperCase() }}</span>
              <span class="username">{{ userStore.user?.username }}</span>
            </RouterLink>
            <button class="btn-logout" @click="logout">退出</button>
          </template>
          <template v-else>
            <RouterLink to="/login" class="btn-link">登录</RouterLink>
            <RouterLink to="/register" class="btn-link btn-reg">注册</RouterLink>
          </template>
        </div>
      </div>
    </nav>

    <main :class="isAuthPage ? 'auth-content' : 'main-content'">
      <RouterView />
    </main>

    <footer v-if="!isAuthPage" class="footer">
      <div class="footer-inner">
        <p>ACM OJ 算法竞赛在线评测平台</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.navbar {
  background: var(--navbar-bg);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: background 0.25s, border-color 0.25s;
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 2rem;
}

/* Logo */
.brand {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  text-decoration: none;
  flex-shrink: 0;
}
.brand-icon {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(124,106,247,0.12);
  border: 1px solid rgba(124,106,247,0.3);
  border-radius: 6px;
  padding: 1px 6px;
}
.brand-text {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.04em;
}

/* Nav links */
.nav-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}
.nav-links a {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.15s;
}
.nav-links a:hover,
.nav-links a.router-link-active {
  color: var(--text-primary);
}

/* User section */
.nav-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.nav-avatar-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
}
.nav-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.username { color: var(--accent); font-size: 0.9rem; }
.btn-logout {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: border-color 0.15s, color 0.15s;
}
.btn-logout:hover { border-color: var(--accent); color: var(--text-primary); }
.theme-btn {
  width: 32px; height: 32px; border-radius: 8px;
  background: none; border: 1px solid var(--border);
  color: var(--text-secondary); cursor: pointer; display: flex;
  align-items: center; justify-content: center;
  transition: border-color 0.15s, color 0.15s;
  flex-shrink: 0;
}
.theme-btn:hover { border-color: var(--accent); color: var(--accent); }
.btn-link { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; transition: color 0.15s; }
.btn-link:hover { color: var(--text-primary); }
.btn-reg {
  background: var(--accent);
  color: #fff !important;
  padding: 0.28rem 0.9rem;
  border-radius: 4px;
  transition: background 0.15s;
}
.btn-reg:hover { background: var(--accent-deep); }

/* Main */
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}
.auth-content {
  padding: 0;
  margin: 0;
}

/* Footer */
.footer {
  border-top: 1px solid var(--border);
  margin-top: 3rem;
  padding: 1.2rem 0;
  transition: border-color 0.25s;
}
.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.82rem;
}
</style>
