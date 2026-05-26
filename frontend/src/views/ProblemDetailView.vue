<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProblem } from '@/api/problems'
import { submitCode } from '@/api/problems'
import { useUserStore } from '@/stores/user'
import { useSubmissionStore } from '@/stores/submission'
import DifficultyBadge from '@/components/DifficultyBadge.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import CodeEditor from '@/components/CodeEditor.vue'
import JudgeResult from '@/components/JudgeResult.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const submissionStore = useSubmissionStore()

const problem = ref(null)
const loading = ref(true)
const language = ref('C++')
const code = ref('')
const submitting = ref(false)
const submitError = ref('')
const contestId = route.query.contest_id || null

const LANGUAGES = ['C', 'C++', 'Java', 'Python']

const DEFAULT_CODE = {
  'C':      '#include <stdio.h>\n\nint main() {\n    \n    return 0;\n}\n',
  'C++':    '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    \n    return 0;\n}\n',
  'Java':   'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        \n    }\n}\n',
  'Python': '# Python solution\nimport sys\ninput = sys.stdin.readline\n\n',
}

function switchLanguage(lang) {
  if (language.value === lang) return
  // 只有代码未修改或是默认代码时才自动切换模板
  const isDefault = Object.values(DEFAULT_CODE).includes(code.value) || !code.value
  language.value = lang
  if (isDefault) code.value = DEFAULT_CODE[lang]
}

async function handleSubmit() {
  if (!userStore.isLoggedIn) {
    router.push(`/login?next=/problems/${route.params.id}`)
    return
  }
  if (!code.value.trim()) {
    submitError.value = '代码不能为空'
    return
  }
  submitting.value = true
  submitError.value = ''
  try {
    const { data } = await submitCode(route.params.id, language.value, code.value, contestId)
    submissionStore.startPolling(data.submission_id)
  } catch (e) {
    submitError.value = e.response?.data?.detail || '提交失败，请重试'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await getProblem(route.params.id)
    problem.value = data
    code.value = DEFAULT_CODE['C++']
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  submissionStore.stopPolling()
})
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>

  <div v-else-if="problem" class="detail-layout">
    <!-- 左栏：题面 -->
    <div class="left-panel">
      <!-- 标题区 -->
      <div class="problem-header">
        <h1 class="problem-title">#{{ problem.id }} {{ problem.title }}</h1>
        <div class="problem-meta">
          <DifficultyBadge :difficulty="problem.difficulty" />
          <span class="meta-item">⏱ {{ problem.time_limit }} ms</span>
          <span class="meta-item">💾 {{ problem.memory_limit }} MB</span>
          <span class="meta-item" v-if="problem.source">来源：{{ problem.source }}</span>
        </div>
        <div class="tags" v-if="problem.tags?.length">
          <span v-for="t in problem.tags" :key="t.id" class="tag">{{ t.name }}</span>
        </div>
      </div>

      <!-- 题目描述 -->
      <div class="section">
        <div class="section-label">题目描述</div>
        <MarkdownRenderer :content="problem.description" />
      </div>

      <div class="section">
        <div class="section-label">输入格式</div>
        <MarkdownRenderer :content="problem.input_desc" />
      </div>

      <div class="section">
        <div class="section-label">输出格式</div>
        <MarkdownRenderer :content="problem.output_desc" />
      </div>

      <!-- 样例 -->
      <div class="samples">
        <div class="sample-group">
          <div class="sample-label">样例输入</div>
          <pre class="sample-block">{{ problem.sample_input }}</pre>
        </div>
        <div class="sample-group">
          <div class="sample-label">样例输出</div>
          <pre class="sample-block">{{ problem.sample_output }}</pre>
        </div>
      </div>

      <div class="section" v-if="problem.hint">
        <div class="section-label">提示</div>
        <MarkdownRenderer :content="problem.hint" />
      </div>
    </div>

    <!-- 右栏：编辑器 + 提交 -->
    <div class="right-panel">
      <!-- 语言选择 -->
      <div class="lang-bar">
        <button
          v-for="lang in LANGUAGES" :key="lang"
          class="lang-btn" :class="{ active: language === lang }"
          @click="switchLanguage(lang)"
        >{{ lang }}</button>
      </div>

      <!-- Monaco 编辑器 -->
      <div class="editor-wrap">
        <CodeEditor v-model="code" :language="language" />
      </div>

      <!-- 提交区 -->
      <div class="submit-area">
        <div v-if="submitError" class="submit-error">{{ submitError }}</div>
        <div class="submit-row">
          <span class="shortcut-tip">Ctrl+Enter 提交</span>
          <button
            class="btn-submit"
            :disabled="submitting || submissionStore.polling"
            @click="handleSubmit"
          >
            {{ submitting ? '提交中...' : submissionStore.polling ? '评测中...' : '提交代码' }}
          </button>
        </div>
      </div>

      <!-- 评测结果 -->
      <JudgeResult
        v-if="submissionStore.current"
        :submission="submissionStore.current"
        :polling="submissionStore.polling"
      />
    </div>
  </div>
