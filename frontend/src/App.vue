<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

function logout() {
  userStore.logout()
  router.push('/')
}
</script>

<template>
  <div id="app">
    <nav class="navbar">
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
        </div>
        <div class="nav-user">
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

    <main class="main-content">
      <RouterView />
    </main>

    <footer class="footer">
      <div class="footer-inner">
        <p>ACM OJ 算法竞赛在线评测平台</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.navbar {
  background: #1a1a2e;
  border-bottom: 1px solid #2d2d4e;
  position: sticky;
  top: 0;
  z-index: 100;
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
  color: #7c6af7;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(124,106,247,0.12);
  border: 1px solid rgba(124,106,247,0.3);
  border-radius: 6px;
  padding: 1px 6px;
}
.brand-text {
  font-size: 1.1rem;
  font-weight: 700;
  color: #e0e0f0;
  letter-spacing: 0.04em;
}

/* Nav links */
.nav-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}
.nav-links a {
  color: #c8c8d4;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.15s;
}
.nav-links a:hover,
.nav-links a.router-link-active {
  color: #fff;
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
.username { color: #a78bfa; font-size: 0.9rem; }
.btn-logout {
  background: none;
  border: 1px solid #3d3d5c;
  color: #c8c8d4;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-logout:hover { border-color: #7c6af7; color: #fff; }
.btn-link { color: #c8c8d4; text-decoration: none; font-size: 0.9rem; }
.btn-link:hover { color: #fff; }
.btn-reg {
  background: #7c6af7;
  color: #fff !important;
  padding: 0.28rem 0.9rem;
  border-radius: 4px;
}
.btn-reg:hover { background: #6c5ae7; }

/* Main */
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}

/* Footer */
.footer {
  border-top: 1px solid #2d2d4e;
  margin-top: 3rem;
  padding: 1.2rem 0;
}
.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  text-align: center;
  color: #555;
  font-size: 0.82rem;
}
</style>
