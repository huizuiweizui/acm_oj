<script setup>
defineProps({
  nickname: { type: String, default: '' },
  title: { type: String, default: '' },
})
</script>

<template>
  <header class="star-header">
    <div class="star-header-inner">
      <RouterLink to="/star" class="star-brand"><span aria-hidden="true">★</span> 星语</RouterLink>
      <span v-if="title" class="star-header-title">{{ title }}</span>
      <span class="star-header-right">
        <span v-if="nickname" class="star-nick">{{ nickname }}</span>
        <RouterLink to="/" class="star-leave">离开星语</RouterLink>
      </span>
    </div>
  </header>
</template>

<style scoped>
.star-header {
  background: var(--s-card);
  border-bottom: 1px solid var(--s-border);
}
.star-header-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 20px;
}
.star-brand {
  font-size: 22px;
  font-weight: 700;
  color: var(--s-accent);
  text-decoration: none;
  white-space: nowrap;
}
.star-header-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.star-header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 18px;
  white-space: nowrap;
}
.star-nick { font-weight: 600; }
.star-leave {
  font-size: 16px;
  color: var(--s-text-2);
}
</style>
