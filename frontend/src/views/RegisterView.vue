<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const username = ref('')
const password = ref('')
const password2 = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const registerState = ref('idle') // idle | success | failure

const focusState = ref('none')
const svgRef = ref(null)
const mouse = reactive({ x: 0, y: 0 })

const charCenters = {
  orange: { svgX: 95,  svgY: 280 },
  purple: { svgX: 185, svgY: 210 },
  black:  { svgX: 255, svgY: 220 },
  yellow: { svgX: 320, svgY: 220 },
}

const eyeOffsets = reactive({
  orange: { x: 0, y: 0 },
  purple: { x: 0, y: 0 },
  black:  { x: 0, y: 0 },
  yellow: { x: 0, y: 0 },
})

function getSvgScreenPos(svgX, svgY) {
  if (!svgRef.value) return { x: 0, y: 0 }
  const rect = svgRef.value.getBoundingClientRect()
  const scaleX = rect.width / 420
  const scaleY = rect.height / 320
  return {
    x: rect.left + svgX * scaleX,
    y: rect.top + svgY * scaleY,
  }
}

function onMouseMove(e) {
  mouse.x = e.clientX
  mouse.y = e.clientY
  for (const [id, c] of Object.entries(charCenters)) {
    const pos = getSvgScreenPos(c.svgX, c.svgY)
    const dx = e.clientX - pos.x
    const dy = e.clientY - pos.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    const max = 2.8
    if (dist > 0) {
      eyeOffsets[id].x = (dx / dist) * Math.min(max, dist / 50)
      eyeOffsets[id].y = (dy / dist) * Math.min(max, dist / 50)
    }
  }
}

onMounted(() => window.addEventListener('mousemove', onMouseMove))
onUnmounted(() => window.removeEventListener('mousemove', onMouseMove))

const expr = computed(() => {
  const st = registerState.value
  const fs = focusState.value
  const inPw = fs === 'password' || fs === 'password2'
  const peek = showPassword.value

  return {
    orange: {
      eyeOpen: st === 'failure' ? 0.5 : inPw ? (peek ? 1.2 : 0) : fs === 'username' ? 1.3 : 1,
      mouthType: st === 'success' ? 'big-smile' : st === 'failure' ? 'sad' : inPw && peek ? 'sneak' : 'smile',
      bodyTilt: fs === 'username' ? -8 : inPw && peek ? 4 : 0,
      bodyBounce: st === 'success',
      bodyShake: st === 'failure',
      curious: fs === 'username',
    },
    purple: {
      eyeOpen: st === 'failure' ? 0.5 : inPw ? 0 : fs === 'username' ? 1.3 : 1,
      mouthType: st === 'success' ? 'big-smile' : st === 'failure' ? 'sad' : 'flat',
      bodyTilt: fs === 'username' ? -12 : inPw ? -6 : 0,
      bodyBounce: st === 'success',
      bodyShake: st === 'failure',
      curious: fs === 'username',
    },
    black: {
      eyeOpen: st === 'failure' ? 0.5 : inPw ? 0 : fs === 'username' ? 1.4 : 1,
      mouthType: st === 'success' ? 'big-smile' : st === 'failure' ? 'sad' : fs === 'username' ? 'o' : 'small',
      bodyTilt: fs === 'username' ? -10 : inPw ? -4 : 0,
      bodyBounce: st === 'success',
      bodyShake: st === 'failure',
      curious: fs === 'username',
    },
    yellow: {
      eyeOpen: st === 'failure' ? 0.5 : inPw ? 0 : fs === 'username' ? 1.3 : 1,
      mouthType: st === 'success' ? 'big-smile' : st === 'failure' ? 'sad' : 'flat',
      bodyTilt: fs === 'username' ? -8 : inPw ? -4 : 0,
      bodyBounce: st === 'success',
      bodyShake: st === 'failure',
      curious: fs === 'username',
    },
  }
})

