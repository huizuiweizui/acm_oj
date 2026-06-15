<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import api from '@/api/index'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()

const algo = ref(null)
const loading = ref(true)
const notFound = ref(false)
const codeLang = ref('C++')
const CODE_LANGS = ['C++', 'Java', 'Python']

// 知识笔记
const chunks = ref([])
const chunksLoading = ref(false)

// 个性化学习路径（需登录）
const userStore = useUserStore()
const learningPath = ref([])
async function loadPath(id) {
  learningPath.value = []
  if (!userStore.isLoggedIn) return
  try {
    const { data } = await api.get(`/algorithms/${id}/learning-path/`)
    learningPath.value = data.path || []
  } catch {
    learningPath.value = []
  }
}

// 过滤掉不适合直接展示的章节
const SKIP_SECTIONS = new Set(['前置知识', '全文', '相关例题'])
const visibleChunks = ref([])

function diffClass(d) {
  if (d === '入门') return 'diff-beginner'
  if (d === '提高') return 'diff-intermediate'
  return 'diff-advanced'
}

async function loadAlgo(id) {
  loading.value = true
  notFound.value = false
  algo.value = null
  chunks.value = []
  visibleChunks.value = []
  chunksLoading.value = true
  try {
    const [algoRes, chunksRes] = await Promise.all([
      fetch(`/api/algorithms/${id}/`),
      fetch(`/api/algorithms/${id}/chunks/`),
    ])
    if (algoRes.status === 404) { notFound.value = true; return }
    algo.value = await algoRes.json()
    if (chunksRes.ok) {
      const raw = await chunksRes.json()
      const seenSections = new Set()
      visibleChunks.value = raw.filter(c => {
        if (SKIP_SECTIONS.has(c.section)) return false
        if (c.content.trim().length <= 30) return false
        // 过滤掉被 800-token 截断的代码块续集：
        // 续集 chunk 的 section 与上一个重复，且内容以裸代码（空格缩进）开头
        if (seenSections.has(c.section) && /^[ \t]{2,}\S/.test(c.content.trim())) return false
        seenSections.add(c.section)
        return true
      })
    }
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
    chunksLoading.value = false
  }
}

onMounted(() => { loadAlgo(route.params.id); loadPath(route.params.id) })
watch(() => route.params.id, id => { if (id) { loadAlgo(id); loadPath(id) } })

// ── AI 问答抽屉 ───────────────────────────────────────────────
const drawerOpen = ref(false)
const question   = ref('')
const answering  = ref(false)
const inputRef   = ref(null)
const bodyRef    = ref(null)

// 对话历史：[{ role: 'user'|'ai', text: string, done: boolean }]
const messages = ref([])

let abortCtrl = null

function openDrawer() {
  drawerOpen.value = true
  setTimeout(() => inputRef.value?.focus(), 80)
}
function closeDrawer() {
  drawerOpen.value = false
  abortCtrl?.abort()
}

function scrollBottom() {
  setTimeout(() => {
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }, 30)
}

// ESC 关闭
function onKeydown(e) { if (e.key === 'Escape') closeDrawer() }
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => { window.removeEventListener('keydown', onKeydown); abortCtrl?.abort() })

async function ask() {
  const q = question.value.trim()
  if (!q || answering.value) return

  // 推入用户消息，清空输入框
  messages.value.push({ role: 'user', text: q, done: true })
  question.value = ''
  scrollBottom()

  // 推入 AI 占位消息（流式追加）
  const aiMsg = { role: 'ai', text: '', done: false }
  messages.value.push(aiMsg)
  answering.value = true
  scrollBottom()

  abortCtrl = new AbortController()
  try {
    const res = await fetch('/api/ai/ask/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, algo_id: route.params.id }),
      signal: abortCtrl.signal,
    })
    if (!res.ok) { aiMsg.text = '请求失败，请稍后重试。'; aiMsg.done = true; return }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        const data = line.slice(5).trim()
        if (data === '[DONE]') break
        try {
          const obj = JSON.parse(data)
          if (obj.text) { aiMsg.text += obj.text; scrollBottom() }
        } catch { /* ignore */ }
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') aiMsg.text = (aiMsg.text || '') + '\n\n连接中断，请重试。'
  } finally {
    aiMsg.done = true
    answering.value = false
    abortCtrl = null
    scrollBottom()
  }
}

