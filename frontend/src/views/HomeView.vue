<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import api from '@/api/index.js'

use([CanvasRenderer, BarChart, PieChart, TooltipComponent, GridComponent, LegendComponent])

const router = useRouter()
const userStore = useUserStore()
const stats = ref(null)
const canvasRef = ref(null)
let animFrame = null

// ── 粒子动画 ──────────────────────────────────────────────────
function startParticles(canvas) {
  const ctx = canvas.getContext('2d')
  let pts = []

  function resize() {
    canvas.width  = canvas.offsetWidth
    canvas.height = canvas.offsetHeight
  }

  function col(a) {
    return `rgba(124,106,247,${a})`
  }

  function init() {
    resize()
    pts = []
    const n = Math.min(60, Math.floor(canvas.width * canvas.height / 10000))
    for (let i = 0; i < n; i++) {
      pts.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 1.8 + 0.6,
      })
    }
  }

  function frame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i]
      p.x += p.vx; p.y += p.vy
      if (p.x < 0 || p.x > canvas.width)  p.vx *= -1
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1
      for (let j = i + 1; j < pts.length; j++) {
        const q = pts[j]
        const dx = p.x - q.x, dy = p.y - q.y
        const d = Math.sqrt(dx * dx + dy * dy)
        if (d < 130) {
          ctx.beginPath()
          ctx.strokeStyle = col((1 - d / 130) * 0.3)
          ctx.lineWidth = 0.7
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(q.x, q.y)
          ctx.stroke()
        }
      }
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = col(0.6)
      ctx.fill()
    }
    animFrame = requestAnimationFrame(frame)
  }

  const onResize = () => init()
  window.addEventListener('resize', onResize, { passive: true })
  init()
  frame()
  return () => {
    window.removeEventListener('resize', onResize)
    if (animFrame) cancelAnimationFrame(animFrame)
  }
}

// ── 数字滚动动画 ──────────────────────────────────────────────
function animateCount(el) {
  const target = parseInt(el.dataset.target, 10) || 0
  if (target === 0) { el.textContent = '0'; return }
  const dur = 1400, t0 = performance.now()
  const step = (now) => {
    const p = Math.min((now - t0) / dur, 1)
    el.textContent = Math.floor((1 - Math.pow(1 - p, 3)) * target).toLocaleString()
    if (p < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

// ── 滚动显现 ─────────────────────────────────────────────────
function setupReveal() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target) }
    })
  }, { threshold: 0.08 })
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el))

  document.querySelectorAll('.feature-card').forEach((c, i) => {
    c.style.transitionDelay = (i * 0.09) + 's'
  })
}

onMounted(async () => {
  // 粒子
  let cleanup = null
  if (canvasRef.value) cleanup = startParticles(canvasRef.value)

  // 数据
  try {
    const res = await api.get('/stats/')
    stats.value = res.data
  } catch {}

  // 数字滚动（等数据渲染后）
  await new Promise(r => setTimeout(r, 50))
  const cntObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { animateCount(e.target); cntObs.unobserve(e.target) }
    })
  }, { threshold: 0.5 })
  document.querySelectorAll('.count-up').forEach(el => cntObs.observe(el))

  setupReveal()

  onUnmounted(() => { if (cleanup) cleanup() })
})

// ── ECharts ──────────────────────────────────────────────────
const STATUS_LABELS = { AC:'通过', WA:'答案错误', TLE:'超时', MLE:'超内存', RE:'运行错误', CE:'编译错误' }
const STATUS_COLORS = { AC:'#22c55e', WA:'#ef4444', TLE:'#f59e0b', MLE:'#8b5cf6', RE:'#f97316', CE:'#6b7280' }

const dailyOption = computed(() => {
  if (!stats.value) return {}
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 36, right: 8, top: 8, bottom: 48 },
    xAxis: {
      type: 'category',
      data: stats.value.daily_submissions.map(d => d.date.slice(5)),
      axisLabel: { color: '#888', fontSize: 10, rotate: 30, interval: 4 },
      axisLine: { lineStyle: { color: 'rgba(128,128,128,0.2)' } },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLabel: { color: '#888', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(128,128,128,0.12)' } },
    },
    series: [{ type: 'bar', data: stats.value.daily_submissions.map(d => ({
      value: d.count, itemStyle: { color: '#7c6af7', borderRadius: [3,3,0,0] },
    })), barMaxWidth: 18 }],
  }
})