async function submit() {
  if (!username.value || !password.value || !password2.value) {
    error.value = '请填写所有字段'
    return
  }
  if (password.value !== password2.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  registerState.value = 'idle'
  error.value = ''
  try {
    await userStore.register(username.value, password.value, password2.value)
    registerState.value = 'success'
    setTimeout(() => { router.push('/') }, 900)
  } catch (e) {
    registerState.value = 'failure'
    error.value = e.response?.data?.detail || '注册失败，请稍后重试'
    setTimeout(() => { registerState.value = 'idle' }, 2200)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="left-panel">
      <svg
        ref="svgRef"
        class="chars-svg"
        viewBox="0 0 420 320"
        xmlns="http://www.w3.org/2000/svg"
      >
        <!-- Orange semicircle -->
        <g
          :transform="`translate(95,300) rotate(${expr.orange.bodyTilt})`"
          :class="{ bounce: expr.orange.bodyBounce, shake: expr.orange.bodyShake }"
        >
          <path d="M -75,0 A 75,75 0 0 1 75,0 Z" fill="#F97316" />
          <path d="M -75,0 Q -75,20 0,20 Q 75,20 75,0 Z" fill="#EA6C0A" />
          <ellipse cx="-26" cy="-28" :rx="8" :ry="8 * expr.orange.eyeOpen" fill="white" />
          <circle :cx="-26 + eyeOffsets.orange.x" :cy="-28 + eyeOffsets.orange.y" r="4" fill="#1a1a1a" />
          <ellipse cx="26" cy="-28" :rx="8" :ry="8 * expr.orange.eyeOpen" fill="white" />
          <circle :cx="26 + eyeOffsets.orange.x" :cy="-28 + eyeOffsets.orange.y" r="4" fill="#1a1a1a" />
          <path v-if="expr.orange.mouthType === 'smile'" d="M -18,-10 Q 0,-2 18,-10" fill="none" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round" />
          <path v-else-if="expr.orange.mouthType === 'big-smile'" d="M -20,-12 Q 0,2 20,-12" fill="none" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round" />
          <path v-else-if="expr.orange.mouthType === 'sad'" d="M -18,-6 Q 0,-16 18,-6" fill="none" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round" />
        </g>

        <!-- Purple rectangle -->
        <g
          :transform="`translate(185,${expr.purple.curious ? 205 : 220}) rotate(${expr.purple.bodyTilt})`"
          :class="{ bounce: expr.purple.bodyBounce, shake: expr.purple.bodyShake }"
        >
          <rect x="-30" y="-115" width="60" height="130" rx="6" fill="#7C3AED" />
          <rect x="-30" y="-5" width="60" height="10" rx="0" fill="#6D28D9" />
          <ellipse cx="-12" cy="-80" :rx="7" :ry="7 * expr.purple.eyeOpen" fill="white" />
          <circle v-if="expr.purple.eyeOpen > 0" :cx="-12 + eyeOffsets.purple.x" :cy="-80 + eyeOffsets.purple.y" r="3.5" fill="#1a1a1a" />
          <line v-if="expr.purple.eyeOpen === 0" x1="-18" y1="-80" x2="-6" y2="-80" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round" />
          <ellipse cx="12" cy="-80" :rx="7" :ry="7 * expr.purple.eyeOpen" fill="white" />
          <circle v-if="expr.purple.eyeOpen > 0" :cx="12 + eyeOffsets.purple.x" :cy="-80 + eyeOffsets.purple.y" r="3.5" fill="#1a1a1a" />
          <line v-if="expr.purple.eyeOpen === 0" x1="6" y1="-80" x2="18" y2="-80" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round" />
          <line v-if="expr.purple.mouthType === 'flat'" x1="-12" y1="-58" x2="12" y2="-58" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
          <path v-else-if="expr.purple.mouthType === 'sneak'" d="M -12,-60 Q 0,-54 12,-60" fill="none" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
          <path v-else-if="expr.purple.mouthType === 'big-smile'" d="M -14,-62 Q 0,-50 14,-62" fill="none" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round" />
          <path v-else-if="expr.purple.mouthType === 'sad'" d="M -12,-54 Q 0,-62 12,-54" fill="none" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
        </g>

        <!-- Black tall rectangle -->
        <g
          :transform="`translate(255,${expr.black.curious ? 218 : 230}) rotate(${expr.black.bodyTilt})`"
          :class="{ bounce: expr.black.bodyBounce, shake: expr.black.bodyShake }"
        >
          <rect x="-22" y="-100" width="44" height="115" rx="4" fill="#1a1a1a" />
          <ellipse cx="-9" cy="-68" :rx="6" :ry="6 * expr.black.eyeOpen" fill="white" />
          <circle v-if="expr.black.eyeOpen > 0" :cx="-9 + eyeOffsets.black.x" :cy="-68 + eyeOffsets.black.y" r="3" fill="#1a1a30" />
          <line v-if="expr.black.eyeOpen === 0" x1="-14" y1="-68" x2="-4" y2="-68" stroke="white" stroke-width="2" stroke-linecap="round" />
          <ellipse cx="9" cy="-68" :rx="6" :ry="6 * expr.black.eyeOpen" fill="white" />
          <circle v-if="expr.black.eyeOpen > 0" :cx="9 + eyeOffsets.black.x" :cy="-68 + eyeOffsets.black.y" r="3" fill="#1a1a30" />
          <line v-if="expr.black.eyeOpen === 0" x1="4" y1="-68" x2="14" y2="-68" stroke="white" stroke-width="2" stroke-linecap="round" />
          <circle v-if="expr.black.mouthType === 'o' || expr.black.mouthType === 'small'" cx="0" cy="-50" :r="expr.black.mouthType === 'o' ? 6 : 3" fill="none" stroke="white" :stroke-width="expr.black.mouthType === 'o' ? 2.5 : 2" />
          <path v-else-if="expr.black.mouthType === 'big-smile'" d="M -12,-54 Q 0,-43 12,-54" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" />
          <path v-else-if="expr.black.mouthType === 'sad'" d="M -10,-46 Q 0,-54 10,-46" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" />
        </g>

        <!-- Yellow rounded rectangle -->
        <g
          :transform="`translate(320,${expr.yellow.curious ? 215 : 228}) rotate(${expr.yellow.bodyTilt})`"
          :class="{ bounce: expr.yellow.bodyBounce, shake: expr.yellow.bodyShake }"
        >
          <rect x="-26" y="-95" width="52" height="110" rx="26" fill="#FBBF24" />
          <ellipse cx="-9" cy="-60" :rx="6" :ry="6 * expr.yellow.eyeOpen" fill="white" />
          <circle v-if="expr.yellow.eyeOpen > 0" :cx="-9 + eyeOffsets.yellow.x" :cy="-60 + eyeOffsets.yellow.y" r="3" fill="#1a1a1a" />
          <line v-if="expr.yellow.eyeOpen === 0" x1="-14" y1="-60" x2="-4" y2="-60" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
          <ellipse cx="9" cy="-60" :rx="6" :ry="6 * expr.yellow.eyeOpen" fill="white" />
          <circle v-if="expr.yellow.eyeOpen > 0" :cx="9 + eyeOffsets.yellow.x" :cy="-60 + eyeOffsets.yellow.y" r="3" fill="#1a1a1a" />
          <line v-if="expr.yellow.eyeOpen === 0" x1="4" y1="-60" x2="14" y2="-60" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
          <line v-if="expr.yellow.mouthType === 'flat'" x1="-10" y1="-42" x2="10" y2="-42" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
          <path v-else-if="expr.yellow.mouthType === 'big-smile'" d="M -12,-45 Q 0,-35 12,-45" fill="none" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
          <path v-else-if="expr.yellow.mouthType === 'sad'" d="M -10,-38 Q 0,-46 10,-38" fill="none" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round" />
        </g>
      </svg>
    </div>

    <div class="right-panel">
      <div class="form-card">
        <div class="logo-icon">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="#1a1a1a"/>
            <path d="M16 8 L22 14 L16 20 L10 14 Z" fill="white"/>
          </svg>
        </div>

        <h1 class="form-title">Create account</h1>
        <p class="form-subtitle">Join us and start competing</p>

        <div v-if="error" class="error-banner">{{ error }}</div>

        <form @submit.prevent="submit" novalidate>
          <div class="field">
            <label>用户名 <span class="hint">（3~20 位字母/数字/下划线）</span></label>
            <input
              v-model="username"
              type="text"
              placeholder="Enter your username"
              autocomplete="username"
              @focus="focusState = 'username'"
              @blur="focusState = 'none'"
            />
          </div>

          <div class="field">
            <label>Password <span class="hint">（至少 6 位）</span></label>
            <div class="pw-wrap">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="new-password"
                @focus="focusState = 'password'"
                @blur="focusState = 'none'"
              />
              <button
                type="button"
                class="eye-btn"
                @mousedown="showPassword = true"
                @mouseup="showPassword = false"
                @mouseleave="showPassword = false"
                tabindex="-1"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </div>

          <div class="field">
            <label>Confirm Password</label>
            <input
              v-model="password2"
              :type="showPassword ? 'text' : 'password'"
              placeholder="••••••••"
              autocomplete="new-password"
              @focus="focusState = 'password2'"
              @blur="focusState = 'none'"
            />
          </div>

          <button
            type="submit"
            class="btn-login"
            :disabled="loading"
            :class="{ success: registerState === 'success', failure: registerState === 'failure' }"
          >
            {{ loading ? 'Creating...' : registerState === 'success' ? 'Welcome!' : 'Sign Up' }}
          </button>
        </form>

        <p class="signup-link">
          Already have an account? <RouterLink to="/login">Log In</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #fff;
}

.left-panel {
  flex: 0 0 52%;
  background: #e8e8e8;
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
}

.chars-svg {
  width: 100%;
  max-width: 460px;
  height: auto;
  flex-shrink: 0;
}

.right-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  overflow-y: auto;
}

.form-card {
  width: 100%;
  max-width: 400px;
}

.logo-icon { margin-bottom: 1.5rem; }

.form-title {
  font-size: 1.8rem;
  font-weight: 800;
  color: #111;
  margin: 0 0 0.3rem;
  letter-spacing: -0.02em;
}

.form-subtitle {
  color: #888;
  font-size: 0.9rem;
  margin: 0 0 2rem;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #dc2626;
  padding: 0.6rem 0.9rem;
  border-radius: 8px;
  font-size: 0.85rem;
  margin-bottom: 1.2rem;
}

.field { margin-bottom: 1.2rem; }

.field label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #111;
  margin-bottom: 0.5rem;
}

