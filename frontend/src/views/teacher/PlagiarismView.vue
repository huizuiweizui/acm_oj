<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPlagiarism, getPlagiarismPair } from '@/api/exam'

const route = useRoute()
const router = useRouter()
const aid = Number(route.params.aid)

const board = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const threshold = ref(0.5)

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await getPlagiarism(aid, threshold.value)
    board.value = data
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '加载失败（需教师/管理员权限）'
  } finally {
    loading.value = false
  }
}

function simClass(s) {
  if (s >= 0.85) return 'sim-high'
  if (s >= 0.65) return 'sim-mid'
  return 'sim-low'
}
function pct(s) { return Math.round(s * 100) }

// 并排对比
const pair = ref(null)
const pairLoading = ref(false)
async function openPair(p, problemTitle) {
  pair.value = { meta: p, problemTitle }
  pairLoading.value = true
  try {
    const { data } = await getPlagiarismPair(aid, p.sub_a, p.sub_b)
    pair.value = { meta: p, problemTitle, ...data }
  } catch {
    pair.value = null
  } finally {
    pairLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="plag">
    <div class="plag-header">
      <button class="btn-back" @click="router.back()">← 返回</button>
      <div class="ph-titles">
        <h1 class="ph-title">代码查重{{ board?.assignment?.title ? '：' + board.assignment.title : '' }}</h1>
        <p class="ph-sub">Winnowing 指纹算法 · 对每位学生最新提交两两比对（已抵抗改名/重排版/改注释）</p>
      </div>
      <div class="thr-box">
        <label>阈值</label>
        <input v-model.number="threshold" type="number" min="0.1" max="1" step="0.05" class="thr-input" />
        <button class="btn-primary" :disabled="loading" @click="load">{{ loading ? '检测中…' : '重新检测' }}</button>
      </div>
    </div>

    <div v-if="loading" class="empty-tip">检测中…</div>
    <div v-else-if="errorMsg" class="empty-tip err">{{ errorMsg }}</div>
    <div v-else-if="!board.report.length" class="empty-tip">
      ✓ 未发现相似度 ≥ {{ pct(board.threshold) }}% 的可疑提交对
    </div>
    <div v-else class="report">
      <div v-for="prob in board.report" :key="prob.problem_id" class="prob-block">
        <div class="prob-title">
          #{{ prob.problem_id }} {{ prob.problem_title }}
          <span class="prob-meta">检测 {{ prob.checked }} 人 · {{ prob.pairs.length }} 对可疑</span>
        </div>
        <div v-for="(p, i) in prob.pairs" :key="i" class="pair-row" @click="openPair(p, prob.problem_title)">
          <div class="pair-names">
            <span class="pname">{{ p.name_a }}</span>
            <span class="vs">⟷</span>
            <span class="pname">{{ p.name_b }}</span>
          </div>
          <div class="sim-bar-wrap">
            <div class="sim-bar" :class="simClass(p.similarity)" :style="{ width: pct(p.similarity) + '%' }"></div>
          </div>
          <span :class="['sim-val', simClass(p.similarity)]">{{ pct(p.similarity) }}%</span>
          <span class="jac">Jaccard {{ pct(p.jaccard) }}%</span>
          <button class="btn-xs">并排对比 →</button>
        </div>
      </div>
    </div>

    <!-- 并排代码对比 -->
    <div v-if="pair" class="modal-overlay" @click.self="pair = null">
      <div class="cmp-modal">
        <div class="cmp-head">
          <div class="cmp-title">
            {{ pair.meta.name_a }} ⟷ {{ pair.meta.name_b }}
            <span class="cmp-prob">{{ pair.problemTitle }}</span>
          </div>
          <div class="cmp-sim" :class="simClass(pair.meta.similarity)">相似度 {{ pct(pair.meta.similarity) }}%</div>
          <button class="btn-secondary" @click="pair = null">关闭</button>
        </div>
        <div v-if="pairLoading" class="empty-tip">加载中…</div>
        <div v-else-if="pair.a" class="cmp-grid">
          <div class="cmp-col">
            <div class="cmp-col-h">{{ pair.meta.name_a }} · {{ pair.a.language }}</div>
            <pre class="code-pre">{{ pair.a.code }}</pre>
          </div>
          <div class="cmp-col">
            <div class="cmp-col-h">{{ pair.meta.name_b }} · {{ pair.b.language }}</div>
            <pre class="code-pre">{{ pair.b.code }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plag { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
.plag-header { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.btn-back { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; flex-shrink: 0; }
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.ph-titles { flex: 1; min-width: 12rem; }
.ph-title { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.ph-sub { font-size: 0.8rem; color: var(--text-muted); margin: 0.2rem 0 0; }
.thr-box { display: flex; align-items: center; gap: 0.5rem; }
.thr-box label { font-size: 0.82rem; color: var(--text-secondary); }
.thr-input { width: 4.5rem; background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px; padding: 0.4rem 0.5rem; color: var(--text-primary); font-size: 0.85rem; }
.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.45rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }

.report { display: flex; flex-direction: column; gap: 1.25rem; }
.prob-block { display: flex; flex-direction: column; gap: 0.5rem; }
.prob-title { font-weight: 700; color: var(--text-primary); font-size: 0.95rem; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
.prob-meta { font-size: 0.78rem; color: var(--text-muted); font-weight: 400; margin-left: 0.5rem; }
.pair-row { display: flex; align-items: center; gap: 0.85rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 0.9rem; cursor: pointer; transition: border-color 0.15s; }
.pair-row:hover { border-color: var(--accent); }
.pair-names { display: flex; align-items: center; gap: 0.5rem; min-width: 12rem; }
.pname { color: var(--text-primary); font-weight: 500; font-size: 0.9rem; }
.vs { color: var(--text-muted); }
.sim-bar-wrap { flex: 1; height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden; min-width: 4rem; }
.sim-bar { height: 100%; border-radius: 4px; }
.sim-val { font-weight: 700; font-family: monospace; width: 3rem; text-align: right; }
.jac { font-size: 0.75rem; color: var(--text-muted); white-space: nowrap; }
.sim-high { color: #f87171; }
.sim-bar.sim-high { background: #ef4444; }
.sim-mid { color: #f59e0b; }
.sim-bar.sim-mid { background: #f59e0b; }
.sim-low { color: #facc15; }
.sim-bar.sim-low { background: #eab308; }
.btn-xs { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.78rem; white-space: nowrap; }
.pair-row:hover .btn-xs { border-color: var(--accent); color: var(--accent); }

.empty-tip { text-align: center; padding: 3rem; color: var(--text-muted); }
.empty-tip.err { color: #f87171; }

/* 并排对比弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; z-index: 200; padding: 1.5rem; }
.cmp-modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; width: 1000px; max-width: 96vw; max-height: 90vh; display: flex; flex-direction: column; gap: 0.85rem; }
.cmp-head { display: flex; align-items: center; gap: 1rem; }
.cmp-title { flex: 1; font-weight: 700; color: var(--text-primary); }
.cmp-prob { font-size: 0.8rem; color: var(--text-muted); font-weight: 400; margin-left: 0.5rem; }
.cmp-sim { font-weight: 700; font-family: monospace; }
.btn-secondary { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.cmp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; overflow: hidden; }
.cmp-col { display: flex; flex-direction: column; gap: 0.4rem; min-width: 0; }
.cmp-col-h { font-size: 0.82rem; color: var(--text-secondary); font-weight: 600; }
.code-pre { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem; margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.5; color: var(--text-primary); overflow: auto; max-height: 65vh; white-space: pre; }
</style>
