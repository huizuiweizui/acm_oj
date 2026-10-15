// 前后端规则一致性检查：用 star/tests/maze_cases.json 里的用例跑前端 maze.js，
// 结果必须与后端 star/services/maze.py 生成的期望完全相同。
//   node frontend/scripts/check-maze.mjs
// Django 测试（star.tests.test_maze.JsParityTests）也会调用它。
import { readFileSync } from 'node:fs'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { simulate } from '../src/components/star/maze.js'

const casesPath = fileURLToPath(new URL('../../star/tests/maze_cases.json', import.meta.url))
const cases = JSON.parse(readFileSync(casesPath, 'utf8'))

let failed = 0
for (const c of cases) {
  const r = simulate(c.level, c.program)
  const last = r.frames[r.frames.length - 1]
  const got = {
    result: r.result,
    final: { x: last.x, y: last.y, dir: last.dir },
    cards: r.frames.map((f) => f.card),
  }
  const want = { result: c.result, final: c.final, cards: c.cards }
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    failed += 1
    console.error(`✗ ${c.name}\n  want ${JSON.stringify(want)}\n  got  ${JSON.stringify(got)}`)
  }
}
console.log(`${cases.length - failed}/${cases.length} cases match`)
process.exit(failed ? 1 : 0)