.hint { font-size: 0.75rem; color: #aaa; font-weight: 400; }

.field input {
  width: 100%;
  padding: 0.65rem 0;
  border: none;
  border-bottom: 1.5px solid #ddd;
  outline: none;
  font-size: 0.95rem;
  color: #111;
  background: transparent;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.field input:focus { border-bottom-color: #111; }
.field input::placeholder { color: #bbb; }

.pw-wrap { position: relative; display: flex; align-items: center; }
.pw-wrap input { flex: 1; padding-right: 2rem; }

.eye-btn {
  position: absolute;
  right: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: #aaa;
  padding: 0;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}

.eye-btn:hover { color: #555; }

.btn-login {
  width: 100%;
  padding: 0.85rem;
  background: #111;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 0.5rem;
  margin-bottom: 0;
}

.btn-login:hover:not(:disabled) { background: #333; }
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-login.success { background: #16a34a; }
.btn-login.failure { background: #dc2626; animation: shake-btn 0.4s; }

.signup-link {
  margin-top: 1.5rem;
  text-align: center;
  font-size: 0.875rem;
  color: #888;
}

.signup-link a {
  color: #111;
  font-weight: 700;
  text-decoration: none;
}

.signup-link a:hover { text-decoration: underline; }

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  30% { transform: translateY(-16px); }
  60% { transform: translateY(-6px); }
}

@keyframes shake {
  0%, 100% { transform: translateX(0) rotate(0deg); }
  20% { transform: translateX(-6px) rotate(-3deg); }
  40% { transform: translateX(6px) rotate(3deg); }
  60% { transform: translateX(-4px) rotate(-2deg); }
  80% { transform: translateX(4px) rotate(2deg); }
}

@keyframes shake-btn {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-6px); }
  75% { transform: translateX(6px); }
}

.bounce { animation: bounce 0.7s ease; }
.shake  { animation: shake  0.5s ease; }

g { transition: transform 0.35s cubic-bezier(.34,1.56,.64,1); }
</style>
