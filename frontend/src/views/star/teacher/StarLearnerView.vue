<script setup>
import '@/assets/star-teacher.css'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import {
  createTask, getLearner, getLearnerReport, getMaterials, regenerateProfile, updateLearner,
} from '@/api/star'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const uid = Number(route.params.uid)

const LAYER = { enlighten: '启蒙层', intro: '入门层' }
const KNOW = { sequence: '顺序', loop: '循环', condition: '条件' }
const PROFILE_STATUS = {
  surveying: { cls: 'plain', text: '✎ 填写中' },
  pending: { cls: 'warn', text: '⏳ 待确认' },
  confirmed: { cls: 'ok', text: '✓ 已确认' },
}
const TASK_STATUS = {
  draft: { cls: 'warn', text: '⏳ 待审核' },
  approved: { cls: 'ok', text: '✓ 已通过' },
  failed: { cls: 'bad', text: '✗ 生成未通过' },
}
const SOURCE = { llm: '大模型生成', rule: '规则生成', seed: '演示数据' }

const tab = ref('profile')
const loading = ref(true)
const error = ref('')
const msg = ref('')
const learner = ref(null)
const tasks = ref([])
const stats = ref(null)
const themes = ref({})
const llmConfigured = ref(true)
const materials = ref(null)
const form = ref(null)
const saving = ref(false)
const regenBusy = ref(false)
const material = ref('')
const creating = ref('')
const report = ref(null)
const reportBusy = ref('')

