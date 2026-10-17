<script setup>
// 批量布置：选一个团队里的学生、选若干任务，一次发下去。
// 用的是不经大模型的默认版本（关卡套学生的兴趣主题包，入门题用通用分步任务），所以几秒钟就能发完；
// 需要按画像个性化改造的学生，仍到学生详情页单独发起。
import '@/assets/star-teacher.css'
import { computed, onMounted, ref, watch } from 'vue'
import { assignTasks, getAssignData, getMaterials } from '@/api/star'

const LAYER = { enlighten: '启蒙层', intro: '入门层' }
const KNOW = { sequence: '顺序', loop: '循环', condition: '条件' }

const teams = ref([])
const materials = ref(null)
const teamId = ref(null)
const picked = ref([])          // 学生 user_id
const chosen = ref([])          // 素材 key，按勾选顺序
const approve = ref(true)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const result = ref(null)

async function load() {
  const [a, m] = await Promise.all([getAssignData(), getMaterials()])
  teams.value = a.data.teams
  materials.value = m.data
  if (!teams.value.some((t) => t.id === teamId.value)) {
    teamId.value = (teams.value.find((t) => t.learners.length) || teams.value[0])?.id ?? null
  }
}

onMounted(async () => {
  try {
    await load()
  } catch (e) {
    error.value = e.response?.status === 403 ? '需要教师或管理员权限' : '加载失败，请刷新重试'
  } finally {
    loading.value = false
  }
})

const team = computed(() => teams.value.find((t) => t.id === teamId.value))
const learners = computed(() => team.value?.learners || [])
watch(teamId, () => { picked.value = [] })

const byKey = computed(() => {
  const m = {}
  for (const l of materials.value?.levels || []) m[l.key] = { ...l, layer: 'enlighten' }
  for (const p of materials.value?.problems || []) m[p.key] = { ...p, layer: 'intro' }
  return m
})
const problemGroups = computed(() => ['sequence', 'condition', 'loop'].map((k) => ({
  key: k,
  items: (materials.value?.problems || []).filter((p) => p.knowledge === k),
})))

function toggleMaterial(key) {
  chosen.value = chosen.value.includes(key) ? chosen.value.filter((k) => k !== key) : [...chosen.value, key]
}
function pickLayer(layer) {
  picked.value = learners.value.filter((l) => l.layer === layer).map((l) => l.user_id)
}
function haveCount(key) {
  return learners.value.filter((l) => picked.value.includes(l.user_id) && l.templates.includes(key)).length
}

// 预估：每名学生能拿到几项（层级对得上、还没有的）
const plan = computed(() => learners.value
  .filter((l) => picked.value.includes(l.user_id))
  .map((l) => ({
    ...l,
    gets: chosen.value.filter((k) => byKey.value[k]?.layer === l.layer && !l.templates.includes(k)),
  })))
const planTotal = computed(() => plan.value.reduce((n, l) => n + l.gets.length, 0))

const title = (key) => byKey.value[key]?.title || key