function onEnter(e) {
  if (e.shiftKey) return
  e.preventDefault()
  ask()
}
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

      <!-- 前置知识 -->
      <div class="path-group prereq-top" v-if="algo.prerequisites?.length">
        <div class="path-hd">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 3 12 9 6"/><polyline points="21 18 15 12 21 6"/></svg>
          先学这些
        </div>
        <div class="path-cards">
          <div
            v-for="n in algo.prerequisites" :key="n.algo_id"
            class="path-card prereq-card"
            @click="router.push({ name: 'learn-detail', params: { id: n.algo_id } })"
          >
            <span class="pc-name">{{ n.name }}</span>
            <span class="pc-en">{{ n.name_en }}</span>
            <div class="pc-tags">
              <span class="pc-cat">{{ n.category }}</span>
              <span class="pc-diff" :class="diffClass(n.difficulty)">{{ n.difficulty }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 有详情内容 -->
      <template v-if="algo.description">
        <div class="detail-section" v-if="learningPath.length">
          <div class="section-hd">个性化学习路径</div>
          <div style="display:flex;flex-direction:column;gap:0.6rem;margin-top:0.5rem">
            <div v-for="(node, i) in learningPath" :key="node.algo_id"
                 style="border:1px solid var(--border);border-radius:8px;padding:0.7rem 0.9rem"
                 :style="node.is_target ? 'border-color:var(--accent)' : ''">
              <div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap">
                <span style="width:1.5rem;height:1.5rem;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.78rem;font-weight:700;flex-shrink:0"
                      :style="node.mastered ? 'background:#10b981;color:#fff' : 'background:var(--bg-secondary);color:var(--text-muted)'">
                  {{ node.mastered ? '✓' : i + 1 }}
                </span>
                <span style="font-weight:600;color:var(--text-primary);cursor:pointer" @click="router.push(`/learn/${node.algo_id}`)">{{ node.name }}</span>
                <span style="font-size:0.78rem;color:var(--text-muted)">{{ node.category }}</span>
                <span v-if="node.problem_count" style="font-size:0.78rem;color:var(--text-muted);font-family:monospace">{{ node.solved_count }}/{{ node.problem_count }}</span>
                <span v-if="node.is_target" style="font-size:0.72rem;padding:0.1rem 0.45rem;border-radius:4px;background:rgba(99,102,241,0.15);color:var(--accent)">目标</span>
              </div>
              <div v-if="node.recommend.length" style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.5rem;padding-left:2.1rem">
                <a v-for="p in node.recommend" :key="p.id" :href="`/problems/${p.id}`" target="_blank"
                   style="font-size:0.8rem;color:var(--accent);text-decoration:none;border:1px solid var(--border);border-radius:4px;padding:0.15rem 0.5rem">
                  #{{ p.id }} {{ p.title }}
                </a>
              </div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-hd">算法简介</div>
          <p class="detail-text">{{ algo.description }}</p>
        </div>

        <div class="detail-section" v-if="algo.steps && algo.steps.length">
          <div class="section-hd">执行步骤</div>
          <ol class="steps-list">
            <li v-for="s in algo.steps" :key="s">{{ s }}</li>
          </ol>
        </div>

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

      <div class="no-detail" v-else>
        <div class="nd-icon">📝</div>
        <p>该算法的详细内容正在整理中，敬请期待</p>
        <p class="nd-desc">{{ algo.desc }}</p>
      </div>

      <!-- ── 算法笔记 ── -->
      <div class="detail-section notes-section" v-if="chunksLoading || visibleChunks.length">
        <div class="section-hd">算法笔记</div>
        <div v-if="chunksLoading" class="notes-loading">
          <div class="spinner"></div>
          <span>加载笔记中…</span>
        </div>
        <div v-else class="notes-body">
          <div v-for="(chunk, i) in visibleChunks" :key="i" class="note-chunk">
            <div v-if="chunk.section && chunk.section !== '概述'" class="chunk-section-hd">
              {{ chunk.section }}
            </div>
            <MarkdownRenderer :content="chunk.content" />
          </div>
        </div>
      </div>

      <!-- ── 学习路径（相关算法 + 学完继续） ── -->
      <div
        v-if="algo.related?.length || algo.extends_to?.length"
        class="path-section"
      >
        <div class="path-group" v-if="algo.related?.length">
          <div class="path-hd">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/></svg>
            相关算法
          </div>
          <div class="path-cards">
            <div
              v-for="n in algo.related" :key="n.algo_id"
              class="path-card related-card"
              @click="router.push({ name: 'learn-detail', params: { id: n.algo_id } })"
            >
              <span class="pc-name">{{ n.name }}</span>
              <span class="pc-en">{{ n.name_en }}</span>
              <div class="pc-tags">
                <span class="pc-cat">{{ n.category }}</span>
                <span class="pc-diff" :class="diffClass(n.difficulty)">{{ n.difficulty }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="path-group" v-if="algo.extends_to?.length">
          <div class="path-hd">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 21 12 15 6"/><polyline points="3 18 9 12 3 6"/></svg>
            学完继续
          </div>
          <div class="path-cards">
            <div
              v-for="n in algo.extends_to" :key="n.algo_id"
              class="path-card extends-card"
              @click="router.push({ name: 'learn-detail', params: { id: n.algo_id } })"
            >
              <span class="pc-name">{{ n.name }}</span>
              <span class="pc-en">{{ n.name_en }}</span>
              <div class="pc-tags">
                <span class="pc-cat">{{ n.category }}</span>
                <span class="pc-diff" :class="diffClass(n.difficulty)">{{ n.difficulty }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── 右下角「问 AI」悬浮按钮 ── -->
    <button v-if="!loading && !notFound" class="ask-fab" @click="openDrawer" title="问 AI">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <span>问 AI</span>
    </button>

    <!-- ── AI 问答抽屉 ── -->
    <Transition name="drawer">
      <div v-if="drawerOpen" class="drawer-mask" @click.self="closeDrawer">
        <div class="drawer">
          <!-- 抽屉头部 -->
          <div class="drawer-header">
            <div class="drawer-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              AI 问答
            </div>
            <div class="drawer-context" v-if="algo">正在学习：{{ algo.name }}</div>
            <button class="drawer-close" @click="closeDrawer">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>

          <!-- 对话区 -->
          <div class="drawer-body" ref="bodyRef">
            <!-- 空状态 -->
            <div v-if="messages.length === 0" class="drawer-empty">
              <p>对 <b>{{ algo?.name }}</b> 有任何疑问，都可以在这里提问</p>
              <p class="drawer-hint">基于算法笔记知识库回答 · 代码示例用 C++</p>
            </div>
            <!-- 消息气泡列表 -->
            <template v-else>
              <div
                v-for="(msg, i) in messages" :key="i"
                :class="['msg-row', msg.role === 'user' ? 'msg-user' : 'msg-ai']"
              >
                <!-- AI 头像 -->
                <div v-if="msg.role === 'ai'" class="msg-avatar ai-avatar">AI</div>
                <!-- 气泡 -->
                <div class="msg-bubble">
                  <template v-if="msg.role === 'user'">{{ msg.text }}</template>
                  <template v-else>
                    <MarkdownRenderer :content="msg.text" />
                    <span v-if="!msg.done" class="cursor-blink">▋</span>
                  </template>
                </div>
              </div>
            </template>
          </div>

          <!-- 输入区 -->
          <div class="drawer-footer">
            <textarea
              ref="inputRef"
              v-model="question"
              class="drawer-input"
              placeholder="输入问题…（Enter 发送，Shift+Enter 换行）"
              rows="2"
              :disabled="answering"
              @keydown.enter="onEnter"
            />
            <button
              class="drawer-send"
              :disabled="!question.trim() || answering"
              @click="ask"
            >
              <span v-if="answering" class="send-spinner"></span>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </Transition>
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
.code-body pre { margin: 0; padding: 1.2rem 1.4rem; background: var(--code-bg); overflow-x: auto; max-height: 480px; }
.code-body code { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.65; }
.code-empty { padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.88rem; }

/* 无详情 */
.no-detail { text-align: center; padding: 3rem 1rem; }
.no-detail p { color: var(--text-muted); margin: 0.5rem 0; }
.nd-desc { font-size: 0.88rem; max-width: 480px; margin: 0.5rem auto 0; line-height: 1.7; }

/* ── 算法笔记 ── */
.notes-section { margin-top: 2rem; }
.notes-loading {
  display: flex; align-items: center; gap: 10px;
  color: var(--text-muted); font-size: 0.88rem; padding: 1rem 0;
}
.notes-loading .spinner { width: 18px; height: 18px; margin: 0; border-width: 2px; }
.notes-body { display: flex; flex-direction: column; gap: 1.5rem; }
.note-chunk { }
.chunk-section-hd {
  font-size: 0.95rem; font-weight: 700; color: var(--text-secondary);
  margin-bottom: 8px; padding: 4px 0;
  border-bottom: 1px solid var(--border);
}
/* MarkdownRenderer 在笔记区的细节调整（只覆盖布局，颜色全走 CSS 变量） */
.notes-body :deep(.md-body) { font-size: 0.9rem; line-height: 1.85; }
.notes-body :deep(.md-body h1),
.notes-body :deep(.md-body h2) { display: none; }
.notes-body :deep(.md-body h3) { font-size: 0.9rem; color: var(--text-secondary); margin: 1em 0 0.4em; }
.notes-body :deep(.md-body pre) { padding: 1rem 1.2rem; margin: 0.8em 0; }
.notes-body :deep(.md-body blockquote) {
  border-left: 3px solid var(--accent); margin: 0.8em 0;
  padding: 0.4em 1em; border-radius: 0 6px 6px 0;
}

/* 前置知识（置顶） */
.prereq-top {
  margin-bottom: 2rem;
  padding: 12px 16px;
  background: rgba(248, 113, 113, 0.06);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 10px;
}

/* ── 学习路径 ── */
.path-section {
  margin-top: 2.5rem; padding-top: 2rem;
  border-top: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 1.5rem;
}
.path-group {}
.path-hd {
  display: flex; align-items: center; gap: 7px;
  font-size: 0.88rem; font-weight: 700; color: var(--text-secondary);
  margin-bottom: 10px;
}
.path-cards {
  display: flex; flex-wrap: wrap; gap: 10px;
}
.path-card {
  display: flex; flex-direction: column; gap: 4px;
  padding: 10px 14px; border-radius: 10px;
  border: 1px solid var(--border); background: var(--bg-card);
  cursor: pointer; min-width: 130px; max-width: 180px;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
}
.path-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
.prereq-card:hover  { border-color: #f87171; }
.extends-card:hover { border-color: #a78bfa; }
.related-card:hover { border-color: var(--accent); }

.pc-name { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }
.pc-en   { font-size: 0.72rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pc-tags { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
.pc-cat  { font-size: 0.68rem; color: var(--text-muted); background: var(--bg-input); padding: 1px 6px; border-radius: 4px; }
.pc-diff { font-size: 0.68rem; font-weight: 600; padding: 1px 6px; border-radius: 4px; }
.pc-diff.diff-beginner     { background: rgba(34,197,94,0.12);  color: #22c55e; }
.pc-diff.diff-intermediate { background: rgba(245,158,11,0.12); color: #f59e0b; }
.pc-diff.diff-advanced     { background: rgba(239,68,68,0.12);  color: #ef4444; }

/* ── 问 AI 悬浮按钮 ── */
.ask-fab {
  position: fixed; right: 28px; bottom: 36px; z-index: 200;
  display: flex; align-items: center; gap: 7px;
  padding: 12px 20px; border-radius: 28px;
  background: linear-gradient(135deg, #7c6af7, #22d3ee);
  color: #fff; font-size: 0.92rem; font-weight: 600;
  border: none; cursor: pointer; box-shadow: 0 4px 20px rgba(124,106,247,0.4);
  transition: transform 0.2s, box-shadow 0.2s;
}
.ask-fab:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(124,106,247,0.5); }

/* ── 抽屉遮罩 ── */
.drawer-mask {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(0,0,0,0.35); backdrop-filter: blur(2px);
}

/* ── 抽屉 ── */
.drawer {
  position: absolute; right: 0; top: 0; bottom: 0; width: 420px; max-width: 95vw;
  background: var(--bg-card); border-left: 1px solid var(--border);
  display: flex; flex-direction: column;
  box-shadow: -8px 0 32px rgba(0,0,0,0.25);
}

.drawer-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 18px 12px; border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.drawer-title {
  display: flex; align-items: center; gap: 7px;
  font-size: 0.97rem; font-weight: 700; color: var(--text-primary);
}
.drawer-context {
  flex: 1; font-size: 0.78rem; color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.drawer-close {
  width: 28px; height: 28px; border-radius: 6px; border: none;
  background: var(--bg-input); color: var(--text-muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}
.drawer-close:hover { background: rgba(239,68,68,0.12); color: #ef4444; }

.drawer-body {
  flex: 1; overflow-y: auto; padding: 14px 14px 6px;
  display: flex; flex-direction: column; gap: 14px;
  scroll-behavior: smooth;
}
.drawer-empty { margin: auto; text-align: center; color: var(--text-muted); }
.drawer-empty b { color: var(--text-primary); }
.drawer-hint { font-size: 0.78rem; margin-top: 6px; opacity: 0.65; }

/* 消息行 */
.msg-row { display: flex; align-items: flex-start; gap: 8px; }
.msg-user { flex-direction: row-reverse; }

/* AI 头像 */
.msg-avatar {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.65rem; font-weight: 700; margin-top: 2px;
}
.ai-avatar {
  background: linear-gradient(135deg, #7c6af7, #22d3ee); color: #fff;
}

/* 气泡 */
.msg-bubble {
  max-width: 82%; padding: 10px 13px; border-radius: 12px;
  font-size: 0.88rem; line-height: 1.65; word-break: break-word;
}
.msg-user .msg-bubble {
  background: linear-gradient(135deg, #7c6af7, #5b52d4);
  color: #fff; border-bottom-right-radius: 4px;
}
.msg-ai .msg-bubble {
  background: var(--bg-input); color: var(--text-primary);
  border-bottom-left-radius: 4px;
}
.msg-ai .msg-bubble :deep(.md-body) { font-size: 0.88rem; }
.msg-ai .msg-bubble :deep(.md-body p) { margin: 0.35em 0; }
.msg-ai .msg-bubble :deep(.md-body pre) { font-size: 0.79rem; }
.msg-ai .msg-bubble :deep(.md-body ul),
.msg-ai .msg-bubble :deep(.md-body ol) { padding-left: 1.2em; }
.cursor-blink {
  display: inline-block; color: var(--accent);
  animation: blink 0.9s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

.drawer-footer {
  display: flex; align-items: flex-end; gap: 10px;
  padding: 12px 14px; border-top: 1px solid var(--border); flex-shrink: 0;
}
.drawer-input {
  flex: 1; resize: none;
  background: var(--bg-input); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 10px;
  padding: 9px 12px; font-size: 0.88rem; line-height: 1.5; outline: none;
  transition: border-color 0.15s; font-family: inherit;
}
.drawer-input:focus { border-color: var(--accent); }
.drawer-input:disabled { opacity: 0.5; }

.drawer-send {
  width: 38px; height: 38px; border-radius: 10px; border: none; flex-shrink: 0;
  background: linear-gradient(135deg, #7c6af7, #22d3ee);
  color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: opacity 0.15s, transform 0.15s;
}
.drawer-send:disabled { opacity: 0.4; cursor: default; transform: none; }
.drawer-send:not(:disabled):hover { transform: scale(1.06); }

.send-spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* ── 抽屉动画 ── */
.drawer-enter-active, .drawer-leave-active { transition: opacity 0.2s; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-active .drawer, .drawer-leave-active .drawer { transition: transform 0.25s ease; }
.drawer-enter-from .drawer, .drawer-leave-to .drawer { transform: translateX(100%); }
</style>
