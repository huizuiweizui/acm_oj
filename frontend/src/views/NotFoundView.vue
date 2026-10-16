<template>
  <div class="not-found">
    <div class="code">404</div>
    <h2>页面不存在</h2>
    <p>你访问的页面可能已被移除，或链接有误。</p>
    <RouterLink to="/" class="back-btn">返回首页</RouterLink>
  </div>
</template>

<style scoped>
.not-found {
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