</template>

<style scoped>
.loading { text-align: center; padding: 4rem; color: #888; }

.detail-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.2rem;
  align-items: start;
  min-height: calc(100vh - 100px);
}

/* 左栏 */
.left-panel {
  background: #16162a;
  border: 1px solid #2d2d4e;
  border-radius: 10px;
  padding: 1.6rem;
  overflow-y: auto;
  max-height: calc(100vh - 90px);
}

.problem-header { margin-bottom: 1.4rem; }
.problem-title { font-size: 1.25rem; font-weight: 700; color: #e0e0f0; margin: 0 0 0.75rem; }
.problem-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.6rem; }
.meta-item { font-size: 0.82rem; color: #888; }
.tags { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.4rem; }
.tag {
  padding: 0.15rem 0.55rem; border-radius: 4px;
  background: #1e1e38; border: 1px solid #3d3d5c;
  font-size: 0.75rem; color: #a0a0c0;
}

.section { margin-bottom: 1.2rem; }
.section-label {
  font-size: 0.82rem; font-weight: 700; color: #7c6af7;
  text-transform: uppercase; letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.samples {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;
  margin-bottom: 1.2rem;
}
.sample-group { display: flex; flex-direction: column; gap: 0.4rem; }
.sample-label { font-size: 0.8rem; font-weight: 600; color: #888; }
.sample-block {
  background: #12121e; border: 1px solid #2d2d4e;
  border-radius: 6px; padding: 0.75rem;
  font-size: 0.85rem; color: #c8c8d8;
  white-space: pre-wrap; word-break: break-all;
  font-family: 'Fira Code', 'Consolas', monospace;
  min-height: 60px; margin: 0;
}

/* 右栏 */
.right-panel {
  display: flex; flex-direction: column; gap: 0.6rem;
  position: sticky; top: 72px;
}

.lang-bar {
  display: flex; gap: 0.3rem;
  background: #16162a; border: 1px solid #2d2d4e;
  border-radius: 8px; padding: 0.4rem;
}
.lang-btn {
  padding: 0.3rem 0.9rem; border: none; border-radius: 5px;
  background: transparent; color: #888; cursor: pointer; font-size: 0.85rem;
}
.lang-btn:hover { color: #e0e0f0; }
.lang-btn.active { background: #7c6af7; color: #fff; font-weight: 600; }

.editor-wrap {
  height: 460px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #2d2d4e;
}

.submit-area {
  background: #16162a; border: 1px solid #2d2d4e;
  border-radius: 8px; padding: 0.75rem 1rem;
}
.submit-error { color: #ff8080; font-size: 0.85rem; margin-bottom: 0.5rem; }
.submit-row { display: flex; align-items: center; justify-content: space-between; }
.shortcut-tip { font-size: 0.78rem; color: #555; }
.btn-submit {
  padding: 0.5rem 1.8rem; background: #7c6af7; color: #fff;
  border: none; border-radius: 6px; font-size: 0.95rem; font-weight: 600; cursor: pointer;
}
.btn-submit:hover:not(:disabled) { background: #6c5ae7; }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

@media (max-width: 900px) {
  .detail-layout { grid-template-columns: 1fr; }
  .left-panel { max-height: none; }
  .right-panel { position: static; }
}
</style>