function fillForm(l) {
  const p = l.profile || {}
  form.value = {
    layer: l.layer || p.layer || '',
    nickname: p.nickname || l.nickname,
    interests: (p.interests || []).join('，'),
    theme_key: p.theme_key || 'train',
    prefer: p.presentation?.prefer || 'both',
    step_size: p.presentation?.step_size || 'normal',
    pronoun_reversal: !!p.communication?.pronoun_reversal,
    echolalia: !!p.communication?.echolalia,
    notes: p.communication?.notes || '',
    vocabulary: (l.vocabulary || []).map((v) => ({ ...v })),
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [{ data }, m] = await Promise.all([getLearner(uid), getMaterials()])
    learner.value = data.learner
    tasks.value = data.tasks
    stats.value = data.stats
    themes.value = data.themes
    llmConfigured.value = data.llm_configured
    materials.value = m.data
    fillForm(data.learner)
  } catch (e) {
    error.value = e.response?.status === 404 ? '学生不存在，或不在你的团队里' : '加载失败，请刷新重试'
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ── 画像 ──
async function saveProfile(confirm = false) {
  saving.value = true
  msg.value = ''
  error.value = ''
  const f = form.value
  try {
    const { data } = await updateLearner(uid, {
      layer: f.layer,
      nickname: f.nickname,
      interests: f.interests.split(/[，,、\s]+/).filter(Boolean),
      theme_key: f.theme_key,
      presentation: { prefer: f.prefer, step_size: f.step_size },
      communication: { pronoun_reversal: f.pronoun_reversal, echolalia: f.echolalia, notes: f.notes },
      vocabulary: f.vocabulary.filter((v) => v.word.trim() && v.meaning.trim()),
      confirm,
    })
    learner.value = data.learner
    fillForm(data.learner)
    msg.value = confirm ? '画像已确认' : '已保存'
  } catch (e) {
    error.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function regenProfile() {
  if (!window.confirm('重新生成会覆盖当前画像（需要重新确认），继续吗？')) return
  regenBusy.value = true
  error.value = ''
  try {
    const { data } = await regenerateProfile(uid)
    learner.value = data.learner
    fillForm(data.learner)
    msg.value = '画像已重新生成，请检查后确认'
  } catch (e) {
    error.value = e.response?.data?.detail || '生成失败'
  } finally {
    regenBusy.value = false
  }
}

// ── 任务 ──
const materialOptions = computed(() => {
  if (!materials.value || !learner.value) return []
  if (learner.value.layer === 'enlighten') {
    return materials.value.levels.map((l) => ({
      key: l.key, text: `${l.key} · ${l.title}（${KNOW[l.knowledge]}，最少 ${l.shortest} 张卡片）`, hasDefault: true,
    }))
  }
  return materials.value.problems.map((p) => ({
    key: p.key, text: `${p.title}（${KNOW[p.knowledge]}${p.demo ? '，演示题' : ''}）`, hasDefault: p.has_default,
  }))
})
const selectedMaterial = computed(() => materialOptions.value.find((m) => m.key === material.value))

async function newTask(mode) {
  if (!material.value) return
  creating.value = mode
  error.value = ''
  try {
    const { data } = await createTask(uid, material.value, mode)
    router.push({ name: 'star-review', params: { id: data.id } })
  } catch (e) {
    error.value = e.response?.data?.detail || '生成失败'
  } finally {
    creating.value = ''
  }
}

// ── 学习情况 ──
const summary = computed(() => stats.value?.summary || {})
const maxSteps = computed(() => Math.max(1, ...(stats.value?.tasks || []).map((t) => t.steps.length)))
const perTaskOption = computed(() => {
  const rows = (stats.value?.tasks || []).filter((t) => t.steps.some((s) => s.done))
  return {
    tooltip: { trigger: 'axis' },
    legend: { type: 'scroll', top: 0, textStyle: { color: '#71717a' } },
    grid: { left: 70, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: Array.from({ length: maxSteps.value }, (_, i) => `第${i + 1}步`) },
    yAxis: {
      type: 'value', min: 0, max: 3, interval: 1,
      axisLabel: { formatter: (v) => ['0 不看', '1 方向', '2 关键', '3 示范'][v] },
    },
    series: rows.map((t) => ({
      name: t.title, type: 'line', connectNulls: false, symbolSize: 8,
      data: t.steps.map((s) => s.hint_level),
    })),
  }
})
const trendOption = computed(() => {
  const s = stats.value?.hint_series || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 70, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', name: '完成顺序', data: s.map((_, i) => i + 1) },
    yAxis: {
      type: 'value', min: 0, max: 3, interval: 1,
      axisLabel: { formatter: (v) => ['0 不看', '1 方向', '2 关键', '3 示范'][v] },
    },
    series: [{ name: '提示等级', type: 'line', step: 'middle', data: s.map((x) => x.hint_level), symbolSize: 7 }],
  }
})

function fmtMs(ms) {
  if (!ms) return '—'
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s} 秒` : `${Math.floor(s / 60)} 分 ${s % 60} 秒`
}

async function makeReport(audience) {
  reportBusy.value = audience
  error.value = ''
  try {
    const { data } = await getLearnerReport(uid, audience)
    report.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || '报告生成失败'
  } finally {
    reportBusy.value = ''
  }
}

function printReport() {
  const r = report.value
  if (!r) return
  const win = window.open('', '_blank', 'width=720,height=900')
  if (!win) return
  const title = `${learner.value.nickname} · 学习报告（${r.audience === 'parent' ? '家长版' : '教师版'}）`
  const doc = win.document
  doc.title = title
  const h = doc.createElement('h2')
  h.textContent = title
  const p = doc.createElement('p')
  p.textContent = r.text
  p.style.cssText = 'font-size:16px;line-height:1.9;white-space:pre-wrap'
  const foot = doc.createElement('p')
  foot.textContent = `生成日期：${new Date().toLocaleDateString('zh-CN')}`
  foot.style.cssText = 'color:#666;font-size:13px'
  doc.body.style.cssText = 'font-family:system-ui,"Microsoft YaHei",sans-serif;padding:32px'
  doc.body.append(h, p, foot)
  win.focus()
  win.print()
}

// ── 对话记录 ──
function metaTags(m) {
  const t = []
  const meta = m.meta || {}
  if (meta.guard) t.push({ cls: 'bad', text: '求助护栏' })
  if (meta.echolalia) t.push({ cls: 'warn', text: '仿说：换问法' })
  for (const [w, s] of meta.replaced || []) t.push({ cls: 'info', text: `词表：${w}→${s}` })
  if (meta.cached) t.push({ cls: 'plain', text: '缓存回答' })
  if (meta.fallback) t.push({ cls: 'plain', text: '兜底回复' })
  return t
}
</script>

<template>
  <div class="st-page">
    <p v-if="loading" class="st-muted">加载中…</p>
    <div v-else-if="!learner" class="st-error">{{ error }}</div>

    <template v-else>
      <header class="st-head">
        <RouterLink class="st-btn" :to="{ name: 'star-teacher' }">← 学习者</RouterLink>
        <div>
          <h1>{{ learner.nickname }} <span class="st-muted">（{{ learner.username }}）</span></h1>
          <p class="st-row">
            <span class="st-badge plain">{{ LAYER[learner.layer] || '未定层级' }}</span>
            <span class="st-badge" :class="PROFILE_STATUS[learner.status]?.cls">{{ PROFILE_STATUS[learner.status]?.text }}</span>
            <span class="st-muted">任务 {{ summary.tasks_done }} / {{ summary.tasks_total }} 完成</span>
          </p>
        </div>
      </header>

      <div v-if="!llmConfigured" class="st-notice">⚠ 未配置大模型：本页的大模型功能会用规则兜底，任务只能用"默认版本"生成。</div>
      <div v-if="error" class="st-error">{{ error }}</div>
      <div v-if="msg" class="st-notice ok-notice">{{ msg }}</div>

      <nav class="st-tabs" role="tablist">
        <button v-for="[k, t] in [['profile', '画像'], ['tasks', `任务（${tasks.length}）`], ['learning', '学习情况与报告'], ['dialogue', '对话记录']]"
                :key="k" type="button" role="tab" class="st-tab" :class="{ 'is-active': tab === k }"
                :aria-selected="tab === k" @click="tab = k">{{ t }}</button>
      </nav>

      <!-- ═════ 画像 ═════ -->
      <div v-if="tab === 'profile'" class="two-col">
        <section class="st-card">
          <h2>问卷结果</h2>
          <dl class="st-kv">
            <template v-for="s in learner.survey" :key="s.key">
              <dt>{{ s.title }}</dt>
              <dd>{{ s.icon }} {{ s.label || '—' }}</dd>
            </template>
          </dl>
          <h3>引导对话</h3>
          <ul class="qa">
            <li v-for="(d, i) in learner.intro_dialogue" :key="i">
              <span class="st-muted">问：{{ d.question }}</span>
              <span>答：<b>{{ d.answer }}</b> <span v-if="d.via === 'text'" class="st-badge plain">自己写的</span></span>
            </li>
            <li v-if="!learner.intro_dialogue.length" class="st-muted">还没有引导对话</li>
          </ul>
        </section>

        <section class="st-card">
          <h2>画像（{{ SOURCE[learner.profile?.source] || '—' }}）</h2>
          <p v-if="learner.profile?.llm_note" class="st-muted">{{ learner.profile.llm_note }}</p>
          <div class="st-form">
            <label>层级</label>
            <div class="st-row">
              <label><input v-model="form.layer" type="radio" value="enlighten"> 启蒙层（卡片闯关）</label>
              <label><input v-model="form.layer" type="radio" value="intro"> 入门层（分步学习）</label>
            </div>
            <span></span>
            <p class="st-muted">建议理由：{{ learner.profile?.layer_reason || '—' }}</p>
            <label for="f-nick">昵称</label>
            <input id="f-nick" v-model="form.nickname" class="st-input" maxlength="10">
            <label for="f-int">兴趣</label>
            <input id="f-int" v-model="form.interests" class="st-input" placeholder="用逗号分隔，最多 3 个">
            <label for="f-theme">关卡主题</label>
            <select id="f-theme" v-model="form.theme_key" class="st-select">
              <option v-for="(t, k) in themes" :key="k" :value="k">{{ t.hero }} {{ t.name }}</option>
            </select>
            <label for="f-pref">呈现偏好</label>
            <div class="st-row">
              <select id="f-pref" v-model="form.prefer" class="st-select narrow">
                <option value="image">喜欢看图</option><option value="text">喜欢看字</option><option value="both">都可以</option>
              </select>
              <select v-model="form.step_size" class="st-select narrow" aria-label="步骤粒度">
                <option value="small">步骤拆得更细</option><option value="normal">步骤粒度正常</option>
              </select>
            </div>
            <label>沟通特点</label>
            <div class="st-row">
              <label><input v-model="form.pronoun_reversal" type="checkbox"> 代词逆转（用"你"指自己）</label>
              <label><input v-model="form.echolalia" type="checkbox"> 仿说</label>
            </div>
            <label for="f-notes">备注</label>
            <input id="f-notes" v-model="form.notes" class="st-input" maxlength="60">
            <label>个人词表</label>
            <div class="vocab">
              <div v-for="(v, i) in form.vocabulary" :key="i" class="st-row">
                <input v-model="v.word" class="st-input w-sm" placeholder="学生的说法" maxlength="10">
                <span>→</span>
                <input v-model="v.meaning" class="st-input w-sm" placeholder="标准说法" maxlength="10">
                <button type="button" class="st-btn st-btn-sm st-btn-danger" @click="form.vocabulary.splice(i, 1)">删除</button>
              </div>
              <button type="button" class="st-btn st-btn-sm" @click="form.vocabulary.push({ word: '', meaning: '' })">+ 添加词条</button>
            </div>
          </div>
          <div class="st-row actions">
            <button type="button" class="st-btn" :disabled="saving" @click="saveProfile(false)">保存</button>
            <button type="button" class="st-btn st-btn-primary" :disabled="saving || !form.layer" @click="saveProfile(true)">
              保存并确认画像
            </button>
            <button type="button" class="st-btn" :disabled="regenBusy || !learner.survey.some((s) => s.value)" @click="regenProfile">
              {{ regenBusy ? '生成中…' : '重新生成画像' }}
            </button>
          </div>
        </section>
      </div>

      <!-- ═════ 任务 ═════ -->
      <template v-if="tab === 'tasks'">
        <section class="st-card">
          <h2>新建改造任务</h2>
          <p v-if="!learner.layer" class="st-muted">请先在"画像"里确定层级。</p>
          <div v-else class="st-row">
            <select v-model="material" class="st-select wide" aria-label="素材">
              <option value="" disabled>选择{{ learner.layer === 'enlighten' ? '关卡模板' : '入门题' }}</option>
              <option v-for="m in materialOptions" :key="m.key" :value="m.key">{{ m.text }}</option>
            </select>
            <button type="button" class="st-btn st-btn-primary" :disabled="!material || !!creating || !llmConfigured"
                    @click="newTask('llm')">
              {{ creating === 'llm' ? '生成并校验中…' : '大模型改造' }}
            </button>
            <button type="button" class="st-btn" :disabled="!material || !!creating || !selectedMaterial?.hasDefault"
                    @click="newTask('template')">
              {{ creating === 'template' ? '生成中…' : '使用默认版本' }}
            </button>
          </div>
          <p v-if="creating === 'llm'" class="st-muted gap">
            大模型生成后由程序校验（格式、句长、答案唯一、代码行来源、关卡可解），不合格的错误会回填给大模型修复，最多 3 轮，约需 10–60 秒。
          </p>
        </section>

        <section class="st-card">
          <div class="st-table-wrap">
            <table class="st-table">
              <thead>
                <tr><th>#</th><th>标题</th><th>素材</th><th>状态</th><th>生成次数</th><th>进度</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="t in tasks" :key="t.id">
                  <td class="st-num">{{ t.sort_order }}</td>
                  <td>{{ t.title }}</td>
                  <td class="st-num">{{ t.template }}</td>
                  <td><span class="st-badge" :class="TASK_STATUS[t.status]?.cls">{{ TASK_STATUS[t.status]?.text }}</span></td>
                  <td class="st-num">{{ t.gen_count }}</td>
                  <td class="st-num">{{ t.done_steps.length }} / {{ t.steps_total }}</td>
                  <td>
                    <RouterLink class="st-btn st-btn-sm" :to="{ name: 'star-review', params: { id: t.id } }">
                      {{ t.status === 'approved' ? '查看' : '审核' }}
                    </RouterLink>
                  </td>
                </tr>
                <tr v-if="!tasks.length"><td colspan="7" class="st-empty">还没有任务</td></tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <!-- ═════ 学习情况与报告 ═════ -->
      <template v-if="tab === 'learning'">
        <div class="st-stats">
          <div class="st-stat"><div class="v">{{ summary.tasks_done }} / {{ summary.tasks_total }}</div><div class="k">完成任务</div></div>
          <div class="st-stat"><div class="v">{{ summary.steps_solved }}</div><div class="k">做对的步骤</div></div>
          <div class="st-stat"><div class="v">{{ summary.attempts }}</div><div class="k">作答次数</div></div>
          <div class="st-stat"><div class="v">{{ summary.avg_hint ?? '—' }}</div><div class="k">平均提示等级</div></div>
          <div class="st-stat">
            <div class="v">{{ summary.avg_hint_early ?? '—' }} → {{ summary.avg_hint_late ?? '—' }}</div>
            <div class="k">前半 → 后半提示等级</div>
          </div>
          <div v-if="learner.layer === 'enlighten'" class="st-stat">
            <div class="v">{{ summary.levels_cleared }}</div><div class="k">通关关卡</div>
          </div>
        </div>

        <section class="st-card">
          <h2>各任务每一步的提示等级</h2>
          <v-chart v-if="stats.tasks.some((t) => t.steps.some((s) => s.done))" class="chart" :option="perTaskOption" autoresize />
          <p v-else class="st-muted">还没有做对的步骤。</p>
        </section>
        <section class="st-card">
          <h2>按完成顺序的提示等级（看提示是否逐步撤除）</h2>
          <v-chart v-if="stats.hint_series.length" class="chart small" :option="trendOption" autoresize />
          <p v-else class="st-muted">还没有数据。</p>
        </section>

        <section class="st-card">
          <h2>任务明细</h2>
          <div class="st-table-wrap">
            <table class="st-table">
              <thead>
                <tr><th>任务</th><th>状态</th><th>作答次数</th><th>各步提示等级</th><th>用时</th><th v-if="learner.layer === 'enlighten'">卡片数（学生 / 最少）</th></tr>
              </thead>
              <tbody>
                <tr v-for="t in stats.tasks" :key="t.task_id">
                  <td>{{ t.title }}</td>
                  <td>
                    <span v-if="t.done" class="st-badge ok">✓ 完成</span>
                    <span v-else-if="t.attempts" class="st-badge info">● 进行中</span>
                    <span v-else class="st-badge plain">未开始</span>
                  </td>
                  <td class="st-num">{{ t.attempts }}</td>
                  <td class="st-num">{{ t.steps.map((s) => s.hint_level ?? '·').join(' / ') }}</td>
                  <td class="st-num">{{ fmtMs(t.steps.reduce((a, s) => a + s.duration_ms, 0)) }}</td>
                  <td v-if="learner.layer === 'enlighten'" class="st-num">
                    {{ t.level?.best_cards ?? '—' }} / {{ t.level?.shortest ?? '—' }}
                  </td>
                </tr>
                <tr v-if="!stats.tasks.length"><td colspan="6" class="st-empty">还没有已通过的任务</td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="st-card">
          <h2>学习报告</h2>
          <div class="st-row">
            <button type="button" class="st-btn" :disabled="!!reportBusy" @click="makeReport('teacher')">
              {{ reportBusy === 'teacher' ? '生成中…' : '生成教师版' }}
            </button>
            <button type="button" class="st-btn" :disabled="!!reportBusy" @click="makeReport('parent')">
              {{ reportBusy === 'parent' ? '生成中…' : '生成家长版' }}
            </button>
            <button v-if="report" type="button" class="st-btn" @click="printReport">打印</button>
          </div>
          <div v-if="report" class="report">
            <p class="st-muted">
              {{ report.audience === 'parent' ? '家长版' : '教师版' }} · {{ report.source === 'llm' ? '大模型生成' : '规则生成' }}
            </p>
            <p class="report-text">{{ report.text }}</p>
          </div>
        </section>
      </template>

      <!-- ═════ 对话记录 ═════ -->
      <section v-if="tab === 'dialogue'" class="st-card">
        <h2>对话助手最近记录</h2>
        <p class="st-muted">标签说明每句话经过了哪些沟通特征处理：仿说检测、个人词表替换、缓存、求助护栏。</p>
        <ul class="chat-log">
          <li v-for="(m, i) in learner.assistant_dialogue" :key="i" :class="m.role">
            <span class="who">{{ m.role === 'bot' ? '学伴' : learner.nickname }}</span>
            <span class="what">{{ m.text }}
              <span v-if="m.options?.length" class="st-muted">［{{ m.options.join(' / ') }}］</span>
            </span>
            <span class="tags">
              <span v-if="m.role === 'user' && m.via === 'option'" class="st-badge plain">点选项</span>
              <span v-for="(t, k) in metaTags(m)" :key="k" class="st-badge" :class="t.cls">{{ t.text }}</span>
            </span>
          </li>
          <li v-if="!learner.assistant_dialogue.length" class="st-muted">还没有对话</li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.two-col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); gap: 20px; align-items: start; }
@media (max-width: 960px) { .two-col { grid-template-columns: 1fr; } }
.qa { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; font-size: 14px; }
.qa li { display: flex; flex-direction: column; gap: 2px; }
.vocab { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.w-sm { width: 130px; }
.narrow { width: auto; }
.wide { width: auto; min-width: 360px; max-width: 100%; }
.actions { margin-top: 18px; }
.gap { margin-top: 10px; }
.ok-notice { border-color: var(--status-ac-dot); background: var(--status-ac-bg); color: var(--status-ac-text); }
.chart { width: 100%; height: 300px; }
.chart.small { height: 220px; }
.report { margin-top: 14px; border-top: 1px solid var(--border); padding-top: 12px; }
.report-text { white-space: pre-wrap; line-height: 1.8; margin: 6px 0 0; color: var(--text-primary); }
.chat-log { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; font-size: 14px; }
.chat-log li { display: grid; grid-template-columns: 56px 1fr auto; gap: 10px; align-items: baseline; padding: 6px 0; border-bottom: 1px solid var(--border); }
.chat-log .who { color: var(--text-secondary); }
.chat-log li.bot .who { color: var(--accent); }
.tags { display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }
</style>