const statusOption = computed(() => {
  if (!stats.value) return {}
  const pieData = Object.entries(stats.value.submissions_by_status)
    .filter(([k]) => STATUS_LABELS[k])
    .map(([k, v]) => ({ name: STATUS_LABELS[k], value: v, itemStyle: { color: STATUS_COLORS[k] } }))
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#888', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
    series: [{ type: 'pie', radius: ['45%','70%'], center: ['50%','42%'], data: pieData,
      label: { show: false }, emphasis: { label: { show: true, fontSize: 12 } } }],
  }
})

// ── 状态辅助 ────────────────────────────────────────────────
function statusClass(s) {
  const m = { AC:'ac', WA:'wa', TLE:'tle', MLE:'mle', RE:'re', CE:'ce', Pending:'pending', Judging:'judging' }
  return m[s] || 'pending'
}
function timeAgo(iso) {
  const diff = Date.now() - new Date(iso)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return new Date(iso).toLocaleDateString('zh-CN')
}
function diffClass(d) {
  const m = { '入门':'easy','普及-':'easy','普及/提高-':'medium','普及+/提高':'medium',
    '提高+/省选-':'hard','省选/NOI-':'hard','NOI/NOI+/CTSC':'expert','暂无评定':'unrated' }
  return m[d] || 'unrated'
}
</script>

