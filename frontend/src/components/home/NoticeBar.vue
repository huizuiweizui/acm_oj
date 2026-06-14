<script setup>
defineProps({
  message: { type: String, default: '' }
})
</script>

<template>
  <div v-if="message" class="notice-bar">
    <svg class="icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"/>
    </svg>
    <span class="text">{{ message }}</span>
  </div>
</template>

<style scoped>
.notice-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--home-accent-light);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.icon {
  width: 14px;
  height: 14px;
  color: var(--home-accent);
  flex-shrink: 0;
}
.text {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
