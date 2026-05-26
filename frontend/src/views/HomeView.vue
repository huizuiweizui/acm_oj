<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import api from '@/api/index.js'

use([CanvasRenderer, BarChart, PieChart, TooltipComponent, GridComponent, LegendComponent])

const router = useRouter()
const stats = ref(null)

onMounted(async () => {
  try {
    const res = await api.get('/stats/')
    stats.value = res.data
  } catch {}
})

const STATUS_LABELS = {
  AC: '通过', WA: '答案错误', TLE: '超时',
  MLE: '超内存', RE: '运行错误', CE: '编译错误',
}
const STATUS_COLORS = {
  AC: '#22c55e', WA: '#ef4444', TLE: '#f59e0b',
  MLE: '#8b5cf6', RE: '#f97316', CE: '#6b7280',
}

const dailyOption = computed(() => {
  if (!stats.value) return {}
  const data = stats.value.daily_submissions
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 36, right: 8, top: 8, bottom: 48 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date.slice(5)),
      axisLabel: { color: '#666', fontSize: 10, rotate: 30, interval: 4 },
      axisLine: { lineStyle: { color: '#2d2d4e' } },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLabel: { color: '#666', fontSize: 10 },
      splitLine: { lineStyle: { color: '#1e1e38' } },
    },
    series: [{
      type: 'bar',
      data: data.map(d => ({
        value: d.count,
        itemStyle: { color: '#7c6af7', borderRadius: [3, 3, 0, 0] },
      })),
      barMaxWidth: 18,
    }],
  }
})

const statusOption = computed(() => {
  if (!stats.value) return {}
  const dist = stats.value.submissions_by_status
  const pieData = Object.entries(dist)
    .filter(([k]) => STATUS_LABELS[k])
    .map(([k, v]) => ({
      name: STATUS_LABELS[k],
      value: v,
      itemStyle: { color: STATUS_COLORS[k] },
    }))
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      bottom: 0,
      textStyle: { color: '#888', fontSize: 11 },
      itemWidth: 10, itemHeight: 10,
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '42%'],
      data: pieData,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, color: '#e0e0f0' } },
    }],
  }
})
</script>

<template>
  <div class="home">

    <!-- Hero -->
    <div class="hero">
      <div class="hero-title">ACM <span class="accent">OJ</span></div>
      <div class="hero-sub">算法竞赛在线评测平台 &middot; 代码 &middot; 比赛 &middot; 成长</div>

      <div class="hero-stats" v-if="stats">
        <div class="hstat">
          <div class="hstat-val">{{ stats.total_problems }}</div>
          <div class="hstat-label">道题目</div>
        </div>
        <div class="hstat-div"></div>
        <div class="hstat">
          <div class="hstat-val">{{ stats.total_submissions }}</div>
          <div class="hstat-label">次提交</div>
        </div>
        <div class="hstat-div"></div>
        <div class="hstat">
          <div class="hstat-val">{{ stats.total_users }}</div>
          <div class="hstat-label">位用户</div>
        </div>
      </div>

      <div class="hero-actions">
        <button class="btn-primary" @click="router.push('/problems')">开始刷题</button>
        <button class="btn-secondary" @click="router.push('/contests')">查看比赛</button>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="charts-row" v-if="stats">
      <div class="chart-card">
        <div class="card-title">近 30 天提交趋势</div>
        <VChart :option="dailyOption" autoresize style="height:200px; width:100%" />
      </div>
      <div class="chart-card">
        <div class="card-title">评测结果分布</div>
        <VChart :option="statusOption" autoresize style="height:200px; width:100%" />
      </div>
    </div>

    <!-- 功能入口 -->
    <div class="feature-grid">
      <div class="feature-card" @click="router.push('/problems')">
        <div class="feature-icon-wrap icon-purple"></div>
        <div class="feature-title">题库</div>
        <div class="feature-desc">覆盖入门到 CTSC 难度，Monaco 编辑器在线提交</div>
      </div>
      <div class="feature-card" @click="router.push('/contests')">
        <div class="feature-icon-wrap icon-blue"></div>
        <div class="feature-title">比赛</div>
        <div class="feature-desc">支持 ICPC / IOI 赛制，实时榜单，罚时计算</div>
      </div>
      <div class="feature-card" @click="router.push('/rank')">
        <div class="feature-icon-wrap icon-amber"></div>
        <div class="feature-title">排行榜</div>
        <div class="feature-desc">Rating 积分系统，AC 数与 Rating 双维度榜单</div>
      </div>
      <div class="feature-card" @click="router.push('/discussions')">
        <div class="feature-icon-wrap icon-green"></div>
        <div class="feature-title">讨论区</div>
        <div class="feature-desc">Markdown 发帖，题解交流，关联题目讨论</div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.home { padding: 0; }

