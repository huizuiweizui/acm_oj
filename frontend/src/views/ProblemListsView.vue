<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getProblemLists, createProblemList } from '@/api/lists'

const router = useRouter()
const tab = ref('mine')
const lists = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await getProblemLists({ scope: tab.value })
    lists.value = data
  } finally {
    loading.value = false
  }
}
function switchTab(t) { tab.value = t; load() }

const modal = ref(false)
const form = ref({ title: '', description: '', is_public: true })
const creating = ref(false)
function openCreate() { form.value = { title: '', description: '', is_public: true }; modal.value = true }
async function doCreate() {
  if (!form.value.title.trim()) return
  creating.value = true
  try {
    const { data } = await createProblemList(form.value)
    modal.value = false
    router.push(`/problem-lists/${data.id}`)
  } finally {
    creating.value = false
  }
}
function pct(d) { return d.problem_count ? Math.round(d.solved_count / d.problem_count * 100) : 0 }

onMounted(load)
</script>

<template>
  <div class="pl-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">题单 / 训练计划</h1>
        <p class="page-sub">收藏题目、编排训练，跟踪 AC 进度</p>
      </div>
      <button class="btn-primary" @click="openCreate">＋ 新建题单</button>
    </div>

    <div class="tabs">
      <button :class="['tab', tab === 'mine' && 'tab-active']" @click="switchTab('mine')">我的题单</button>
      <button :class="['tab', tab === 'public' && 'tab-active']" @click="switchTab('public')">公开题单</button>
    </div>

    <div v-if="loading" class="empty-tip">加载中…</div>
    <div v-else-if="lists.length === 0" class="empty-tip">
      {{ tab === 'mine' ? '还没有题单，点击右上角新建' : '暂无公开题单' }}
    </div>
    <div v-else class="pl-grid">
      <div v-for="d in lists" :key="d.id" class="pl-card" @click="router.push(`/problem-lists/${d.id}`)">
        <div class="pl-card-top">
          <span class="pl-card-title">{{ d.title }}</span>
          <span :class="['vis-tag', d.is_public ? 'vis-pub' : 'vis-pri']">{{ d.is_public ? '公开' : '私有' }}</span>
        </div>
        <p v-if="d.description" class="pl-card-desc">{{ d.description }}</p>
        <div class="pl-progress">
          <div class="pl-bar"><div class="pl-fill" :style="{ width: pct(d) + '%' }"></div></div>
          <span class="pl-prog-txt">{{ d.solved_count }} / {{ d.problem_count }}</span>
        </div>
        <div class="pl-card-meta">
          <span v-if="tab === 'public'">@{{ d.owner_username }}</span>
          <span>{{ d.problem_count }} 题</span>
        </div>
      </div>
    </div>

    <div v-if="modal" class="modal-overlay" @click.self="modal = false">
      <div class="modal">
        <h2 class="modal-title">新建题单</h2>
        <input v-model="form.title" class="form-input" placeholder="题单标题" maxlength="200" />
        <textarea v-model="form.description" class="form-textarea" placeholder="简介（可选）" rows="2" />
        <label class="check-label"><input type="checkbox" v-model="form.is_public" /> 公开（其他人可见）</label>
        <div class="modal-actions">
          <button class="btn-secondary" @click="modal = false">取消</button>
          <button class="btn-primary" :disabled="creating || !form.title.trim()" @click="doCreate">
            {{ creating ? '创建中…' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pl-page { max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.25rem; }
.page-sub { color: var(--text-muted); font-size: 0.875rem; margin: 0; }
.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.5rem 1.25rem; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }
.btn-secondary { background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 0.5rem 1.1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }

.tabs { display: flex; border-bottom: 1px solid var(--border); }
.tab { background: none; border: none; border-bottom: 2px solid transparent; padding: 0.6rem 1.25rem; color: var(--text-secondary); cursor: pointer; font-size: 0.9rem; }
.tab:hover { color: var(--text-primary); }
.tab-active { color: var(--accent); border-bottom-color: var(--accent); }

.pl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.1rem; }
.pl-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 1.1rem; cursor: pointer; transition: border-color 0.15s, transform 0.1s; display: flex; flex-direction: column; gap: 0.6rem; }
.pl-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.pl-card-top { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; }
.pl-card-title { font-weight: 600; color: var(--text-primary); }
.vis-tag { font-size: 0.7rem; padding: 0.1rem 0.45rem; border-radius: 4px; flex-shrink: 0; }
.vis-pub { background: #10b98122; color: #10b981; }
.vis-pri { background: rgba(100,100,100,0.12); color: var(--text-muted); border: 1px solid var(--border); }
.pl-card-desc { font-size: 0.82rem; color: var(--text-muted); margin: 0; line-height: 1.4; }
.pl-progress { display: flex; align-items: center; gap: 0.6rem; }
.pl-bar { flex: 1; height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden; }
.pl-fill { height: 100%; background: #10b981; border-radius: 3px; transition: width 0.3s; }
.pl-prog-txt { font-size: 0.78rem; color: var(--text-muted); font-family: monospace; }
.pl-card-meta { display: flex; gap: 1rem; font-size: 0.78rem; color: var(--text-muted); }

.empty-tip { text-align: center; padding: 3rem; color: var(--text-muted); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.75rem; width: 440px; max-width: 95vw; display: flex; flex-direction: column; gap: 0.85rem; }
.modal-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.form-input, .form-textarea { background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem 0.75rem; color: var(--text-primary); font-size: 0.9rem; width: 100%; box-sizing: border-box; }
.form-input:focus, .form-textarea:focus { outline: none; border-color: var(--accent); }
.form-textarea { resize: vertical; font-family: inherit; }
.check-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-secondary); cursor: pointer; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
</style>
