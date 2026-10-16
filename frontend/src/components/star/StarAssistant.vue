<script setup>
// 对话助手：回复固定是"一句话 + 选项按钮"，学习者点按钮就能回答，也可以自己打字。
// 面板直接出现、直接收起，不做滑入动画。
import { nextTick, ref } from 'vue'
import { chatWithStar } from '@/api/star'

const props = defineProps({
  nickname: { type: String, default: '' },
  taskId: { type: Number, default: null },
  step: { type: Number, default: null },
})

const open = ref(false)
const messages = ref([])
const text = ref('')
const sending = ref(false)
const bodyRef = ref(null)

function greet() {
  if (messages.value.length) return
  messages.value.push({
    role: 'bot',
    text: `${props.nickname || '你好'}，有问题可以问我。`,
    options: ['我要提示', '我没听懂', '我想休息'],
  })
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    greet()
    scrollBottom()
  }
}

async function scrollBottom() {
  await nextTick()
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
}

async function send(content, via = 'text') {
  const t = (content ?? text.value).trim()
  if (!t || sending.value) return
  messages.value.push({ role: 'user', text: t })
  text.value = ''
  sending.value = true
  scrollBottom()
  try {
    const { data } = await chatWithStar({ text: t, via, task_id: props.taskId, step: props.step })
    messages.value.push({ role: 'bot', text: data.reply, options: data.options || [] })
  } catch (e) {
    const limited = e.response?.status === 429
    messages.value.push({
      role: 'bot',
      text: limited ? '我们先休息一下，等会儿再聊。' : '我没有听到，请再说一次。',
      options: ['再说一次', '找老师'],
    })
  } finally {
    sending.value = false
    scrollBottom()
  }
}
</script>

<template>
  <button type="button" class="ask-btn s-btn" :aria-expanded="open" @click="toggle">
    🙋 {{ open ? '收起学伴' : '问学伴' }}
  </button>

  <aside v-if="open" class="assistant" aria-label="学伴对话">
    <header class="a-head">
      <b>学伴</b>
      <button type="button" class="a-close" aria-label="收起" @click="open = false">✕</button>
    </header>
    <div ref="bodyRef" class="a-body" aria-live="polite">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <p class="bubble">{{ m.text }}</p>
        <div v-if="m.role === 'bot' && m.options?.length && i === messages.length - 1" class="a-options">
          <button
            v-for="opt in m.options"
            :key="opt"
            type="button"
            class="s-btn a-opt"
            :disabled="sending"
            @click="send(opt, 'option')"
          >{{ opt }}</button>
        </div>
      </div>
      <p v-if="sending" class="s-muted">学伴在想……</p>
    </div>
    <form class="a-foot" @submit.prevent="send()">
      <input v-model="text" class="a-input" maxlength="200" placeholder="也可以自己打字" aria-label="想说的话">
      <button type="submit" class="s-btn s-btn-primary" :disabled="sending || !text.trim()">发送</button>
    </form>
  </aside>
</template>

<style scoped>
.ask-btn {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 40;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}
.assistant {
  position: fixed;
  right: 24px;
  bottom: 96px;
  width: min(420px, calc(100vw - 48px));
  height: min(560px, calc(100vh - 140px));
  z-index: 41;
  display: flex;
  flex-direction: column;
  background: var(--s-card);
  border: 2px solid var(--s-border-strong);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
.a-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--s-border);
}
.a-close {
  width: 44px;
  height: 44px;
  border: none;
  background: transparent;
  font-size: 20px;
  cursor: pointer;
}
.a-body { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.msg { display: flex; flex-direction: column; gap: 8px; }
.msg.user { align-items: flex-end; }
.bubble {
  margin: 0;
  padding: 10px 14px;
  border-radius: 8px;
  max-width: 90%;
  border: 1px solid var(--s-border);
  background: var(--s-bg);
}
.msg.user .bubble { background: var(--s-accent-soft); border-color: var(--s-accent-ink, var(--s-accent)); }
.a-options { display: flex; flex-wrap: wrap; gap: 8px; }
.a-opt { min-height: 48px; padding: 6px 16px; }
.a-foot { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--s-border); }
.a-input {
  flex: 1;
  min-width: 0;
  font: inherit;
  font-size: 18px;
  padding: 8px 12px;
  border: 2px solid var(--s-border-strong);
  border-radius: 6px;
}
</style>
