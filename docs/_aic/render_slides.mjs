import { pathToFileURL } from 'node:url'
import path from 'node:path'
import { chromium } from './lib.mjs'
const HERE = path.dirname(new URL(import.meta.url).pathname).replace(/^\/(\w:)/, '$1')
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } })
await p.goto(pathToFileURL(path.join(HERE, 'slides.html')).href)
await p.waitForTimeout(500)
for (const id of ['title', 'problem', 'arch', 'results', 'end'])
  await p.locator('#' + id).screenshot({ path: path.join(HERE, 'slides', id + '.png') })
await b.close()
