<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDiscussion, createReply, deleteDiscussion } from '@/api/discussions'
import { useUserStore } from '@/stores/user'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const discussion = ref(null)
const replies = ref([])
const loading = ref(true)
const replyContent = ref('')
const submitting = ref(false)
const replyError = ref('')

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

async function fetchDiscussion() {
  loading.value = true
  try {
    const { data } = await getDiscussion(route.params.id)
    discussion.value = data.discussion
    replies.value = data.replies
  } finally {
    loading.value = false
  }
}

async function deletePost() {
  if (!confirm('确定要删除这篇帖子吗？')) return
  try {
    await deleteDiscussion(route.params.id)
    router.push('/discussions')
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

async function submitReply() {
  if (!replyContent.value.trim()) {
    replyError.value = '回复内容不能为空'
    return
  }
  submitting.value = true
  replyError.value = ''
  try {
    const { data } = await createReply(route.params.id, replyContent.value)
    replies.value.push(data)
    replyContent.value = ''
  } catch (e) {
    replyError.value = e.response?.data?.detail || '回复失败'
  } finally {
    submitting.value = false
  }
}

onMounted(fetchDiscussion)
</script>

<template>
  <div class="discussion-detail" v-if="!loading && discussion">
    <!-- 返回 -->
    <button class="btn-back" @click="router.push('/discussions')">← 返回讨论列表</button>

    <!-- 帖子主体 -->
    <div class="post-card">
      <div class="post-header">
        <div class="post-meta">
          <div class="avatar" :style="{ background: 'var(--accent)' }">
            {{ discussion.username?.[0]?.toUpperCase() }}
          </div>
          <div class="meta-info">
            <span class="author">{{ discussion.username }}</span>
            <span class="time">{{ timeAgo(discussion.created_at) }}</span>
          </div>
        </div>
        <div class="post-actions">
          <RouterLink
            v-if="discussion.problem_id"
            :to="`/problems/${discussion.problem_id}`"
            class="problem-tag"
          >题目 #{{ discussion.problem_id }}：{{ discussion.problem_title }}</RouterLink>
          <button
            v-if="userStore.user?.username === discussion.username"
            class="btn-delete"
            @click="deletePost"
          >删除</button>
        </div>
      </div>

      <h1 class="post-title">{{ discussion.title }}</h1>
      <MarkdownRenderer :content="discussion.content" />

      <div class="post-footer">
        <span class="view-count">👁 {{ discussion.view_count }} 次浏览</span>
      </div>
    </div>

    <!-- 回复列表 -->
    <div class="replies-section">
      <div class="replies-title">回复 ({{ replies.length }})</div>

      <div v-if="replies.length === 0" class="no-replies">暂无回复，来说第一句话</div>

      <div class="reply-card" v-for="(r, i) in replies" :key="r.id">
        <div class="reply-header">
          <div class="reply-meta">
            <div class="avatar small" :style="{ background: 'var(--accent)' }">
              {{ r.username?.[0]?.toUpperCase() }}
            </div>
            <span class="author">{{ r.username }}</span>
            <span class="floor">#{{ i + 1 }}</span>
            <span class="time">{{ timeAgo(r.created_at) }}</span>
          </div>
        </div>
        <MarkdownRenderer :content="r.content" />
      </div>
    </div>

    <!-- 回复框 -->
    <div class="reply-form" v-if="userStore.isLoggedIn">
      <div class="form-title">发表回复</div>
      <textarea
        v-model="replyContent"
        class="reply-textarea"
        placeholder="支持 Markdown 语法..."
        rows="5"
      ></textarea>
      <div v-if="replyError" class="error-msg">{{ replyError }}</div>
      <div class="form-actions">
        <button class="btn-submit" :disabled="submitting" @click="submitReply">
          {{ submitting ? '发布中...' : '发布回复' }}
        </button>
      </div>
    </div>
    <div class="login-tip" v-else>
      <RouterLink to="/login">登录</RouterLink> 后才能发表回复
    </div>
  </div>

  <div v-else-if="loading" class="loading">加载中...</div>
</template>

<style scoped>
.discussion-detail { padding: 0.5rem 0; max-width: 860px; }
.loading { text-align: center; padding: 4rem; color: var(--text-muted); }

.btn-back {
  background: none; border: none; color: var(--text-muted); cursor: pointer;
  font-size: 0.875rem; padding: 0; margin-bottom: 1.2rem;
}
.btn-back:hover { color: var(--text-primary); }

.post-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.5rem 1.8rem; margin-bottom: 1.5rem;
}
.post-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;
}
.post-meta { display: flex; align-items: center; gap: 0.75rem; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.9rem; font-weight: 700; color: #fff; flex-shrink: 0;
}
.avatar.small { width: 28px; height: 28px; font-size: 0.78rem; }
.meta-info { display: flex; flex-direction: column; }
.author { color: var(--accent); font-weight: 600; font-size: 0.9rem; }
.time { color: var(--text-muted); font-size: 0.8rem; }
.problem-tag {
  font-size: 0.82rem; color: var(--accent);
  background: var(--bg-input); border: 1px solid var(--border);
  padding: 0.2rem 0.6rem; border-radius: 4px;
}
.problem-tag:hover { border-color: var(--accent); }
.post-actions { display: flex; align-items: center; gap: 0.6rem; }
.btn-delete {
  padding: 0.2rem 0.7rem; font-size: 0.82rem; cursor: pointer;
  background: transparent; border: 1px solid #e05555; color: #e05555;
  border-radius: 4px; transition: background 0.15s, color 0.15s;
}
.btn-delete:hover { background: #e05555; color: #fff; }

.post-title { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin: 0 0 1rem; }
.post-footer { margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid var(--border); }
.view-count { font-size: 0.82rem; color: var(--text-muted); }

/* 回复 */
.replies-section { margin-bottom: 1.5rem; }
.replies-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 1rem; }
.no-replies { color: var(--text-muted); font-size: 0.9rem; padding: 1rem 0; }

.reply-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem 1.4rem; margin-bottom: 0.75rem;
}
.reply-header { margin-bottom: 0.75rem; }
.reply-meta { display: flex; align-items: center; gap: 0.6rem; }
.floor { color: var(--text-muted); font-size: 0.8rem; }

/* 回复框 */
.reply-form {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 1.4rem 1.8rem;
}
.form-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.9rem; }
.reply-textarea {
  width: 100%; padding: 0.7rem 0.9rem;
  background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 7px; color: var(--text-primary); font-size: 0.9rem;
  resize: vertical; font-family: inherit;
}
.reply-textarea:focus { outline: none; border-color: var(--accent); }
.error-msg { color: var(--status-wa-text); font-size: 0.85rem; margin-top: 0.4rem; }
.form-actions { margin-top: 0.75rem; }
.btn-submit {
  padding: 0.5rem 1.4rem; background: var(--accent); color: #fff;
  border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;
}
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.login-tip {
  text-align: center; padding: 1.5rem;
  color: var(--text-muted); font-size: 0.9rem;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
}
.login-tip a { color: var(--accent); }
</style>
