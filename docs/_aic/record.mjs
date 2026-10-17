// 星语演示视频：逐场景录屏（CDP screencast，逐帧 JPEG + 时间戳）
//   node record.mjs [场景名 ...]      不带参数录全部场景
// 输出 clips/<场景>/f*.jpg 与 clips/<场景>/frames.txt（ffconcat，带每帧时长）
import fs from 'node:fs'
import path from 'node:path'
import { chromium, loginAs, apiGet, tokens, BASE, API, PW } from './lib.mjs'

const HERE = path.dirname(new URL(import.meta.url).pathname).replace(/^\/(\w:)/, '$1')
const CLIPS = path.join(HERE, 'clips')
const W = 1600, H = 900, DSF = 1.2

const INIT = `
(() => {
  const css = \`#__vue-devtools-container__, [id^="__vue-devtools"], .vue-devtools__anchor { display:none !important; }
  #fake-cursor { position: fixed; z-index: 2147483647; left: 0; top: 0; width: 26px; height: 26px; pointer-events: none;
    transform: translate(-3px, -2px); transition: none; }
  .fake-ripple { position: fixed; z-index: 2147483646; width: 36px; height: 36px; margin: -18px 0 0 -18px; border-radius: 50%;
    background: rgba(255, 170, 0, .45); pointer-events: none; animation: fr .5s ease-out forwards; }
  @keyframes fr { from { transform: scale(.3); opacity: 1 } to { transform: scale(1.6); opacity: 0 } }
  html { scroll-behavior: smooth; }\`
  const add = () => {
    if (document.getElementById('fake-cursor')) return
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s)
    const c = document.createElement('div'); c.id = 'fake-cursor'
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    const p = window.__cursor || { x: ${W / 2}, y: ${H / 2} }
    c.style.left = p.x + 'px'; c.style.top = p.y + 'px'
    document.body.appendChild(c)
  }
  document.addEventListener('mousemove', e => {
    window.__cursor = { x: e.clientX, y: e.clientY }
    sessionStorage.setItem('__cursor', JSON.stringify(window.__cursor))
    const c = document.getElementById('fake-cursor'); if (c) { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px' }
  }, true)
  document.addEventListener('mousedown', e => {
    const r = document.createElement('div'); r.className = 'fake-ripple'
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'
    document.body.appendChild(r); setTimeout(() => r.remove(), 600)
  }, true)
  try { window.__cursor = JSON.parse(sessionStorage.getItem('__cursor')) || undefined } catch {}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add()
  new MutationObserver(add).observe(document.documentElement, { childList: true, subtree: true })
})()`

// ── 录屏 ───────────────────────────────────────────────────────────
async function startRec(page, name) {
  const dir = path.join(CLIPS, name)
  fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true })
  const cdp = await page.context().newCDPSession(page)
  const frames = []
  cdp.on('Page.screencastFrame', (f) => {
    const file = `f${String(frames.length).padStart(5, '0')}.jpg`
    frames.push({ file, t: f.metadata.timestamp })
    fs.writeFileSync(path.join(dir, file), Buffer.from(f.data, 'base64'))
    cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {})
  })
  await cdp.send('Page.startScreencast', {
    format: 'jpeg', quality: 92, maxWidth: Math.round(W * DSF), maxHeight: Math.round(H * DSF), everyNthFrame: 1,
  })
  const t0 = Date.now() / 1000
  return {
    async stop() {
      await page.waitForTimeout(300)
      const end = Date.now() / 1000
      await cdp.send('Page.stopScreencast').catch(() => {})
      if (!frames.length) throw new Error(`${name}: no frames`)
      frames[0].t = Math.min(frames[0].t, t0)
      let txt = 'ffconcat version 1.0\n'
      frames.forEach((f, i) => {
        const next = i + 1 < frames.length ? frames[i + 1].t : end
        txt += `file ${f.file}\nduration ${Math.max(0.001, next - f.t).toFixed(3)}\n`
      })
      txt += `file ${frames[frames.length - 1].file}\n`
      fs.writeFileSync(path.join(dir, 'frames.txt'), txt)
      console.log(`${name}: ${frames.length} frames, ${(end - frames[0].t).toFixed(1)} s`)
    },
  }
}