/* Hero */
.hero {
  text-align: center;
  padding: 4rem 1rem 3rem;
  background: linear-gradient(180deg, #13132a 0%, #0f0f1e 100%);
  border-radius: 12px;
  margin-bottom: 1.5rem;
  border: 1px solid #2d2d4e;
}
.hero-title {
  font-size: 3rem;
  font-weight: 800;
  color: #e0e0f0;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}
.accent { color: #7c6af7; }
.hero-sub { color: #666; font-size: 1rem; margin-bottom: 2rem; }

.hero-stats {
  display: inline-flex;
  align-items: center;
  background: #1a1a38;
  border: 1px solid #2d2d4e;
  border-radius: 10px;
  padding: 0.8rem 0;
  margin-bottom: 2rem;
}
.hstat { text-align: center; padding: 0 2rem; }
.hstat-val { font-size: 1.6rem; font-weight: 700; color: #a78bfa; }
.hstat-label { font-size: 0.78rem; color: #666; margin-top: 0.1rem; }
.hstat-div { width: 1px; height: 36px; background: #2d2d4e; flex-shrink: 0; }

.hero-actions { display: flex; gap: 1rem; justify-content: center; }
.btn-primary {
  background: #7c6af7; color: #fff;
  border: none; padding: 0.6rem 2rem;
  border-radius: 6px; font-size: 0.95rem; font-weight: 600;
  cursor: pointer; transition: background 0.15s;
}
.btn-primary:hover { background: #6c5ae7; }
.btn-secondary {
  background: transparent; color: #a78bfa;
  border: 1px solid #7c6af7; padding: 0.6rem 2rem;
  border-radius: 6px; font-size: 0.95rem; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.btn-secondary:hover { background: #7c6af720; }

/* 图表 */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.2rem;
  margin-bottom: 1.5rem;
}
.chart-card {
  background: #16162a; border: 1px solid #2d2d4e;
  border-radius: 10px; padding: 1.2rem 1.4rem;
}
.card-title {
  font-size: 0.88rem; font-weight: 700;
  color: #a78bfa; margin-bottom: 0.8rem;
}

/* 功能入口 */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}
.feature-card {
  background: #16162a; border: 1px solid #2d2d4e;
  border-radius: 10px; padding: 1.4rem;
  cursor: pointer; transition: border-color 0.15s, transform 0.15s;
}
.feature-card:hover { border-color: #7c6af7; transform: translateY(-2px); }
.feature-icon-wrap {
  width: 36px; height: 36px; border-radius: 8px; margin-bottom: 0.9rem;
}
.icon-purple { background: #7c6af730; border: 1px solid #7c6af760; }
.icon-blue   { background: #3b82f630; border: 1px solid #3b82f660; }
.icon-amber  { background: #f59e0b30; border: 1px solid #f59e0b60; }
.icon-green  { background: #22c55e30; border: 1px solid #22c55e60; }
.feature-title { font-size: 1rem; font-weight: 700; color: #e0e0f0; margin-bottom: 0.4rem; }
.feature-desc { font-size: 0.82rem; color: #666; line-height: 1.5; }

@media (max-width: 900px) {
  .charts-row { grid-template-columns: 1fr; }
  .feature-grid { grid-template-columns: repeat(2, 1fr); }
  .hero-title { font-size: 2rem; }
}
@media (max-width: 500px) {
  .feature-grid { grid-template-columns: 1fr; }
  .hstat-div { width: 80px; height: 1px; }
}
</style>