async function submit() {
  if (!picked.value.length || !chosen.value.length) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    const { data } = await assignTasks({ learners: picked.value, materials: chosen.value, approve: approve.value })
    result.value = data
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || '布置失败，请重试'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="st-page">
    <header class="st-head">
      <div>
        <h1>星语 · 批量布置任务</h1>
        <p class="st-muted">
          选学生、选任务，一次发下去。用的是默认版本：关卡按每个学生的兴趣换主题，入门题是通用的分步任务，
          每道都以"排一排代码 → 自己写代码"收尾。要按画像个性化改造，请到学生详情页单独发起。
        </p>
      </div>
      <div class="st-head-actions">
        <RouterLink class="st-btn" :to="{ name: 'star-teacher' }">← 学习者列表</RouterLink>
      </div>
    </header>

    <div v-if="error" class="st-error">{{ error }}</div>
    <p v-if="loading" class="st-muted">加载中…</p>

    <template v-else-if="materials">
      <!-- ═════ 1 选学生 ═════ -->
      <section class="st-card">
        <h2>1. 选学生</h2>
        <p v-if="!teams.length" class="st-muted">你还没有创建团队。先在"团队"里建一个团队、让学生加入，学生填完星语问卷后会出现在这里。</p>
        <template v-else>
          <div class="st-row">
            <label for="a-team" class="st-muted">团队</label>
            <select id="a-team" v-model="teamId" class="st-select">
              <option v-for="t in teams" :key="t.id" :value="t.id">{{ t.name }}（{{ t.learners.length }} 名学习者）</option>
            </select>
            <button type="button" class="st-btn st-btn-sm" @click="pickLayer('enlighten')">选全部启蒙层</button>
            <button type="button" class="st-btn st-btn-sm" @click="pickLayer('intro')">选全部入门层</button>
            <button type="button" class="st-btn st-btn-sm" @click="picked = learners.map((l) => l.user_id)">全选</button>
            <button type="button" class="st-btn st-btn-sm" @click="picked = []">清空</button>
          </div>
          <div class="st-table-wrap">
            <table class="st-table">
              <thead>
                <tr><th class="w-check"></th><th>昵称</th><th>账号</th><th>层级</th><th>已有任务</th></tr>
              </thead>
              <tbody>
                <tr v-for="l in learners" :key="l.user_id" :class="{ 'is-off': !l.layer }">
                  <td>
                    <input
                      v-model="picked"
                      type="checkbox"
                      :value="l.user_id"
                      :disabled="!l.layer"
                      :aria-label="`选择 ${l.nickname}`"
                    >
                  </td>
                  <td><b>{{ l.nickname }}</b></td>
                  <td class="st-num">{{ l.username }}</td>
                  <td>
                    <span v-if="l.layer">{{ LAYER[l.layer] }}</span>
                    <span v-else class="st-muted">还没定层级</span>
                  </td>
                  <td class="st-num">{{ l.templates.length }}</td>
                </tr>
                <tr v-if="!learners.length">
                  <td colspan="5" class="st-empty">这个团队里还没有填过星语问卷的学生。</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </section>

      <!-- ═════ 2 选任务 ═════ -->
      <section class="st-card">
        <h2>2. 选任务 <span class="st-muted">（学生看到的顺序 = 勾选的顺序）</span></h2>
        <div class="mat-grid">
          <fieldset class="mat-col">
            <legend>启蒙层 · 卡片闯关</legend>
            <label v-for="lv in materials.levels" :key="lv.key" class="mat">
              <input
                type="checkbox"
                :checked="chosen.includes(lv.key)"
                :aria-label="`${lv.key} ${lv.title}`"
                @change="toggleMaterial(lv.key)"
              >
              <span class="seq">{{ chosen.includes(lv.key) ? chosen.indexOf(lv.key) + 1 : '' }}</span>
              <span class="mat-name">{{ lv.key }} {{ lv.title }}</span>
              <span class="st-badge plain">{{ KNOW[lv.knowledge] }}</span>
              <span v-if="haveCount(lv.key)" class="st-muted">{{ haveCount(lv.key) }} 人已有</span>
            </label>
          </fieldset>
          <fieldset class="mat-col">
            <legend>入门层 · 分步学习 → 自己写代码</legend>
            <template v-for="g in problemGroups" :key="g.key">
              <p class="grp">{{ KNOW[g.key] }}</p>
              <label v-for="p in g.items" :key="p.key" class="mat" :class="{ 'is-off': !p.problem_id }">
                <input
                  type="checkbox"
                  :checked="chosen.includes(p.key)"
                  :disabled="!p.problem_id"
                  :aria-label="p.title"
                  @change="toggleMaterial(p.key)"
                >
                <span class="seq">{{ chosen.includes(p.key) ? chosen.indexOf(p.key) + 1 : '' }}</span>
                <span class="mat-name">{{ p.title }}</span>
                <span v-if="!p.problem_id" class="st-muted">题库里还没有，先运行 seed_star</span>
                <span v-else-if="haveCount(p.key)" class="st-muted">{{ haveCount(p.key) }} 人已有</span>
              </label>
            </template>
          </fieldset>
        </div>
      </section>

      <!-- ═════ 3 确认 ═════ -->
      <section class="st-card">
        <h2>3. 确认并布置</h2>
        <p v-if="!picked.length || !chosen.length" class="st-muted">先选学生和任务。</p>
        <template v-else>
          <ul class="plan">
            <li v-for="l in plan" :key="l.user_id">
              <b>{{ l.nickname }}</b>（{{ LAYER[l.layer] }}）：
              <span v-if="l.gets.length">{{ l.gets.map(title).join('、') }}</span>
              <span v-else class="st-muted">没有新任务（层级不对或已经有了）</span>
            </li>
          </ul>
          <label class="approve">
            <input v-model="approve" type="checkbox">
            直接发给学生（默认版本已通过全部规则校验）；不勾选则先放进待审核，逐个看过再通过
          </label>
          <div class="st-row">
            <button type="button" class="st-btn st-btn-primary" :disabled="busy || !planTotal" @click="submit">
              {{ busy ? '布置中…' : `布置 ${planTotal} 项任务` }}
            </button>
          </div>
        </template>

        <div v-if="result" class="result">
          <p :class="result.created_total ? 'ok-line' : 'st-muted'">
            {{ result.created_total
              ? `已布置 ${result.created_total} 项任务${result.approved ? '，学生现在就能看到。' : '，在学生详情页里待审核。'}`
              : '没有新布置的任务。' }}
          </p>
          <table class="st-table">
            <thead><tr><th>学生</th><th>新布置</th><th>跳过</th></tr></thead>
            <tbody>
              <tr v-for="r in result.results" :key="r.user_id">
                <td>
                  <RouterLink :to="{ name: 'star-learner', params: { uid: r.user_id } }">{{ r.nickname }}</RouterLink>
                </td>
                <td>{{ r.created.map((c) => c.title).join('、') || '—' }}</td>
                <td class="st-muted">
                  <span v-for="s in r.skipped" :key="s.template" class="skip">{{ title(s.template) }}：{{ s.reason }}</span>
                  <span v-if="!r.skipped.length">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.w-check { width: 36px; }
tr.is-off td { color: var(--text-secondary); }
.mat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 760px) { .mat-grid { grid-template-columns: 1fr; } }
.mat-col { border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px 14px; margin: 0; min-width: 0; }
.mat-col legend { font-size: 14px; font-weight: 600; padding: 0 6px; color: var(--text-primary); }
.grp { font-size: 12.5px; color: var(--text-secondary); margin: 10px 0 2px; }
.mat { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 14px; cursor: pointer; flex-wrap: wrap; }
.mat.is-off { cursor: not-allowed; color: var(--text-secondary); }
.seq {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 12px;
  font-family: var(--font-mono);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent);
  color: #fff;
}
.seq:empty { background: transparent; border: 1px dashed var(--border-strong); }
.mat-name { color: var(--text-primary); }
.plan { margin: 0 0 12px; padding-left: 18px; font-size: 14px; display: flex; flex-direction: column; gap: 4px; }
.approve { display: flex; gap: 8px; align-items: flex-start; font-size: 14px; margin-bottom: 12px; }
.result { margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px; }
.ok-line { color: var(--status-ac-text); font-weight: 600; margin: 0 0 10px; }
.skip { display: block; }
</style>
