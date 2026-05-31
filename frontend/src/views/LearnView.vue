<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const CATEGORIES = ['全部', '基础算法', '排序', '搜索', '贪心', '动态规划', '图论', '数据结构', '字符串', '数学']

// ── 状态 ─────────────────────────────────────────────────────
const router = useRouter()
const algorithms = ref([])
const keyword = ref('')
const activeCategory = ref('全部')

function diffClass(d) {
  if (d === '入门') return 'diff-beginner'
  if (d === '提高') return 'diff-intermediate'
  return 'diff-advanced'
}

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return algorithms.value.filter(a => {
    const catOk = activeCategory.value === '全部' || a.category === activeCategory.value
    const kwOk = !kw || a.name.toLowerCase().includes(kw) || a.name_en.toLowerCase().includes(kw)
    return catOk && kwOk
  })
})

function openDetail(algo) {
  router.push({ name: 'learn-detail', params: { id: algo.algo_id } })
}

// ── 视差 Hero ────────────────────────────────────────────────
const heroRef = ref(null)
let onScroll = null
onMounted(async () => {
  const res = await fetch('/api/algorithms/')
  algorithms.value = await res.json()

  onScroll = () => {
    if (!heroRef.value) return
    const el = heroRef.value.querySelector('.hero-parallax-bg')
    if (el) el.style.transform = `translateY(${window.scrollY * 0.3}px)`
  }
  window.addEventListener('scroll', onScroll, { passive: true })
})
onUnmounted(() => { if (onScroll) window.removeEventListener('scroll', onScroll) })
</script>

<template>
  <div class="learn-page">

    <!-- ===== 列表视图 ===== -->
    <div>

      <!-- Hero -->
      <div class="learn-hero" ref="heroRef">
        <div class="hero-parallax-bg">
          <div class="hero-grad"></div>
          <svg class="deco-hex" style="left:-4%;top:-30%;width:50%;" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="hexA" x="0" y="0" width="52" height="60" patternUnits="userSpaceOnUse"><polygon points="26,2 50,15 50,45 26,58 2,45 2,15" fill="none" stroke="#7c6af7" stroke-width="1.2"/></pattern></defs>
            <rect width="400" height="400" fill="url(#hexA)"/>
          </svg>
          <svg class="deco-hex" style="right:-6%;bottom:-40%;width:42%;opacity:0.05;" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="hexB" x="0" y="0" width="52" height="60" patternUnits="userSpaceOnUse"><polygon points="26,2 50,15 50,45 26,58 2,45 2,15" fill="none" stroke="#22d3ee" stroke-width="1.2"/></pattern></defs>
            <rect width="300" height="300" fill="url(#hexB)"/>
          </svg>
          <span class="code-float" style="left:7%;top:22%">O(n log n)</span>
          <span class="code-float" style="right:14%;top:28%">dp[i][j] = dp[i-1][j-1] + 1</span>
          <span class="code-float" style="left:22%;bottom:26%">BFS / DFS</span>
          <span class="code-float" style="right:9%;bottom:32%">while (l &lt;= r)</span>
          <span class="code-float" style="left:48%;top:18%">Dijkstra</span>
        </div>
        <div class="hero-content">
          <h1 class="learn-hero-title">算法学习</h1>
          <p class="learn-hero-sub">从原理到实战，系统掌握每一个算法<br>边学习、边刷题，稳步提升竞赛实力</p>
        </div>
      </div>

      <!-- 控制区 -->
      <div class="learn-controls">
        <div class="search-row">
          <div class="search-wrapper">
            <svg class="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="keyword" class="search-input" placeholder="搜索算法名称…" />
          </div>
        </div>
        <div class="category-bar">
          <span
            v-for="cat in CATEGORIES" :key="cat"
            class="cat-tag" :class="{ active: activeCategory === cat }"
            @click="activeCategory = cat"
          >{{ cat }}</span>
        </div>
      </div>

      <!-- 卡片网格 -->
      <div class="algo-section">
        <div class="algo-grid">
          <div
            v-for="algo in filtered" :key="algo.algo_id"
            class="algo-card"
            @click="openDetail(algo)"
          >
            <div class="algo-card-header">
              <div>
                <div class="algo-name">{{ algo.name }}</div>
                <div class="algo-name-en">{{ algo.name_en }}</div>
              </div>
              <span class="diff-learn" :class="diffClass(algo.difficulty)">{{ algo.difficulty }}</span>
            </div>
            <p class="algo-desc">{{ algo.desc }}</p>
            <div class="algo-footer">
              <span class="algo-category-tag">{{ algo.category }}</span>
              <svg class="algo-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
          </div>
        </div>
        <div v-if="filtered.length === 0" class="learn-empty">
          <div class="learn-empty-icon">🔍</div>
          <p>没有找到匹配的算法</p>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.learn-page { padding: 0; }