<template>
  <div class="home">

    <!-- ===== Hero ===== -->
    <section class="hero hero-enhanced">
      <canvas ref="canvasRef" class="hero-canvas"></canvas>

      <!-- 浮动算法文字 -->
      <div class="hero-deco" aria-hidden="true">
        <span class="deco-line" style="top:18%;left:5%;animation-delay:0s">O(n log n)</span>
        <span class="deco-line" style="top:72%;left:4%;animation-delay:1.5s">BFS / DFS</span>
        <span class="deco-line" style="top:22%;right:5%;animation-delay:0.8s">dp[i][j]</span>
        <span class="deco-line" style="top:68%;right:6%;animation-delay:2s">Dijkstra</span>
        <span class="deco-line" style="top:48%;left:8%;animation-delay:2.8s">AC ✓</span>
        <span class="deco-line" style="top:38%;right:9%;animation-delay:3.5s">#include</span>
      </div>

      <div class="hero-content">
        <div class="hero-eyebrow">
          <span class="eyebrow-dot"></span>
          在线算法评测平台
        </div>
        <h1 class="hero-title">ACM <span class="hero-title-hl">OJ</span></h1>
        <p class="hero-subtitle">
          在线算法竞赛评测平台 — 提交代码，即时评测<br>
          支持 ICPC / IOI 赛制比赛
        </p>

        <div class="stats-grid" v-if="stats">
          <div class="stat-card">
            <div class="stat-number count-up" :data-target="stats.total_problems">0</div>
            <div class="stat-label">算法题目</div>
          </div>
          <div class="stat-card">
            <div class="stat-number count-up" :data-target="stats.total_submissions">0</div>
            <div class="stat-label">提交次数</div>
          </div>
          <div class="stat-card">
            <div class="stat-number count-up" :data-target="stats.total_users">0</div>
            <div class="stat-label">注册用户</div>
          </div>
        </div>

        <div class="hero-actions">
          <button class="btn-hero-primary" @click="router.push('/problems')">浏览题库</button>
          <button
            v-if="!userStore.isLoggedIn"
            class="btn-hero-ghost"
            @click="router.push('/register')"
          >立即注册</button>
        </div>
      </div>
    </section>

    <!-- ===== 特性区 ===== -->
    <section class="features-section">
      <div class="section-header">
        <h2 class="section-title">为什么选择 ACM OJ？</h2>
        <p class="section-subtitle">专为算法竞赛设计，提供完整的练习与比赛体验</p>
      </div>
      <div class="features-grid">
        <div class="feature-card reveal">
          <div class="feature-icon fi-blue">⚡</div>
          <h3 class="feature-title">毫秒级评测</h3>
          <p class="feature-desc">沙箱隔离评测引擎，支持 C / C++ / Java / Python，精确到毫秒的时间与内存测量</p>
        </div>
        <div class="feature-card reveal">
          <div class="feature-icon fi-purple">🏆</div>
          <h3 class="feature-title">多种赛制</h3>
          <p class="feature-desc">完整支持 ICPC 罚时赛制与 IOI 得分赛制，实时排行榜自动更新</p>
        </div>
        <div class="feature-card reveal">
          <div class="feature-icon fi-green">🤖</div>
          <h3 class="feature-title">AI 代码分析</h3>
          <p class="feature-desc">集成 DeepSeek 大模型，提交后自动提供代码优化建议与错误原因分析</p>
        </div>
        <div class="feature-card reveal">
          <div class="feature-icon fi-cyan">💬</div>
          <h3 class="feature-title">题目讨论区</h3>
          <p class="feature-desc">每道题目配备专属讨论区，与其他选手交流解题思路，共同进步</p>
        </div>
      </div>
    </section>

    <!-- ===== 图表区 ===== -->
    <div class="charts-row reveal" v-if="stats">
      <div class="chart-card">
        <div class="card-title">近 30 天提交趋势</div>
        <VChart :option="dailyOption" autoresize style="height:200px;width:100%" />
      </div>
      <div class="chart-card">
        <div class="card-title">评测结果分布</div>
        <VChart :option="statusOption" autoresize style="height:200px;width:100%" />
      </div>
    </div>

    <!-- ===== 主内容区 ===== -->
    <div class="home-grid" v-if="stats">

      <!-- 左：比赛 + 题目 -->
      <div class="home-main">

        <!-- 近期比赛 -->
        <div class="card reveal" v-if="stats.active_contests?.length">
          <div class="card-header">
            <h3 class="card-title-sm">🏆 近期比赛</h3>
            <button class="btn-ghost-sm" @click="router.push('/contests')">全部比赛 →</button>
          </div>
          <div
            v-for="c in stats.active_contests" :key="c.id"
            class="contest-row"
            @click="router.push(`/contests/${c.id}`)"
          >
            <div class="contest-row-info">
              <div class="contest-row-title">{{ c.title }}</div>
              <div class="contest-row-meta">{{ c.rule_type }} · {{ c.start_time }} ~ {{ c.end_time }}</div>
            </div>
            <span class="contest-status-tag" :class="c.status">
              {{ c.status === 'running' ? '进行中' : '即将开始' }}
            </span>
          </div>
        </div>

        <!-- 最新题目 -->
        <div class="card reveal">
          <div class="card-header">
            <h3 class="card-title-sm">📋 最新题目</h3>
            <button class="btn-ghost-sm" @click="router.push('/problems')">查看全部 →</button>
          </div>
          <table class="mini-table" v-if="stats.recent_problems?.length">
            <thead>
              <tr><th>#</th><th>题目</th><th>难度</th><th>通过率</th></tr>
            </thead>
            <tbody>
              <tr
                v-for="p in stats.recent_problems" :key="p.id"
                class="mini-row"
                @click="router.push(`/problems/${p.id}`)"
              >
                <td class="mono-cell">{{ p.id }}</td>
                <td class="problem-title-cell">{{ p.title }}</td>
                <td>
                  <span class="diff-badge" :class="diffClass(p.difficulty)">{{ p.difficulty }}</span>
                </td>
                <td class="muted-cell">{{ p.ac_rate }}%</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-inner">暂无题目</div>
        </div>
      </div>

      <!-- 右：快速导航 + 实时评测 -->
      <div class="home-side">

        <!-- 快速导航 -->
        <div class="card reveal">
          <div class="card-header">
            <h3 class="card-title-sm">🚀 快速导航</h3>
          </div>
          <div class="quicknav-list">
            <div class="quicknav-item" @click="router.push('/problems')">
              <span class="qnav-icon" style="background:rgba(129,140,248,0.12)">📚</span>
              <span>全部题库</span>
              <svg class="qnav-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
            <div class="quicknav-item" @click="router.push('/contests')">
              <span class="qnav-icon" style="background:rgba(167,139,250,0.12)">🏆</span>
              <span>参加比赛</span>
              <svg class="qnav-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
            <div class="quicknav-item" @click="router.push('/rank')">
              <span class="qnav-icon" style="background:rgba(52,211,153,0.12)">📊</span>
              <span>查看排行榜</span>
              <svg class="qnav-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
            <div class="quicknav-item" @click="router.push('/discussions')">
              <span class="qnav-icon" style="background:rgba(34,211,238,0.12)">💬</span>
              <span>讨论社区</span>
              <svg class="qnav-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
            <div v-if="!userStore.isLoggedIn" class="quicknav-item" @click="router.push('/register')">
              <span class="qnav-icon" style="background:rgba(251,191,36,0.12)">✨</span>
              <span>立即注册</span>
              <svg class="qnav-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
          </div>
        </div>

        <!-- 实时评测 -->
        <div class="card reveal" v-if="stats.recent_submissions?.length">
          <div class="card-header">
            <div class="live-feed-header">
              <span class="live-dot"></span>
              <h3 class="card-title-sm" style="margin:0">实时评测</h3>
            </div>
          </div>
          <div class="live-list">
            <div
              v-for="s in stats.recent_submissions" :key="s.id"
              class="live-item"
            >
              <div class="live-left">
                <span class="live-avatar" :style="{ background: s.avatar_color }">
                  {{ s.username[0].toUpperCase() }}
                </span>
                <div class="live-info">
                  <RouterLink :to="`/users/${s.user_id}`" class="live-user" @click.stop>
                    {{ s.username }}
                  </RouterLink>
                  <span class="live-problem"> 提交了 </span>
                  <RouterLink :to="`/problems/${s.problem_id}`" class="live-pid" @click.stop>
                    #{{ s.problem_id }}
                  </RouterLink>
                </div>
              </div>
              <div class="live-right">
                <span class="status-dot-badge" :class="statusClass(s.status)">
                  <span class="sdot"></span>{{ s.status }}
                </span>
                <span class="live-time">{{ timeAgo(s.submitted_at) }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
.home { padding: 0; }

/* ── Hero ─────────────────────────────────────── */
.hero-enhanced {
  position: relative;
  text-align: center;
  padding: 5rem 1rem 4rem;
  background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
  border-radius: 12px;
  margin-bottom: 2rem;
  border: 1px solid var(--border);
  overflow: hidden;
}
.hero-canvas {
  position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none;
}
.hero-deco {
  position: absolute; inset: 0; pointer-events: none;
}
.deco-line {
  position: absolute;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  color: rgba(124,106,247,0.25);
  animation: decoFloat 6s ease-in-out infinite;
  white-space: nowrap;
}
@keyframes decoFloat {
  0%, 100% { transform: translateY(0); opacity: 0.25; }
  50%        { transform: translateY(-8px); opacity: 0.45; }
}
.hero-content { position: relative; z-index: 1; }
.hero-eyebrow {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 0.82rem; color: var(--accent); font-weight: 500;
  margin-bottom: 1rem;
}
.eyebrow-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(0.8)} }

