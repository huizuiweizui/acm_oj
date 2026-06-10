<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createDiscussion } from '@/api/discussions'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const route = useRoute()
const router = useRouter()

const title = ref('')
const content = ref('')
const problem_id = ref(route.query.problem_id || '')
const preview = ref(false)
const error = ref('')
const submitting = ref(false)

async function submit() {
  if (!title.value.trim()) { error.value = '标题不能为空'; return }
  if (!content.value.trim()) { error.value = '内容不能为空'; return }
  submitting.value = true
  error.value = ''
  try {
    const { data } = await createDiscussion({
      title: title.value,
      content: content.value,
      problem_id: problem_id.value || undefined,
    })
    router.push(`/discussions/${data.id}`)
  } catch (e) {
    error.value = e.response?.data?.detail || '发布失败'
    submitting.value = false
  }
}
</script>

<template>
  <div class="create-discussion">
    <button class="btn-back" @click="router.push('/discussions')">← 返回讨论列表</button>
    <h2 class="page-title">发起讨论</h2>

    <div class="form-card">
      <div class="form-group">
        <label>标题</label>
        <input v-model="title" type="text" placeholder="请输入标题" />
      </div>

      <div class="form-group">
        <label>关联题目（选填）</label>
        <input v-model="problem_id" type="number" placeholder="题目 ID，留空表示通用讨论" />
      </div>

      <div class="form-group">
        <div class="content-header">
          <label>内容（Markdown）</label>
          <div class="toggle-btns">
            <button :class="['tog', !preview && 'active']" @click="preview=false">编辑</button>
            <button :class="['tog', preview && 'active']" @click="preview=true">预览</button>
          </div>
        </div>
        <textarea
          v-if="!preview"
          v-model="content"
          class="content-textarea"
          placeholder="支持 Markdown 语法..."
          rows="12"
        ></textarea>
        <div v-else class="preview-box">
          <MarkdownRenderer :content="content" />
        </div>
      </div>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <div class="form-actions">
        <button class="btn-submit" :disabled="submitting" @click="submit">
          {{ submitting ? '发布中...' : '发布' }}
        </button>
        <button class="btn-cancel" @click="router.push('/discussions')">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-discussion { padding: 0.5rem 0; max-width: 860px; }
.btn-back { background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:0.875rem; padding:0; margin-bottom:1.2rem; }
.btn-back:hover { color:var(--text-primary); }
.page-title { font-size:1.3rem; font-weight:700; color:var(--text-primary); margin:0 0 1.2rem; }

.form-card { background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:1.8rem; }
.form-group { display:flex; flex-direction:column; gap:0.4rem; margin-bottom:1.2rem; }
.form-group label { font-size:0.85rem; color:var(--text-secondary); }
.form-group input {
  padding:0.6rem 0.9rem; background:var(--bg-input);
  border:1px solid var(--border); border-radius:7px; color:var(--text-primary); font-size:0.95rem;
}
.form-group input:focus { outline:none; border-color:var(--accent); }

.content-header { display:flex; align-items:center; justify-content:space-between; }
.toggle-btns { display:flex; gap:0.2rem; }
.tog {
  padding:0.2rem 0.7rem; background:var(--bg-input);
  border:1px solid var(--border); color:var(--text-muted); font-size:0.8rem; cursor:pointer; border-radius:4px;
}
.tog.active { background:var(--accent); border-color:var(--accent); color:#fff; }

.content-textarea {
  padding:0.7rem 0.9rem; background:var(--bg-input);
  border:1px solid var(--border); border-radius:7px; color:var(--text-primary);
  font-size:0.9rem; resize:vertical; font-family:inherit; width:100%;
}
.content-textarea:focus { outline:none; border-color:var(--accent); }
.preview-box {
  min-height:200px; padding:1rem; background:var(--bg-input);
  border:1px solid var(--border); border-radius:7px;
}

.error-msg { color: var(--status-wa-text); font-size:0.85rem; margin-bottom:0.8rem; }
.form-actions { display:flex; gap:0.75rem; }
.btn-submit {
  padding:0.55rem 1.4rem; background:var(--accent); color:#fff;
  border:none; border-radius:6px; cursor:pointer; font-size:0.9rem;
}
.btn-submit:hover:not(:disabled) { background:var(--accent-hover); }
.btn-submit:disabled { opacity:0.6; cursor:not-allowed; }
.btn-cancel {
  padding:0.55rem 1.2rem; background:transparent;
  border:1px solid var(--border); color:var(--text-muted); border-radius:6px; cursor:pointer; font-size:0.9rem;
}
.btn-cancel:hover { border-color:var(--accent); color:var(--text-primary); }
</style>
