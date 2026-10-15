<script setup>
// 像素网格：障碍、终点、主角（带朝向箭头）、走过的格子。只负责画，不含任何规则。
import { computed } from 'vue'

const props = defineProps({
  level: { type: Object, required: true },
  pos: { type: Object, default: null },        // {x, y, dir}；缺省为起点
  trail: { type: Array, default: () => [] },   // 走过的格子 "x,y"
  bump: { type: Boolean, default: false },      // 撞墙 / 出界时给主角加醒目边框
  maxWidth: { type: Number, default: 520 },
})

const ARROW = { N: '▲', E: '▶', S: '▼', W: '◀' }
const DIR_TEXT = { N: '上', E: '右', S: '下', W: '左' }

const w = computed(() => props.level.grid.w)
const h = computed(() => props.level.grid.h)
const cell = computed(() => Math.min(72, Math.floor(props.maxWidth / w.value)))
const hero = computed(() => props.pos || props.level.start)
const walls = computed(() => new Set((props.level.walls || []).map(([x, y]) => `${x},${y}`)))
const trailSet = computed(() => new Set(props.trail))

const cells = computed(() => {
  const out = []
  for (let y = 0; y < h.value; y++) {
    for (let x = 0; x < w.value; x++) {
      const key = `${x},${y}`
      out.push({
        key,
        wall: walls.value.has(key),
        goal: x === props.level.goal.x && y === props.level.goal.y,
        hero: x === hero.value.x && y === hero.value.y,
        trail: trailSet.value.has(key),
      })
    }
  }
  return out
})

const ariaText = computed(() =>
  `地图 ${w.value} 列 ${h.value} 行。主角在第 ${hero.value.x + 1} 列第 ${hero.value.y + 1} 行，`
  + `面朝${DIR_TEXT[hero.value.dir]}。终点在第 ${props.level.goal.x + 1} 列第 ${props.level.goal.y + 1} 行。`,
)
</script>

<template>
  <div
    class="board"
    role="img"
    :aria-label="ariaText"
    :style="{
      gridTemplateColumns: `repeat(${w}, ${cell}px)`,
      gridTemplateRows: `repeat(${h}, ${cell}px)`,
      fontSize: `${Math.round(cell * 0.55)}px`,
    }"
  >
    <div
      v-for="c in cells"
      :key="c.key"
      class="cell"
      :class="{ 'is-wall': c.wall, 'is-goal': c.goal, 'is-trail': c.trail && !c.hero, 'is-hero': c.hero, 'is-bump': c.hero && bump }"
    >
      <span v-if="c.wall" aria-hidden="true">{{ level.theme?.wall || '🧱' }}</span>
      <span v-else-if="c.goal && !c.hero" aria-hidden="true">{{ level.theme?.goal || '🏁' }}</span>
      <span v-if="c.hero" class="hero" aria-hidden="true">
        {{ level.theme?.hero || '🤖' }}
        <span class="dir">{{ ARROW[hero.dir] }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.board {
  display: grid;
  gap: 3px;
  padding: 3px;
  background: var(--s-border, #d6d3c8);
  border-radius: 8px;
  width: max-content;
  line-height: 1;
}
.cell {
  background: #fbfaf6;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border-radius: 3px;
}
.cell.is-wall { background: #e4e0d4; }
.cell.is-goal { background: #e3f0e7; box-shadow: inset 0 0 0 3px #2e6b45; }
.cell.is-trail { background: #e7eef5; }
.cell.is-hero { background: #fff7e0; box-shadow: inset 0 0 0 3px #2f5f8f; }
.cell.is-bump { background: #f8e6e4; box-shadow: inset 0 0 0 3px #9b2c2c; }
.hero { position: relative; }
.dir {
  position: absolute;
  right: -0.55em;
  bottom: -0.45em;
  font-size: 0.42em;
  color: #fff;
  background: #2f5f8f;
  border-radius: 4px;
  padding: 2px 3px;
}
</style>
