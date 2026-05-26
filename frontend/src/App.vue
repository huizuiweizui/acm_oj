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
        <RouterLink to="/" class="brand">ACM OJ</RouterLink>
        <div class="nav-links">
          <RouterLink to="/problems">题库</RouterLink>
          <RouterLink to="/contests">比赛</RouterLink>
          <RouterLink to="/rank">排行榜</RouterLink>
          <RouterLink to="/discussions">讨论</RouterLink>
        </div>
        <div class="nav-user">
          <template v-if="userStore.isLoggedIn">
            <RouterLink :to="`/users/${userStore.user?.id}`" class="username">
              {{ userStore.user?.username }}
            </RouterLink>
            <button class="btn-logout" @click="logout">退出</button>
          </template>
          <template v-else>
            <RouterLink to="/login" class="btn-link">登录</RouterLink>
            <RouterLink to="/register" class="btn-link btn-primary">注册</RouterLink>
          </template>
        </div>
      </div>
    </nav>

    <main class="main-content">
      <RouterView />
    </main>
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
.brand {
  font-size: 1.25rem;
  font-weight: 700;
  color: #7c6af7;
  text-decoration: none;
  letter-spacing: 0.05em;
}
.nav-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}
.nav-links a, .nav-user a {
  color: #c8c8d4;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.15s;
}
.nav-links a:hover,
.nav-links a.router-link-active,
.nav-user a:hover {
  color: #fff;
}
.nav-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.username { color: #a78bfa; }
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
.btn-link { font-size: 0.9rem; }
.btn-primary {
  background: #7c6af7;
  color: #fff !important;
  padding: 0.3rem 0.9rem;
  border-radius: 4px;
}
.btn-primary:hover { background: #6c5ae7; }
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}
</style>
