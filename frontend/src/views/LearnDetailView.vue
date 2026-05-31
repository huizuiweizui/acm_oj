<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const algo = ref(null)
const loading = ref(true)
const notFound = ref(false)
const codeLang = ref('C++')
const CODE_LANGS = ['C++', 'Java', 'Python']

function diffClass(d) {
  if (d === '入门') return 'diff-beginner'
  if (d === '提高') return 'diff-intermediate'
  return 'diff-advanced'
}

onMounted(async () => {
  try {
    const res = await fetch(`/api/algorithms/${route.params.id}/`)
    if (res.status === 404) { notFound.value = true; return }
    algo.value = await res.json()
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="learn-detail-page">

    <div v-if="loading" class="state-box">
      <div class="spinner"></div>
      <p>加载中…</p>
    </div>

    <div v-else-if="notFound" class="state-box">
      <div class="nd-icon">🔍</div>
      <p>找不到该算法</p>
      <button class="back-btn" @click="router.push('/learn')">返回列表</button>
    </div>

    <template v-else>
      <!-- 面包屑 -->
      <div class="breadcrumb">
        <span class="bc-link" @click="router.push('/learn')">算法学习</span>
        <span class="bc-sep">/</span>
        <span class="bc-cur">{{ algo.name }}</span>
      </div>

      <!-- 标题区 -->
      <div class="detail-header">
        <div class="detail-title">{{ algo.name }}</div>
        <div class="detail-title-en">{{ algo.name_en }}</div>
        <div class="detail-meta">
          <span class="diff-learn" :class="diffClass(algo.difficulty)">{{ algo.difficulty }}</span>
          <span class="cat-pill">{{ algo.category }}</span>
          <button class="practice-btn" @click="router.push({ path: '/problems', query: { tag: algo.name } })">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12l2 2 4-4"/></svg>
            练习相关题目
          </button>
        </div>
      </div>

      <!-- 有详情内容 -->
      <template v-if="algo.description">
        <!-- 简介 -->
        <div class="detail-section">
          <div class="section-hd">算法简介</div>
          <p class="detail-text">{{ algo.description }}</p>
        </div>

        <!-- 步骤 -->
        <div class="detail-section" v-if="algo.steps && algo.steps.length">
          <div class="section-hd">执行步骤</div>
          <ol class="steps-list">
            <li v-for="s in algo.steps" :key="s">{{ s }}</li>
          </ol>
        </div>

        <!-- 复杂度 -->
        <div class="detail-section" v-if="algo.complexity && algo.complexity.length">
          <div class="section-hd">时空复杂度</div>
          <table class="complexity-table">
            <thead><tr><th>情况</th><th>时间复杂度</th><th>空间复杂度</th></tr></thead>
            <tbody>
              <tr v-for="r in algo.complexity" :key="r.case">
                <td>{{ r.case }}</td><td>{{ r.time }}</td><td>{{ r.space }}</td>
              </tr>
            </tbody>
          </table>
          <div class="stable-tag" v-if="algo.stable !== null">
            {{ algo.stable ? '✓ 稳定排序' : '✗ 不稳定排序' }}
          </div>
        </div>

        <!-- 代码 -->
        <div class="detail-section" v-if="algo.codes && Object.keys(algo.codes).length">
          <div class="section-hd">参考代码</div>
          <div class="code-tabs">
            <div class="code-tab-bar">
              <button
                v-for="lang in CODE_LANGS" :key="lang"
                class="code-tab" :class="{ active: codeLang === lang }"
                @click="codeLang = lang"
              >{{ lang }}</button>
            </div>
            <div class="code-body" v-if="algo.codes[codeLang]">
              <pre><code>{{ algo.codes[codeLang] }}</code></pre>
            </div>
            <div class="code-empty" v-else>暂无该语言的参考代码</div>
          </div>
        </div>
      </template>

      <!-- 无详情时 -->
      <div class="no-detail" v-else>
        <div class="nd-icon">📝</div>
        <p>该算法的详细内容正在整理中，敬请期待</p>
        <p class="nd-desc">{{ algo.desc }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.learn-detail-page { max-width: 860px; padding: 2rem 0 4rem; }

/* 加载 / 404 */
.state-box { text-align: center; padding: 6rem 1rem; color: var(--text-muted); }
.spinner {
  width: 36px; height: 36px; margin: 0 auto 1rem;
  border: 3px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.nd-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
.back-btn {
  margin-top: 1rem; padding: 8px 20px; border-radius: 20px;
  border: 1px solid var(--accent); background: rgba(124,106,247,0.1);
  color: var(--accent); font-size: 0.88rem; cursor: pointer;
}

/* 面包屑 */
.breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 0.87rem; margin-bottom: 1.5rem; }
.bc-link { color: var(--accent); cursor: pointer; }
.bc-link:hover { text-decoration: underline; }
.bc-sep { color: var(--border); }
.bc-cur { color: var(--text-primary); font-weight: 500; }

/* 标题 */
.detail-header { margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
.detail-title    { font-size: 2rem; font-weight: 800; color: var(--text-primary); margin-bottom: 4px; }
.detail-title-en { font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; color: var(--text-muted); margin-bottom: 12px; }
.detail-meta     { display: flex; align-items: center; gap: 10px; }

.diff-learn { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; white-space: nowrap; }
.diff-beginner    { background: rgba(34,197,94,0.12);  color: #22c55e; }
.diff-intermediate{ background: rgba(251,191,36,0.12); color: #f59e0b; }
.diff-advanced    { background: rgba(239,68,68,0.12);  color: #ef4444; }
.cat-pill { font-size: 0.8rem; color: var(--text-muted); padding: 3px 10px; background: var(--bg-input); border-radius: 6px; }

.practice-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 14px; border-radius: 20px; border: 1px solid var(--accent);
  background: rgba(124,106,247,0.1); color: var(--accent);
  font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: background 0.15s, transform 0.15s;
}
.practice-btn:hover { background: rgba(124,106,247,0.2); transform: translateY(-1px); }

/* 章节 */
.detail-section { margin-bottom: 2rem; }
.section-hd {
  font-size: 1rem; font-weight: 700; color: var(--text-primary);
  margin-bottom: 12px; padding-left: 10px; border-left: 3px solid var(--accent);
}
.detail-text { color: var(--text-secondary); line-height: 1.8; font-size: 0.92rem; margin: 0; }

/* 步骤 */
.steps-list { list-style: none; counter-reset: step-counter; padding: 0; display: flex; flex-direction: column; gap: 6px; margin: 0; }
.steps-list li {
  counter-increment: step-counter;
  display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 14px; background: var(--bg-input); border-radius: 8px;
  font-size: 0.88rem; color: var(--text-secondary);
}
.steps-list li::before {
  content: counter(step-counter);
  min-width: 22px; height: 22px;
  background: linear-gradient(135deg, var(--accent), #22d3ee);
  color: #fff; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.72rem; font-weight: 700; flex-shrink: 0; margin-top: 1px;
}

/* 复杂度 */
.complexity-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.complexity-table th { padding: 10px 14px; text-align: left; background: var(--bg-input); color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border); }
.complexity-table td { padding: 10px 14px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
.complexity-table td:not(:first-child) { font-family: 'JetBrains Mono', monospace; color: var(--accent); }
.complexity-table tr:last-child td { border-bottom: none; }
.stable-tag { margin-top: 8px; font-size: 0.82rem; color: var(--text-muted); }

/* 代码 */
.code-tabs { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.code-tab-bar { display: flex; border-bottom: 1px solid var(--border); background: var(--bg-input); }
.code-tab {
  padding: 8px 18px; background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-muted); font-size: 0.85rem; cursor: pointer; transition: all 0.15s; margin-bottom: -1px;
}
.code-tab:hover { color: var(--text-primary); }
.code-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.code-body pre { margin: 0; padding: 1.2rem 1.4rem; background: #12121e; overflow-x: auto; max-height: 480px; }
.code-body code { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.85rem; color: #c8d0e0; line-height: 1.65; }
.code-empty { padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.88rem; }

/* 无详情 */
.no-detail { text-align: center; padding: 3rem 1rem; }
.no-detail p { color: var(--text-muted); margin: 0.5rem 0; }
.nd-desc { font-size: 0.88rem; max-width: 480px; margin: 0.5rem auto 0; line-height: 1.7; }
</style>
