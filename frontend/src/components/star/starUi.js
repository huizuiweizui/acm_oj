// 星语学生端的界面定制：后端按问卷算出 ui（背景、主色、按钮形状……，见 star/services/profile.py
// 的 build_ui），这里把它换成 CSS 变量。所有色值都是低饱和、白字对比度足够的版本。
//
// 定制在填完问卷时定一次，之后不变；只有学生在问卷里说"需要"时，页头才出现
// 调字号 / 换颜色的按钮，选择记在本机浏览器里。
import { computed, reactive } from 'vue'

const BACKGROUNDS = {
  warm:  { bg: '#f5f4ef', card: '#ffffff', border: '#d6d3c8', strong: '#a8a496', text: '#1f2328', text2: '#454c55', code: '#f3f2ec' },
  white: { bg: '#ffffff', card: '#ffffff', border: '#d9dce1', strong: '#a3a9b3', text: '#1f2328', text2: '#454c55', code: '#f4f5f7' },
  gray:  { bg: '#eceef1', card: '#ffffff', border: '#d3d7dd', strong: '#9da4ae', text: '#1f2328', text2: '#454c55', code: '#f1f2f4' },
  blue:  { bg: '#e3eef8', card: '#ffffff', border: '#c9d9e8', strong: '#93a9be', text: '#1f2328', text2: '#454c55', code: '#eef4fa' },
  green: { bg: '#e5f2e3', card: '#ffffff', border: '#cbe0c8', strong: '#95ad91', text: '#1f2328', text2: '#454c55', code: '#eef6ed' },
  dark:  { bg: '#1c1e22', card: '#26292e', border: '#3a3e45', strong: '#5d636d', text: '#eceef1', text2: '#b6bcc6', code: '#202328' },
}

export const ACCENTS = {
  blue:   { name: '蓝色', accent: '#2f5f8f', hover: '#264e76', soft: '#e7eef5', darkSoft: '#24384d', ink: '#8fb8e3' },
  green:  { name: '绿色', accent: '#2e6b45', hover: '#24563a', soft: '#e3f0e7', darkSoft: '#22382b', ink: '#8fcfa5' },
  yellow: { name: '黄色', accent: '#7a6200', hover: '#634f00', soft: '#f7efcc', darkSoft: '#3a3416', ink: '#e3cb6a' },
  orange: { name: '橙色', accent: '#9a4f16', hover: '#7f4112', soft: '#f8e8da', darkSoft: '#3d2c1f', ink: '#efab76' },
  pink:   { name: '粉色', accent: '#9c3d68', hover: '#833355', soft: '#f6e3ec', darkSoft: '#3d2532', ink: '#eb9cc0' },
  red:    { name: '红色', accent: '#9b2c2c', hover: '#822424', soft: '#f8e6e4', darkSoft: '#3d2222', ink: '#ee9a95' },
  purple: { name: '紫色', accent: '#5f4596', hover: '#4f397e', soft: '#ece6f5', darkSoft: '#2f2842', ink: '#b9a3e8' },
}

// 按钮 / 卡片圆角：圆形 → 胶囊按钮，方形 → 直角，长方形 → 小圆角
const SHAPES = {
  round:  { btn: '999px', card: '20px' },
  square: { btn: '2px', card: '2px' },
  soft:   { btn: '6px', card: '8px' },
}

const FONT_STEPS = [0.9, 1, 1.15, 1.3, 1.45]
const KEY_FONT = 'star-font-step'
const KEY_ACCENT = 'star-accent'

function readStore(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function writeStore(key, value) {
  try { localStorage.setItem(key, value) } catch { /* 隐私模式等情况下不保存，不影响使用 */ }
}

export const starUi = reactive({ ui: null, fontStep: 1, accent: '' })

export function setStarUi(ui) {
  starUi.ui = ui || null
  const step = Number(readStore(KEY_FONT))
  starUi.fontStep = ui?.font_adjust && Number.isInteger(step) && FONT_STEPS[step] ? step : 1
  const accent = readStore(KEY_ACCENT)
  starUi.accent = ui?.color_choice && ACCENTS[accent] ? accent : ''
}

export function changeFont(delta) {
  const next = Math.min(FONT_STEPS.length - 1, Math.max(0, starUi.fontStep + delta))
  starUi.fontStep = next
  writeStore(KEY_FONT, String(next))
}

export function chooseAccent(key) {
  if (!ACCENTS[key]) return
  starUi.accent = key
  writeStore(KEY_ACCENT, key)
}

// 换颜色时可选的颜色：问卷里"喜欢"的颜色；一个都没有就给全部
export const accentChoices = computed(() => {
  const liked = starUi.ui?.liked_colors || []
  return (liked.length ? liked : Object.keys(ACCENTS)).filter((k) => ACCENTS[k])
})

export const canZoomOut = computed(() => starUi.fontStep > 0)
export const canZoomIn = computed(() => starUi.fontStep < FONT_STEPS.length - 1)
export const starMark = computed(() => starUi.ui?.mark || '✓')

export const BG_NAMES = { warm: '米色', white: '白色', gray: '浅灰', blue: '浅蓝', green: '浅绿', dark: '深色' }
export const BUTTON_NAMES = { round: '胶囊按钮', square: '直角按钮', soft: '小圆角按钮' }

// 某个学生的界面设置 → CSS 变量。学生端用它，教师审核页的预览也用它（按学生看到的样子画）
export function themeVars(ui, { accent = '', fontStep = 1 } = {}) {
  ui = ui || {}
  const bg = BACKGROUNDS[ui.bg] || BACKGROUNDS.warm
  const ac = ACCENTS[accent || ui.accent] || ACCENTS.blue
  const shape = SHAPES[ui.button] || SHAPES.soft
  const dark = ui.bg === 'dark'
  return {
    '--s-bg': bg.bg,
    '--s-card': bg.card,
    '--s-border': bg.border,
    '--s-border-strong': bg.strong,
    '--s-text': bg.text,
    '--s-text-2': bg.text2,
    '--s-code-bg': bg.code,
    '--s-accent': ac.accent,
    '--s-accent-hover': ac.hover,
    '--s-accent-soft': dark ? ac.darkSoft : ac.soft,
    // 文字用的主色：深色背景上换成浅色版本，保证对比度（按钮底色仍用 --s-accent，配白字）
    '--s-accent-ink': dark ? ac.ink : ac.accent,
    '--s-radius': shape.btn,
    '--s-radius-card': shape.card,
    '--s-zoom': FONT_STEPS[fontStep] ?? 1,
    colorScheme: dark ? 'dark' : 'light',
  }
}

export function useStarTheme() {
  const style = computed(() => themeVars(starUi.ui, { accent: starUi.accent, fontStep: starUi.fontStep }))
  return { style }
}
