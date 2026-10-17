// 方案书配图：高分辨率截图（在录屏之后运行，复用录屏留下的作答与对话数据）
import fs from 'node:fs'
import path from 'node:path'
import { chromium, loginAs, apiGet, tokens, BASE } from './lib.mjs'

const HERE = path.dirname(new URL(import.meta.url).pathname).replace(/^\/(\w:)/, '$1')
const OUT = path.join(HERE, 'docshots'); fs.mkdirSync(OUT, { recursive: true })
const HIDE = '#__vue-devtools-container__, [id^="__vue-devtools"] { display:none !important }'

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5, locale: 'zh-CN' })
await ctx.addInitScript(`document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = ${JSON.stringify(HIDE)}; document.head.appendChild(s) })`)
const page = await ctx.newPage()
const wait = (ms) => page.waitForTimeout(ms)
const shot = async (name, opts = {}) => {
  await wait(900)
  const target = opts.el ? page.locator(opts.el).first() : page
  await target.screenshot({ path: path.join(OUT, `${name}.jpg`), type: 'jpeg', quality: 86, ...(opts.clip ? { clip: opts.clip } : {}) })
  console.log('✓', name)
}
const t = await tokens('star_teacher')
const ids = Object.fromEntries((await apiGet('/star/teacher/learners/', t.access)).learners.map((r) => [r.username, r.user_id]))

// 1 问卷（新学生）
await loginAs(page, 'star_newbie')
await page.goto(`${BASE}/star/start`); await wait(1500)
for (let i = 0; i < 3; i++) { const b = page.getByRole('button', { name: /上一题/ }); if (await b.count()) await b.click(); await wait(300) }
await shot('01_survey', { clip: { x: 170, y: 0, width: 1060, height: 640 } })

// 2 画像
await loginAs(page, 'star_teacher')
await page.goto(`${BASE}/star/teacher/learners/${ids.star_yu}`); await wait(1500)
await page.evaluate(() => window.scrollTo(0, 290)); await shot('02_profile')

// 3 推荐
await page.getByRole('tab', { name: /任务/ }).click(); await wait(800)
await page.getByRole('button', { name: /生成推荐|重新推荐/ }).click(); await wait(2500)
await shot('03_recommend', { el: 'section.st-card >> nth=0' })

// 4 审核页
await page.getByRole('row', { name: /奇数还是偶数/ }).getByRole('link', { name: '查看' }).click(); await wait(2000)
await shot('04_review')

// 5 学习情况
await page.goto(`${BASE}/star/teacher/learners/${ids.star_yu}`); await wait(1500)
await page.getByRole('tab', { name: /学习情况/ }).click(); await wait(1500)
await page.evaluate(() => window.scrollTo(0, 240)); await shot('05_learning')
await page.getByRole('button', { name: '生成家长版' }).click(); await wait(2500)
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await shot('06_report')

// 6 对话记录
await page.evaluate(() => window.scrollTo(0, 0)); await wait(300)
await page.getByRole('tab', { name: /对话记录/ }).click(); await wait(1500)
await page.evaluate(() => window.scrollTo(0, 240)); await shot('07_dialogue')

// 7 学生端：带提示的步骤 + 学伴
await loginAs(page, 'star_yu')
await page.goto(`${BASE}/star`); await wait(1500)
await page.locator('a.s-btn').nth(2).click(); await wait(1500)
await page.getByRole('button', { name: /开始第 1 步/ }).click(); await wait(800)
await page.getByRole('button', { name: /提示/ }).click(); await wait(1000)
await page.getByRole('button', { name: /提示/ }).click(); await wait(1000)
await shot('08_step_hint')
await page.getByRole('button', { name: /问学伴/ }).click(); await wait(800)
await page.locator('.a-input').fill('你不懂'); await page.getByRole('button', { name: '发送' }).click(); await wait(2500)
await shot('09_chat')

// 8 启蒙层
await loginAs(page, 'star_hang')
await page.goto(`${BASE}/star`); await wait(1500)
await page.locator('a.s-btn').nth(1).click(); await wait(1500)
await shot('10_level')

// 9 学生任务列表（深色）
await loginAs(page, 'star_yu')
await page.goto(`${BASE}/star`); await wait(1500)
await shot('11_home_dark', { clip: { x: 200, y: 0, width: 1040, height: 560 } })
await browser.close()
