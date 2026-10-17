<script setup>
// 教师审核页：预览（学生将看到的样子）、修改文字、看校验结果与生成日志，然后通过并锁定或重新生成。
import '@/assets/star-teacher.css'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LevelBoard from '@/components/star/LevelBoard.vue'
import { ACCENTS, BG_NAMES, BUTTON_NAMES, themeVars } from '@/components/star/starUi'
import {
  approveTask, deleteTask, getTaskForReview, regenerateTask, updateTaskContent,
} from '@/api/star'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

const STATUS = {
  draft: { cls: 'warn', text: '⏳ 待审核' },
  approved: { cls: 'ok', text: '✓ 已通过（已锁定）' },
  failed: { cls: 'bad', text: '✗ 未通过校验' },
}
const MODE = { llm: '大模型', template: '默认版本', edit: '教师修改' }
const KNOW = { sequence: '顺序', loop: '循环', condition: '条件' }
const TYPE = { choice: '选择题', fill: '填空题', order: '排序题', code: '写代码' }
const CARD = { forward: '⬆ 前进', left: '↺ 左转', right: '↻ 右转', repeat: '🔁 重复' }

const task = ref(null)
const draft = ref(null)
const jsonMode = ref(false)
const jsonText = ref('')
const loading = ref(true)
const busy = ref('')
const error = ref('')
const msg = ref('')

function setTask(data) {
  task.value = data
  draft.value = JSON.parse(JSON.stringify(data.content || {}))
  jsonText.value = JSON.stringify(data.content || {}, null, 2)
}