/* ── Hero ─────────────────────────────────── */
.learn-hero {
  position: relative; height: 300px; overflow: hidden;
  display: flex; align-items: center; justify-content: center; text-align: center;
  margin-bottom: 0;
}
.learn-hero::after {
  content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 100px;
  background: linear-gradient(to bottom, transparent, var(--bg-primary));
  z-index: 3; pointer-events: none;
}
.hero-parallax-bg {
  position: absolute; inset: -80px 0 0 0; pointer-events: none; overflow: hidden;
}
.hero-grad {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(124,106,247,0.14) 0%, rgba(34,211,238,0.07) 50%, transparent 100%);
}
.deco-hex { position: absolute; opacity: 0.07; }
.code-float {
  position: absolute; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
  color: #7c6af7; opacity: 0.22; white-space: nowrap;
  animation: floatY 7s ease-in-out infinite;
}
.code-float:nth-child(2) { animation-delay: -2.5s; animation-duration: 9s; }
.code-float:nth-child(3) { animation-delay: -5s;   animation-duration: 6.5s; }
.code-float:nth-child(4) { animation-delay: -1s;   animation-duration: 8.5s; }
.code-float:nth-child(5) { animation-delay: -3.5s; animation-duration: 7.5s; }
@keyframes floatY { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }

.hero-content { position: relative; z-index: 2; padding: 0 24px; }
.learn-hero-title {
  font-size: 2.8rem; font-weight: 800;
  background: linear-gradient(135deg, #7c6af7 0%, #22d3ee 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  margin-bottom: 10px;
}
.learn-hero-sub { color: var(--text-muted); font-size: 1rem; line-height: 1.7; margin: 0; }

/* ── 控制区 ─────────────────────────────────── */
.learn-controls {
  position: sticky; top: 56px; z-index: 50;
  background: var(--bg-primary); padding: 12px 0 10px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
}
.search-row { margin-bottom: 8px; }
.search-wrapper { position: relative; max-width: 360px; }
.search-icon { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }
.search-input {
  width: 100%; padding: 8px 14px 8px 36px;
  background: var(--bg-input); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 8px;
  font-size: 0.88rem; outline: none; transition: border-color 0.15s;
}
.search-input:focus { border-color: var(--accent); }

.category-bar { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; padding: 2px 0 4px; }
.category-bar::-webkit-scrollbar { display: none; }
.cat-tag {
  flex-shrink: 0; padding: 5px 16px; border-radius: 20px;
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text-muted); font-size: 0.83rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s; white-space: nowrap;
}
.cat-tag:hover  { border-color: var(--accent); color: var(--accent); }
.cat-tag.active { border-color: var(--accent); color: var(--accent); background: rgba(124,106,247,0.12); font-weight: 600; }

/* ── 卡片网格 ────────────────────────────────── */
.algo-section { padding: 0 0 4rem; }
.algo-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
}
.algo-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 18px 20px;
  cursor: pointer; position: relative; overflow: hidden;
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.algo-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #7c6af7, #22d3ee);
  transform: scaleX(0); transform-origin: left; transition: transform 0.3s;
}
.algo-card:hover { border-color: var(--accent); transform: translateY(-3px); box-shadow: 0 8px 24px rgba(124,106,247,0.15); }
.algo-card:hover::before { transform: scaleX(1); }

.algo-card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.algo-name    { font-size: 0.97rem; font-weight: 600; color: var(--text-primary); }
.algo-name-en { font-size: 0.72rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
.algo-desc    { font-size: 0.82rem; color: var(--text-muted); line-height: 1.55; margin: 6px 0 10px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.algo-footer  { display: flex; align-items: center; justify-content: space-between; }
.algo-category-tag { font-size: 0.72rem; color: var(--text-muted); padding: 2px 7px; background: var(--bg-input); border-radius: 4px; }
.algo-arrow   { color: var(--text-muted); }

.diff-learn { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; white-space: nowrap; }
.diff-beginner    { background: rgba(34,197,94,0.12);  color: #22c55e; }
.diff-intermediate{ background: rgba(251,191,36,0.12); color: #f59e0b; }
.diff-advanced    { background: rgba(239,68,68,0.12);  color: #ef4444; }

.learn-empty { text-align: center; padding: 4rem; color: var(--text-muted); }
.learn-empty-icon { font-size: 2.5rem; margin-bottom: 10px; opacity: 0.4; }

@media (max-width: 1100px) { .algo-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px)  { .algo-grid { grid-template-columns: repeat(2, 1fr); } .learn-hero-title { font-size: 2rem; } }
@media (max-width: 480px)  { .algo-grid { grid-template-columns: 1fr; } }
</style>
