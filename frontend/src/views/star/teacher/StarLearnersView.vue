<script setup>
import '@/assets/star-teacher.css'
import { onMounted, ref } from 'vue'
import { getLearners } from '@/api/star'

const LAYER = { enlighten: '启蒙层', intro: '入门层' }
const STATUS = {
  surveying: { cls: 'plain', text: '✎ 填写中' },
  pending: { cls: 'warn', text: '⏳ 待确认' },
  confirmed: { cls: 'ok', text: '✓ 已确认' },
}

const rows = ref([])
const llmConfigured = ref(true)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await getLearners()
    rows.value = data.learners
    llmConfigured.value = data.llm_configured
  } catch (e) {
    error.value = e.response?.status === 403 ? '需要教师或管理员权限' : '加载失败，请刷新重试'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="st-page">
    <header class="st-head">
      <div>
        <h1>星语 · 学习者</h1>
        <p class="st-muted">面向孤独症学习者的编程学伴。这里列出你创建的团队里、已经填过问卷的学生。</p>
      </div>
      <div class="st-head-actions">
        <RouterLink class="st-btn st-btn-primary" :to="{ name: 'star-assign' }">批量布置任务</RouterLink>
        <RouterLink class="st-btn" :to="{ name: 'star-home' }">体验学生端</RouterLink>
      </div>
    </header>

    <div v-if="!llmConfigured" class="st-notice">
      ⚠ 未配置大模型（.env 中的 LLM_API_KEY / LLM_API_URL / LLM_MODEL）。画像、对话和报告会用规则兜底，
      任务只能用"默认版本"生成；配置后即可使用大模型改造。
    </div>
    <div v-if="error" class="st-error">{{ error }}</div>

    <section class="st-card">
      <div class="st-table-wrap">
        <table class="st-table">
          <thead>
            <tr>
              <th>昵称</th><th>账号</th><th>层级</th><th>画像</th>
              <th>任务完成</th><th>平均提示等级</th><th>待审核任务</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.user_id">
              <td><b>{{ r.nickname }}</b></td>
              <td class="st-num">{{ r.username }}</td>
              <td>{{ LAYER[r.layer] || '—' }}</td>
              <td><span class="st-badge" :class="STATUS[r.status]?.cls">{{ STATUS[r.status]?.text }}</span></td>
              <td class="st-num">{{ r.tasks_done }} / {{ r.tasks_total }}</td>
              <td class="st-num">{{ r.avg_hint ?? '—' }}</td>
              <td>
                <span v-if="r.pending_tasks" class="st-badge warn">● {{ r.pending_tasks }} 个</span>
                <span v-else class="st-muted">—</span>
              </td>
              <td>
                <RouterLink class="st-btn st-btn-sm" :to="{ name: 'star-learner', params: { uid: r.user_id } }">
                  查看
                </RouterLink>
              </td>
            </tr>
            <tr v-if="!loading && !rows.length">
              <td colspan="8" class="st-empty">
                还没有学习者。学生加入你的团队并在"星语"里填完问卷后会出现在这里；
                本地演示可运行 <code>python manage.py seed_star</code> 生成 40 个虚构学生。
              </td>
            </tr>
            <tr v-if="loading"><td colspan="8" class="st-empty">加载中…</td></tr>
          </tbody>
        </table>
      </div>
    </section>
    <p class="st-muted">平均提示等级：每一步第一次做对时用到的提示等级的平均值（0 = 没看提示，3 = 看了完整示范），越低说明越独立。</p>
  </div>
</template>