// ── 动作：带光标移动的点击、逐字输入、平滑滚动 ─────────────────────
const wait = (page, ms) => page.waitForTimeout(ms)
async function moveTo(page, loc) {
  await loc.scrollIntoViewIfNeeded()
  const b = await loc.boundingBox()
  const x = b.x + b.width / 2, y = b.y + b.height / 2
  await page.mouse.move(x, y, { steps: 18 })
  return { x, y }
}
async function click(page, loc, after = 700) {
  await moveTo(page, loc); await wait(page, 250)
  await loc.click(); await wait(page, after)
}
async function type(page, loc, text, delay = 90) {
  await click(page, loc, 200)
  await loc.pressSequentially(text, { delay })
}
async function scrollBy(page, dy, ms = 1200) {
  await page.evaluate((d) => window.scrollBy({ top: d, behavior: 'smooth' }), dy)
  await wait(page, ms)
}
async function scrollTop(page) { await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' })) }

// ── 演示数据准备 ───────────────────────────────────────────────────
async function learnerIds() {
  const t = await tokens('star_teacher')
  const { learners } = await apiGet('/star/teacher/learners/', t.access)
  return Object.fromEntries(learners.map((r) => [r.username, r.user_id]))
}

// ── 场景 ───────────────────────────────────────────────────────────
const SCENES = {
  // 学生第一次进入：图片问卷
  async onboard(page) {
    await loginAs(page, 'star_newbie')
    await page.goto(`${BASE}/star/start`); await wait(page, 1500)
    const rec = await startRec(page, 'onboard')
    await wait(page, 1500)
    for (let i = 0; i < 4; i++) {
      const opts = page.locator('.pic-option')
      if (await opts.count()) {
        await click(page, opts.nth(i === 1 ? 2 : 0), 600)
      } else {
        const rows = page.locator('.scale-row')
        for (let r = 0; r < await rows.count(); r++) await click(page, rows.nth(r).locator('.level').first(), 250)
      }
      await click(page, page.getByRole('button', { name: /下一题/ }), 1100)
    }
    await wait(page, 800)
    await rec.stop()
  },

  // 教师端：小雨的画像
  async profile(page, ids) {
    await loginAs(page, 'star_teacher')
    await page.goto(`${BASE}/star/teacher`); await wait(page, 1500)
    const rec = await startRec(page, 'profile')
    await wait(page, 1500)
    await click(page, page.locator('tr', { hasText: 'star_yu' }).getByRole('link', { name: '查看' }), 1800)
    await scrollBy(page, 330, 2500)
    await moveTo(page, page.getByText('按问卷定制的学生界面')); await wait(page, 1500)
    await moveTo(page, page.getByText('代词逆转')); await wait(page, 1500)
    await moveTo(page, page.getByText('个人词表', { exact: true })); await wait(page, 2500)
    await scrollBy(page, 900, 2500)
    await rec.stop()
  },

  // 教师端：推荐下一项任务 + 审核页
  async recommend(page, ids) {
    await loginAs(page, 'star_teacher')
    await page.goto(`${BASE}/star/teacher/learners/${ids.star_yu}`); await wait(page, 1500)
    const rec = await startRec(page, 'recommend')
    await wait(page, 1000)
    await click(page, page.getByRole('tab', { name: /任务/ }), 1200)
    await click(page, page.getByRole('button', { name: '生成推荐' }), 3500)
    await scrollBy(page, 250, 3000)
    await click(page, page.getByRole('row', { name: /两个数相加/ }).getByRole('link', { name: '查看' }), 2000)
    await scrollBy(page, 400, 2500)
    await scrollBy(page, 500, 2500)
    await rec.stop()
  },

  // 学生端：小雨做「两个数相加」
  async steps(page) {
    await loginAs(page, 'star_yu')
    await page.goto(`${BASE}/star`); await wait(page, 1500)
    const rec = await startRec(page, 'steps')
    await wait(page, 1200)
    await click(page, page.locator('a.s-btn').first(), 1500)
    await click(page, page.getByRole('button', { name: /开始第 1 步/ }), 1200)
    // 第 1 步：先选错，再要提示，再选对
    await click(page, page.getByRole('radio', { name: /输出答案/ }), 500)
    await click(page, page.getByRole('button', { name: '检查' }), 2200)
    await click(page, page.getByRole('button', { name: /提示/ }), 2200)
    await click(page, page.getByRole('radio', { name: /读入两个数/ }), 500)
    await click(page, page.getByRole('button', { name: '检查' }), 1800)
    await click(page, page.getByRole('button', { name: /下一步/ }), 1200)
    // 第 2 步：填空
    await type(page, page.locator('.fill-input'), '+', 200)
    await click(page, page.getByRole('button', { name: '检查' }), 1800)
    await click(page, page.getByRole('button', { name: /下一步/ }), 1200)
    // 第 3 步：排序
    for (const line of ['a = int(input())', 'b = int(input())', 's = a + b', 'print(s)']) {
      await click(page, page.locator('.pool .line', { hasText: line }), 350)
    }
    await click(page, page.getByRole('button', { name: '检查' }), 2600)
    await click(page, page.getByRole('button', { name: /下一步/ }), 1200)
    // 第 4 步：自己写
    const box = page.locator('.code-input')
    await click(page, box, 300)
    await page.keyboard.press('Control+A'); await page.keyboard.press('Delete')
    await box.pressSequentially('# 读入 a 和 b\na = int(input())\nb = int(input())\n# 算出 s\ns = a + b\n# 输出 s\nprint(s)', { delay: 45 })
    await wait(page, 600)
    await click(page, page.getByRole('button', { name: '检查' }), 3500)
    await rec.stop()
  },

  // 学生端：问学伴
  async chat(page) {
    await loginAs(page, 'star_yu')
    await page.goto(`${BASE}/star`); await wait(page, 1200)
    await page.locator('a.s-btn').nth(1).click(); await wait(page, 1200)
    await page.getByRole('button', { name: /开始第 1 步/ }).click(); await wait(page, 800)
    const rec = await startRec(page, 'chat')
    await wait(page, 1000)
    await click(page, page.getByRole('button', { name: /问学伴/ }), 1500)
    await type(page, page.locator('.a-input'), '你不懂', 220)
    await click(page, page.getByRole('button', { name: '发送' }), 4500)
    const opt = page.locator('.a-opt').first()
    if (await opt.count()) { await click(page, opt, 4000) }
    await wait(page, 1500)
    await rec.stop()
  },

  // 启蒙层：小航的卡片闯关
  async level(page) {
    await loginAs(page, 'star_hang')
    await page.goto(`${BASE}/star`); await wait(page, 1500)
    const rec = await startRec(page, 'level')
    await wait(page, 1200)
    await click(page, page.locator('a.s-btn').first(), 1500)
    for (let i = 0; i < 3; i++) await click(page, page.locator('.card-btn').first(), 450)
    await click(page, page.getByRole('button', { name: /运行/ }), 5000)
    const done = page.getByRole('button', { name: /完成这一关/ })
    if (await done.count()) await click(page, done, 2000)
    await rec.stop()
  },

  // 教师端：学习情况、报告、对话记录
  async report(page, ids) {
    await loginAs(page, 'star_teacher')
    await page.goto(`${BASE}/star/teacher/learners/${ids.star_yu}`); await wait(page, 1500)
    const rec = await startRec(page, 'report')
    await wait(page, 800)
    await click(page, page.getByRole('tab', { name: /学习情况/ }), 2500)
    await scrollBy(page, 500, 2500)
    await click(page, page.getByRole('button', { name: '生成家长版' }), 3500)
    await scrollBy(page, 700, 3500)
    await scrollTop(page); await wait(page, 600)
    await click(page, page.getByRole('tab', { name: /对话记录/ }), 3500)
    await scrollBy(page, 300, 2500)
    await rec.stop()
  },
}

// ── 主程序 ─────────────────────────────────────────────────────────
async function ensureNewbie() {
  const r = await fetch(`${API}/auth/register/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'star_newbie', password: PW, password2: PW }),
  })
  if (!r.ok && r.status !== 400) console.warn('register', r.status, await r.text())
}

const ORDER = ['onboard', 'profile', 'steps', 'chat', 'level', 'recommend', 'report']
const wanted = process.argv.slice(2).length ? process.argv.slice(2) : ORDER
await ensureNewbie()
const ids = await learnerIds()
const browser = await chromium.launch()
for (const name of wanted) {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DSF, locale: 'zh-CN' })
  await ctx.addInitScript(INIT)
  const page = await ctx.newPage()
  try {
    await SCENES[name](page, ids)
  } catch (e) {
    console.error(`✗ ${name}:`, e.message.split('\n')[0])
    await page.screenshot({ path: path.join(CLIPS, `${name}-error.png`) })
  }
  await ctx.close()
}
await browser.close()
