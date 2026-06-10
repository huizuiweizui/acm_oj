<template>
  <div class="forbidden">
    <div class="code">403</div>
    <h2>无访问权限</h2>
    <p>你没有访问该页面的权限。</p>
    <RouterLink to="/" class="back-btn">返回首页</RouterLink>
  </div>
</template>

<style scoped>
.forbidden {
  text-align: center;
  padding: 6rem 0;
  color: var(--text-secondary);
}
.code {
  font-size: 5rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
  margin-bottom: 1rem;
  font-family: 'JetBrains Mono', monospace;
}
h2 { color: var(--text-primary); margin-bottom: 0.5rem; }
p { margin-bottom: 2rem; }
.back-btn {
  display: inline-block;
  padding: 0.5rem 1.5rem;
  background: var(--accent);
  color: #fff;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.9rem;
  transition: background 0.15s;
}
.back-btn:hover { background: var(--accent-hover); }
</style>
