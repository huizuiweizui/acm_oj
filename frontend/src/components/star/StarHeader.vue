<script setup>
import { ACCENTS, accentChoices, canZoomIn, canZoomOut, changeFont, chooseAccent, starUi } from './starUi'

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
        <!-- 只有问卷里说"需要调字号"的学生才有 -->
        <span v-if="starUi.ui?.font_adjust" class="tool-group" role="group" aria-label="字的大小">
          <button type="button" class="tool-btn" :disabled="!canZoomOut" aria-label="字变小" @click="changeFont(-1)">A−</button>
          <button type="button" class="tool-btn" :disabled="!canZoomIn" aria-label="字变大" @click="changeFont(1)">A+</button>
        </span>
        <!-- 只有问卷里说"想自己选颜色"的学生才有 -->
        <span v-if="starUi.ui?.color_choice" class="tool-group" role="radiogroup" aria-label="换颜色">
          <button
            v-for="k in accentChoices"
            :key="k"
            type="button"
            role="radio"
            class="color-dot"
            :class="{ 'is-on': (starUi.accent || starUi.ui.accent) === k }"
            :style="{ background: ACCENTS[k].accent }"
            :aria-checked="(starUi.accent || starUi.ui.accent) === k"
            :aria-label="ACCENTS[k].name"
            :title="ACCENTS[k].name"
            @click="chooseAccent(k)"
          ></button>
        </span>
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
  color: var(--s-accent-ink, var(--s-accent));
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
.tool-group { display: inline-flex; align-items: center; gap: 6px; }
.tool-btn {
  min-width: 44px;
  min-height: 40px;
  border: 2px solid var(--s-border-strong);
  border-radius: var(--s-radius, 6px);
  background: var(--s-card);
  color: var(--s-text);
  font: inherit;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}
.tool-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.color-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 3px solid var(--s-card);
  box-shadow: 0 0 0 1px var(--s-border-strong);
  cursor: pointer;
  padding: 0;
}
.color-dot.is-on { box-shadow: 0 0 0 3px var(--s-text); }
@media (max-width: 600px) {
  .star-header-inner { padding: 0 12px; gap: 10px; flex-wrap: wrap; }
  .star-header-right { gap: 10px; }
}
</style>