async function load() {
  loading.value = true
  try {
    setTask((await getTaskForReview(id)).data)
  } catch (e) {
    error.value = e.response?.status === 404 ? '任务不存在' : '加载失败'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const isLevel = computed(() => task.value?.layer === 'enlighten')

// 预览按这个学生的界面设置来画：背景、主色、按钮形状、选中标记都和学生端一样
const studentUi = computed(() => task.value?.student?.ui || {})
const skin = computed(() => themeVars(studentUi.value))
const uiSummary = computed(() => {
  const u = studentUi.value
  return [`${BG_NAMES[u.bg] || '米色'}背景`, `${ACCENTS[u.accent]?.name || '蓝色'}主色`,
    BUTTON_NAMES[u.button] || '小圆角按钮', `选中标记 ${u.mark || '✓'}`].join(' · ')
})
const content = computed(() => task.value?.content || {})
const nick = computed(() => task.value?.student?.nickname || '')
const named = (s) => String(s ?? '').replaceAll('{name}', nick.value)

// 与后端 validators.sentences / char_len 同一口径：不算空白和标点，行内代码记一个词，{name} 按两个字
const SPLIT = /[。！？!?；;\n]+/
const NOT_COUNTED = /[\s，,、：:“”"‘’'（）()《》<>【】[\]…—\-·。！？!?；;]/g
function longSentences(text) {
  const t = String(text || '').replace(/`[^`]*`/g, '代码').replaceAll('{name}', '名字')
  return t.split(SPLIT).map((s) => s.trim()).filter((s) => s && s.replace(NOT_COUNTED, '').length > 20)
}
const tooLong = (text) => longSentences(text).length > 0

function blankFilled(st) {
  const code = String(st.code || '').replace(/_{3,}/g, '____')
  const [a, ...rest] = code.split('____')
  return { before: a, answer: st.answer, after: rest.join('____') }
}

async function save() {
  let payload = draft.value
  if (jsonMode.value) {
    try {
      payload = JSON.parse(jsonText.value)
    } catch {
      error.value = 'JSON 格式有误，请检查括号和引号'
      return
    }
  }
  busy.value = 'save'
  error.value = ''
  msg.value = ''
  try {
    setTask((await updateTaskContent(id, payload)).data)
    msg.value = task.value.check.rules_ok ? '已保存，校验全部通过' : '已保存，但还有校验没通过'
  } catch (e) {
    error.value = e.response?.data?.detail || '保存失败'
  } finally {
    busy.value = ''
  }
}

async function approve() {
  busy.value = 'approve'
  error.value = ''
  try {
    setTask((await approveTask(id)).data)
    msg.value = '已通过并锁定，学生现在可以看到这个任务'
  } catch (e) {
    error.value = [e.response?.data?.detail, ...(e.response?.data?.errors || [])].filter(Boolean).join('；') || '操作失败'
  } finally {
    busy.value = ''
  }
}

async function regenerate(mode) {
  const warn = task.value.status === 'approved' ? '重新生成后需要重新审核，审核前学生看不到这个任务。' : ''
  if (!window.confirm(`${warn}确定重新生成吗？`)) return
  busy.value = mode
  error.value = ''
  msg.value = ''
  try {
    setTask((await regenerateTask(id, mode)).data)
    msg.value = task.value.status === 'draft' ? '已重新生成，校验通过，请审核' : '已重新生成，但未通过校验'
  } catch (e) {
    error.value = e.response?.data?.detail || '生成失败'
  } finally {
    busy.value = ''
  }
}

async function remove() {
  if (!window.confirm('删除这个任务？作答记录也会一起删除。')) return
  await deleteTask(id)
  router.push({ name: 'star-learner', params: { uid: task.value.student.user_id } })
}

// 最近一轮生成里，每次都是接口调用失败（大模型一次输出都没拿到）：要查配置，不是内容问题
const apiFailure = computed(() => {
  const log = task.value?.validation_log || []
  const last = log.length ? log[log.length - 1].run : null
  const entries = log.filter((e) => e.run === last && e.mode === 'llm')
  const failed = entries.length && entries.every((e) => (e.errors || []).some((x) => x.startsWith('接口调用失败')))
  return failed ? entries[entries.length - 1].errors[0] : ''
})
// 表单编辑只在结构完整时可用；空内容或结构不对时只能直接编辑 JSON 或重新生成
const formOk = computed(() => !!task.value?.check?.format_ok && !!draft.value
  && (isLevel.value ? !!draft.value.theme && Array.isArray(draft.value.story) : Array.isArray(draft.value.steps)))

// 默认只显示最新一轮；更早的轮次（比如以前没连上大模型的记录）折叠起来，点开才看
const showOlder = ref(false)
const latestRun = computed(() => {
  const log = task.value?.validation_log || []
  return log.length ? log[log.length - 1].run : null
})
const allRuns = computed(() => [...(task.value?.validation_log || [])].reverse())
const olderCount = computed(() => allRuns.value.filter((r) => r.run !== latestRun.value).length)
const runs = computed(() => (showOlder.value ? allRuns.value : allRuns.value.filter((r) => r.run === latestRun.value)))
</script>

<template>
  <div class="st-page">
    <p v-if="loading" class="st-muted">加载中…</p>
    <div v-else-if="!task" class="st-error">{{ error }}</div>

    <template v-else>
      <header class="st-head">
        <RouterLink class="st-btn" :to="{ name: 'star-learner', params: { uid: task.student.user_id } }">← {{ nick }}</RouterLink>
        <div>
          <h1>{{ named(content.title) || task.template }}</h1>
          <p class="st-row">
            <span class="st-badge" :class="STATUS[task.status]?.cls">{{ STATUS[task.status]?.text }}</span>
            <span class="st-badge plain">{{ isLevel ? '启蒙层 · 卡片闯关' : '入门层 · 分步学习' }}</span>
            <span class="st-muted">素材 {{ task.template }} · 大模型生成 {{ task.gen_count }} 次</span>
          </p>
        </div>
        <div class="st-head-actions">
          <button v-if="task.status !== 'approved'" type="button" class="st-btn st-btn-primary"
                  :disabled="!task.check.rules_ok || !!busy" @click="approve">
            {{ busy === 'approve' ? '处理中…' : '通过并锁定' }}
          </button>
          <button type="button" class="st-btn" :disabled="task.has_attempts || !!busy" @click="regenerate('llm')">
            {{ busy === 'llm' ? '生成并校验中…' : '大模型重新生成' }}
          </button>
          <button type="button" class="st-btn" :disabled="task.has_attempts || !!busy" @click="regenerate('template')">
            {{ busy === 'template' ? '生成中…' : '换成默认版本' }}
          </button>
          <button type="button" class="st-btn st-btn-danger" :disabled="!!busy" @click="remove">删除</button>
        </div>
      </header>
      <p v-if="task.has_attempts" class="st-muted">这个任务已有作答记录，为保留学习数据不能重新生成。</p>

      <div v-if="error" class="st-error">{{ error }}</div>
      <div v-if="msg" class="st-notice ok-notice">{{ msg }}</div>

      <section class="st-card" :class="task.check.rules_ok ? 'check-ok' : 'check-bad'">
        <h2>{{ task.check.rules_ok ? '✓ 全部校验通过' : '✗ 校验未通过' }}</h2>
        <p class="st-muted">
          {{ isLevel
            ? '已检查：JSON 结构、句长（每句 ≤ 20 字）、地图合法、BFS 可解、卡槽数与最少卡片数匹配、循环关卡必须用到重复卡。'
            : '已检查：JSON 结构、句长（每句 ≤ 20 字）、步骤数 3–6、选择题答案唯一、填空答案来自参考解、排序代码行逐字来自参考解（参考解已由评测机实跑通过）。' }}
        </p>
        <p v-if="apiFailure" class="st-notice">
          这次没生成出内容：{{ apiFailure }}。这是大模型接口连不上（地址、key 或模型名不对，或后端还在用旧配置），
          不是内容不合格。检查 .env 里的 LLM_API_URL / LLM_API_KEY / LLM_MODEL，改过之后要完全重启后端，再点"大模型重新生成"。
        </p>
        <ul v-if="task.check.errors.length" class="st-err-list">
          <li v-for="(e, i) in task.check.errors" :key="i">{{ e }}</li>
        </ul>
      </section>

      <div class="two-col">
        <!-- ═════ 预览 ═════ -->
        <section class="st-card">
          <h2>预览（学生看到的内容）</h2>
          <p class="st-muted">{{ nick }}的界面：{{ uiSummary }}</p>
          <p v-if="task.student.avoid_pronouns" class="st-muted">
            代词：{{ nick }}"你""我"容易弄反，任务文字里不用"你""我"，称呼一律用昵称（已校验）。
          </p>
          <div class="skin" :style="skin" aria-label="按学生界面设置画的示意">
            <span class="skin-flow"><span class="is-done">{{ studentUi.mark || '✓' }}</span><span class="is-cur">2</span><span>3</span></span>
            <span class="skin-opt">B　6 <b>{{ studentUi.mark || '✓' }}</b></span>
            <span class="skin-btn">检查</span>
          </div>
          <template v-if="isLevel && task.check.format_ok">
            <p v-for="(s, i) in content.story" :key="i" class="story">{{ named(s) }}</p>
            <div class="skin skin-board" :style="skin">
              <LevelBoard :level="content" :max-width="440" />
            </div>
            <dl class="st-kv gap">
              <dt>知识点</dt><dd>{{ KNOW[content.knowledge] }}</dd>
              <dt>可用卡片</dt><dd>{{ content.cards.map((c) => CARD[c]).join('　') }}</dd>
              <dt>卡槽数</dt><dd class="st-num">{{ content.slots }}</dd>
              <dt>最少卡片</dt><dd class="st-num">{{ task.solution ? task.solution.length : '无解' }}</dd>
              <dt>示范解</dt>
              <dd>
                <span v-for="(c, i) in task.solution || []" :key="i" class="chip">
                  {{ CARD[c.type] }}<template v-if="c.type === 'repeat'"> {{ c.times }} 次</template>
                </span>
              </dd>
            </dl>
          </template>

          <template v-else-if="!isLevel && task.check.format_ok">
            <p v-for="(s, i) in content.intro" :key="i" class="story">{{ named(s) }}</p>
            <ol class="step-list">
              <li v-for="(st, i) in content.steps" :key="i" class="step">
                <p class="step-head">
                  <b>第 {{ i + 1 }} 步 · {{ TYPE[st.type] }}</b>
                  <span class="st-badge plain">{{ KNOW[st.knowledge] || st.knowledge }}</span>
                </p>
                <p class="prompt">{{ named(st.prompt) }}</p>
                <ul v-if="st.type === 'choice'" class="opts">
                  <li v-for="(o, k) in st.options" :key="k" :class="{ right: k === st.answer }">
                    {{ 'ABCD'[k] }}. {{ o }} <b v-if="k === st.answer">✓ 正确答案</b>
                  </li>
                </ul>
                <pre v-else-if="st.type === 'fill'" class="st-code">{{ blankFilled(st).before }}<mark>{{ blankFilled(st).answer }}</mark>{{ blankFilled(st).after }}</pre>
                <template v-else-if="st.type === 'code'">
                  <pre class="st-code">{{ st.starter || '（空白，学生从头写）' }}</pre>
                  <p class="st-muted">学生在起始代码上写出完整程序，由评测机运行测试数据判定；出错时告诉学生第几行、哪一类错。</p>
                </template>
                <template v-else>
                  <pre class="st-code">{{ task.reference_lines.join('\n') }}</pre>
                  <p class="st-muted">学生看到的是固定打乱后的顺序；排好后拼成完整程序，由评测机运行测试数据判定。</p>
                </template>
                <ol class="hints">
                  <li v-for="(h, k) in st.hints" :key="k">提示 {{ k + 1 }}：{{ named(h) }}</li>
                </ol>
              </li>
            </ol>
          </template>
          <p v-else class="st-muted">内容结构不完整，无法预览，请看右侧 JSON。</p>

          <details v-if="content.analysis" class="analysis">
            <summary>大模型的拆解思路（学生看不到）</summary>
            <p>{{ content.analysis }}</p>
          </details>
        </section>

        <!-- ═════ 修改文字 ═════ -->
        <section class="st-card">
          <div class="st-row edit-head">
            <h2>修改文字</h2>
            <label class="st-muted json-toggle"><input v-model="jsonMode" type="checkbox"> 直接编辑 JSON</label>
          </div>
          <p v-if="task.locked" class="st-muted">已通过的任务内容已锁定。要修改请先"重新生成"，审核后再给学生。</p>

          <fieldset :disabled="task.locked || !!busy" class="edit">
            <template v-if="jsonMode">
              <textarea v-model="jsonText" class="st-textarea" rows="26" spellcheck="false" aria-label="任务 JSON"></textarea>
            </template>

            <p v-else-if="!formOk" class="st-muted">
              内容结构不完整{{ apiFailure ? '（大模型没有返回内容）' : '' }}，没法用表单修改。
              可以点上面的"大模型重新生成"或"换成默认版本"，也可以勾选"直接编辑 JSON"。
            </p>

            <template v-else-if="isLevel">
              <label class="fld">标题<input v-model="draft.title" class="st-input" maxlength="20"></label>
              <label v-for="(s, i) in draft.story" :key="`s${i}`" class="fld">
                故事第 {{ i + 1 }} 句 <span v-if="tooLong(draft.story[i])" class="warn-text">超过 20 字</span>
                <input v-model="draft.story[i]" class="st-input">
              </label>
              <div class="st-row">
                <label class="fld">主题名<input v-model="draft.theme.name" class="st-input w-sm"></label>
                <label class="fld">主角<input v-model="draft.theme.hero" class="st-input w-xs"></label>
                <label class="fld">终点<input v-model="draft.theme.goal" class="st-input w-xs"></label>
                <label class="fld">障碍<input v-model="draft.theme.wall" class="st-input w-xs"></label>
                <label class="fld">卡槽数<input v-model.number="draft.slots" type="number" min="1" max="10" class="st-input w-xs"></label>
              </div>
              <p class="st-muted">地图（起点、终点、障碍）请用"直接编辑 JSON"修改，保存时会重新做可解性检查。</p>
            </template>

            <template v-else>
              <label class="fld">标题<input v-model="draft.title" class="st-input" maxlength="20"></label>
              <label v-for="(s, i) in draft.intro" :key="`i${i}`" class="fld">
                开场第 {{ i + 1 }} 句 <span v-if="tooLong(draft.intro[i])" class="warn-text">超过 20 字</span>
                <input v-model="draft.intro[i]" class="st-input">
              </label>
              <div v-for="(st, i) in draft.steps" :key="`st${i}`" class="edit-step">
                <b>第 {{ i + 1 }} 步 · {{ TYPE[st.type] }}</b>
                <label class="fld">
                  题干 <span v-if="tooLong(st.prompt)" class="warn-text">超过 20 字</span>
                  <input v-model="st.prompt" class="st-input">
                </label>
                <template v-if="st.type === 'choice'">
                  <div v-for="(o, k) in st.options" :key="k" class="st-row">
                    <input v-model="st.answer" type="radio" :value="k" :aria-label="`选项 ${'ABCD'[k]} 为正确答案`">
                    <input v-model="st.options[k]" class="st-input opt" :aria-label="`选项 ${'ABCD'[k]}`">
                  </div>
                </template>
                <div v-else-if="st.type === 'fill'" class="st-row">
                  <label class="fld grow">代码（____ 为空）<input v-model="st.code" class="st-input mono"></label>
                  <label class="fld">答案<input v-model="st.answer" class="st-input w-sm mono"></label>
                </div>
                <label v-else-if="st.type === 'code'" class="fld">
                  起始代码（只能是 # 注释和参考解里的原行）
                  <textarea v-model="st.starter" class="st-textarea" rows="6" spellcheck="false"></textarea>
                </label>
                <p v-else class="st-muted">排序题的代码行固定来自参考解，不能修改。</p>
                <label v-for="(h, k) in st.hints" :key="`h${k}`" class="fld">
                  提示 {{ k + 1 }} <span v-if="tooLong(st.hints[k])" class="warn-text">超过 20 字</span>
                  <input v-model="st.hints[k]" class="st-input">
                </label>
              </div>
            </template>

            <div class="st-row save-row">
              <button type="button" class="st-btn st-btn-primary" @click="save">
                {{ busy === 'save' ? '保存中…' : '保存并重新校验' }}
              </button>
              <span class="st-muted">称呼学生处写 {name}，显示时换成昵称。</span>
            </div>
          </fieldset>
        </section>
      </div>

      <section class="st-card">
        <h2>生成与校验日志</h2>
        <p class="st-muted">
          下面是最新一轮（第 {{ latestRun }} 轮），任务现在的状态以它为准。
          <button v-if="olderCount" type="button" class="st-btn st-btn-sm" @click="showOlder = !showOlder">
            {{ showOlder ? '收起更早的记录' : `显示更早的 ${olderCount} 条记录` }}
          </button>
        </p>
        <div class="st-table-wrap">
          <table class="st-table">
            <thead>
              <tr><th>轮次</th><th>方式</th><th>第几次</th><th>结果</th><th>问题</th><th>耗时</th><th>token</th></tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in runs" :key="i">
                <td class="st-num">{{ r.run }}</td>
                <td>{{ MODE[r.mode] || r.mode }}</td>
                <td class="st-num">{{ r.attempt }}</td>
                <td>
                  <span v-if="r.ok" class="st-badge ok">✓ 通过</span>
                  <span v-else-if="(r.errors || []).some((e) => e.startsWith('接口调用失败'))" class="st-badge warn">
                    ⚠ 没连上大模型
                  </span>
                  <span v-else-if="r.format_ok === false" class="st-badge bad">✗ 格式不合格</span>
                  <span v-else class="st-badge bad">✗ 规则未通过</span>
                </td>
                <td>
                  <ul v-if="r.errors?.length" class="st-err-list compact"><li v-for="(e, k) in r.errors" :key="k">{{ e }}</li></ul>
                  <span v-else class="st-muted">—</span>
                </td>
                <td class="st-num">{{ r.duration_ms ? `${(r.duration_ms / 1000).toFixed(1)}s` : '—' }}</td>
                <td class="st-num">{{ r.tokens || '—' }}</td>
              </tr>
              <tr v-if="!runs.length"><td colspan="7" class="st-empty">暂无记录</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.skin {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin: 8px 0 14px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--s-border);
  background: var(--s-bg);
  color: var(--s-text);
  font-size: 15px;
}
.skin-board { display: block; }
.skin-flow { display: inline-flex; gap: 4px; }
.skin-flow span {
  width: 34px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--s-radius, 6px);
  border: 2px solid var(--s-border-strong);
  background: var(--s-card);
  font-size: 13px;
}
.skin-flow .is-done { background: var(--s-accent-soft); border-color: var(--s-accent); color: var(--s-accent-ink); }
.skin-flow .is-cur { background: var(--s-accent); border-color: var(--s-accent); color: #fff; }
.skin-opt {
  padding: 6px 12px;
  border-radius: var(--s-radius-card, 8px);
  border: 2px solid var(--s-accent);
  background: var(--s-card);
  color: var(--s-text);
}
.skin-opt b { color: var(--s-accent-ink); margin-left: 8px; }
.skin-btn {
  padding: 6px 18px;
  border-radius: var(--s-radius, 6px);
  background: var(--s-accent);
  color: #fff;
  font-weight: 600;
}
.two-col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; align-items: start; }
@media (max-width: 1000px) { .two-col { grid-template-columns: 1fr; } }
.check-ok { border-color: var(--status-ac-dot); }
.check-ok h2 { color: var(--status-ac-text); }
.check-bad { border-color: var(--status-wa-dot); }
.check-bad h2 { color: var(--status-wa-text); }
.ok-notice { border-color: var(--status-ac-dot); background: var(--status-ac-bg); color: var(--status-ac-text); }
.story { margin: 0 0 6px; font-weight: 600; color: var(--text-primary); }
.gap { margin-top: 14px; }
.chip {
  display: inline-block;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 1px 8px;
  margin: 0 4px 4px 0;
  font-size: 13px;
}
.step-list { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 14px; }
.step { border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
.step-head { display: flex; gap: 8px; align-items: center; margin: 0 0 6px; }
.prompt { margin: 0 0 8px; font-size: 15px; color: var(--text-primary); }
.opts { list-style: none; padding: 0; margin: 0 0 8px; font-size: 14px; }
.opts li { padding: 2px 0; }
.opts li.right { color: var(--status-ac-text); }
.hints { margin: 8px 0 0; padding-left: 18px; font-size: 13px; color: var(--text-secondary); }
mark { background: var(--status-ac-bg); color: var(--status-ac-text); padding: 0 2px; border-radius: 3px; }
.analysis { margin-top: 16px; font-size: 13px; color: var(--text-secondary); }
.analysis summary { cursor: pointer; }
.edit-head { justify-content: space-between; }
.edit-head h2 { margin: 0; }
.json-toggle { cursor: pointer; }
.edit { border: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 10px; }
.fld { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--text-secondary); }
.fld.grow { flex: 1; }
.edit-step { border-top: 1px solid var(--border); padding-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.opt { flex: 1; width: auto; }
.mono { font-family: var(--font-mono); }
.w-sm { width: 120px; }
.w-xs { width: 70px; }
.warn-text { color: var(--status-wa-text); font-weight: 600; }
.save-row { margin-top: 6px; }
.compact { margin: 0; padding-left: 16px; }
</style>