.hero-title {
  font-size: 3.5rem; font-weight: 800; color: var(--text-primary);
  letter-spacing: 0.05em; margin-bottom: 0.6rem;
}
.hero-title-hl { color: var(--accent); }
.hero-subtitle { color: var(--text-muted); font-size: 1rem; line-height: 1.7; margin-bottom: 2rem; }

.stats-grid {
  display: inline-flex; align-items: stretch;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; margin-bottom: 2rem; overflow: hidden;
}
.stat-card {
  padding: 1rem 2rem; text-align: center;
  border-right: 1px solid var(--border);
}
.stat-card:last-child { border-right: none; }
.stat-number {
  font-size: 1.8rem; font-weight: 700; color: var(--accent); font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem; }

.hero-actions { display: flex; gap: 1rem; justify-content: center; }
.btn-hero-primary {
  background: var(--accent); color: #fff; border: none;
  padding: 0.65rem 2.2rem; border-radius: 7px;
  font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.15s;
}
.btn-hero-primary:hover { background: var(--accent-deep); }
.btn-hero-ghost {
  background: transparent; color: var(--accent);
  border: 1px solid var(--accent); padding: 0.65rem 2.2rem;
  border-radius: 7px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-hero-ghost:hover { background: rgba(124,106,247,0.1); }

/* ── Features ─────────────────────────────────── */
.features-section { margin-bottom: 2rem; }
.section-header { text-align: center; margin-bottom: 1.6rem; }
.section-title { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem; }
.section-subtitle { font-size: 0.9rem; color: var(--text-muted); }
.features-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.feature-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.4rem;
  opacity: 0; transform: translateY(16px);
  transition: opacity 0.4s ease, transform 0.4s ease, border-color 0.15s;
}
.feature-card.visible { opacity: 1; transform: translateY(0); }
.feature-card:hover { border-color: var(--accent); }
.feature-icon {
  width: 42px; height: 42px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; margin-bottom: 1rem;
}
.fi-blue   { background: rgba(59,130,246,0.15); }
.fi-purple { background: rgba(124,106,247,0.15); }
.fi-green  { background: rgba(34,197,94,0.15); }
.fi-cyan   { background: rgba(34,211,238,0.15); }
.feature-title { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem; }
.feature-desc { font-size: 0.82rem; color: var(--text-muted); line-height: 1.55; }

