import { createRequire } from 'node:module'
const require = createRequire(new URL('../../frontend/package.json', import.meta.url))
const pw = require('playwright')
export const EXE = process.env.CHROME_PATH || 'C:/Users/35659/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe'
export const chromium = { launch: (o = {}) => pw.chromium.launch({ executablePath: EXE, ...o }) }

export const BASE = 'http://localhost:5173'
export const API = 'http://127.0.0.1:8000/api'
export const PW = 'StarDemo2026'

export async function tokens(username, password = PW) {
  const r = await fetch(`${API}/auth/login/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) throw new Error(`login ${username}: ${r.status} ${await r.text()}`)
  return r.json()
}

export async function apiGet(path, access) {
  const r = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${access}` } })
  return r.json()
}

// 以某个账号身份打开页面：先写 localStorage 再跳转
export async function loginAs(page, username, password = PW) {
  const t = await tokens(username, password)
  await page.goto(`${BASE}/login`)
  await page.evaluate(([a, r]) => {
    localStorage.setItem('access_token', a)
    localStorage.setItem('refresh_token', r)
  }, [t.access, t.refresh])
  return t
}

// 隐藏 Vue DevTools 悬浮条
export const HIDE_CSS = `#__vue-devtools-container__, .vue-devtools__anchor, [id^="__vue-devtools"] { display: none !important; }`