/* ── Charts ──────────────────────────────────── */
.charts-row {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 1.2rem; margin-bottom: 2rem;
  opacity: 0; transform: translateY(16px);
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.charts-row.visible { opacity: 1; transform: translateY(0); }
.chart-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.2rem 1.4rem;
}
.card-title {
  font-size: 0.88rem; font-weight: 700; color: var(--accent); margin-bottom: 0.8rem;
}

/* ── Home Grid ───────────────────────────────── */
.home-grid {
  display: grid; grid-template-columns: 1fr 340px;
  gap: 1.2rem; align-items: start;
}
.home-main, .home-side { display: flex; flex-direction: column; gap: 1.2rem; }

.card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden;
}
.reveal {
  opacity: 0; transform: translateY(16px);
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.reveal.visible { opacity: 1; transform: translateY(0); }

.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.2rem; border-bottom: 1px solid var(--border);
}
.card-title-sm { font-size: 0.88rem; font-weight: 700; color: var(--accent); margin: 0; }
.btn-ghost-sm {
  background: none; border: none; color: var(--text-muted);
  font-size: 0.8rem; cursor: pointer;
}
.btn-ghost-sm:hover { color: var(--accent); }

/* 近期比赛 */
.contest-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1.2rem; border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background 0.12s;
}
.contest-row:last-child { border-bottom: none; }
.contest-row:hover { background: var(--bg-secondary); }
.contest-row-title { font-size: 0.9rem; color: var(--text-primary); font-weight: 500; }
.contest-row-meta { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem; }
.contest-status-tag {
  font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.6rem;
  border-radius: 999px; flex-shrink: 0;
}
.contest-status-tag.running  { background: rgba(34,197,94,.15);  color: #22c55e; }
.contest-status-tag.upcoming { background: rgba(99,102,241,.15); color: #6366f1; }

/* 最新题目 */
.mini-table { width: 100%; border-collapse: collapse; }
.mini-table th {
  padding: 0.5rem 1rem; font-size: 0.75rem; color: var(--text-muted);
  text-align: left; border-bottom: 1px solid var(--border); background: var(--bg-secondary);
}
.mini-table td { padding: 0.6rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
.mini-row:last-child td { border-bottom: none; }
.mini-row { cursor: pointer; transition: background 0.12s; }
.mini-row:hover td { background: var(--bg-secondary); }
.mono-cell { color: var(--text-muted); font-size: 0.8rem; }
.problem-title-cell { color: var(--accent); }
.muted-cell { color: var(--text-muted); font-size: 0.82rem; }
.empty-inner { padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.88rem; }

/* 难度徽章 */
.diff-badge {
  font-size: 0.7rem; padding: 0.1rem 0.5rem; border-radius: 4px; font-weight: 600;
}
.diff-badge.easy    { background: rgba(34,197,94,.15);  color: #22c55e; }
.diff-badge.medium  { background: rgba(251,191,36,.15); color: #f59e0b; }
.diff-badge.hard    { background: rgba(239,68,68,.15);  color: #ef4444; }
.diff-badge.expert  { background: rgba(139,92,246,.15); color: #8b5cf6; }
.diff-badge.unrated { background: rgba(107,114,128,.15);color: #6b7280; }

/* 快速导航 */
.quicknav-list { display: flex; flex-direction: column; }
.quicknav-item {
  display: flex; align-items: center; gap: 0.8rem;
  padding: 0.75rem 1.2rem; cursor: pointer; font-size: 0.88rem; color: var(--text-secondary);
  border-bottom: 1px solid var(--border); transition: background 0.12s;
}
.quicknav-item:last-child { border-bottom: none; }
.quicknav-item:hover { background: var(--bg-secondary); color: var(--text-primary); }
.qnav-icon {
  width: 30px; height: 30px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0;
}
.qnav-arrow { width: 14px; height: 14px; opacity: 0.4; margin-left: auto; flex-shrink: 0; }

/* 实时评测 */
.live-feed-header { display: flex; align-items: center; gap: 0.5rem; }
.live-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #22c55e;
  box-shadow: 0 0 6px #22c55e;
  animation: livePulse 1.5s ease-in-out infinite;
}
@keyframes livePulse { 0%,100%{opacity:1} 50%{opacity:.4} }
.live-list { display: flex; flex-direction: column; }
.live-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.65rem 1.2rem; border-bottom: 1px solid var(--border); gap: 0.5rem;
}
.live-item:last-child { border-bottom: none; }
.live-left { display: flex; align-items: center; gap: 0.6rem; flex: 1; min-width: 0; }
.live-avatar {
  width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.68rem; font-weight: 700; color: #fff;
}
.live-info { font-size: 0.82rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.live-user { color: var(--accent); text-decoration: none; font-weight: 600; }
.live-user:hover { text-decoration: underline; }
.live-problem { color: var(--text-muted); }
.live-pid { color: var(--accent); text-decoration: none; }
.live-pid:hover { text-decoration: underline; }
.live-right { display: flex; flex-direction: column; align-items: flex-end; gap: 0.2rem; flex-shrink: 0; }
.live-time { font-size: 0.72rem; color: var(--text-muted); }

/* 状态徽章 */
.status-dot-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.5rem;
  border-radius: 999px;
}
.sdot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.status-dot-badge.ac      { background: rgba(34,197,94,.15);  color: #22c55e; }
.status-dot-badge.wa      { background: rgba(239,68,68,.15);  color: #ef4444; }
.status-dot-badge.tle     { background: rgba(245,158,11,.15); color: #f59e0b; }
.status-dot-badge.mle     { background: rgba(139,92,246,.15); color: #8b5cf6; }
.status-dot-badge.re      { background: rgba(249,115,22,.15); color: #f97316; }
.status-dot-badge.ce      { background: rgba(107,114,128,.15);color: #6b7280; }
.status-dot-badge.pending,
.status-dot-badge.judging { background: rgba(59,130,246,.15); color: #3b82f6; }

/* ── 响应式 ───────────────────────────────────── */
@media (max-width: 1000px) {
  .home-grid { grid-template-columns: 1fr; }
  .features-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
  .charts-row { grid-template-columns: 1fr; }
  .hero-title { font-size: 2.5rem; }
  .features-grid { grid-template-columns: 1fr; }
  .stats-grid { flex-direction: column; }
  .stat-card { border-right: none; border-bottom: 1px solid var(--border); }
  .stat-card:last-child { border-bottom: none; }
}
</style>
