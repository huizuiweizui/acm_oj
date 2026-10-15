// 指令卡片闯关的规则 —— star/services/maze.py 的逐行翻译，两边必须一致。
// 前端用它播放动画，后端用同一套规则判定；star/tests/maze_cases.json 是两边共用的用例。
//
// 坐标：x 向右、y 向下，(0, 0) 在左上角。朝向 N / E / S / W。
// 卡片：forward 前进一格；left / right 原地转向；
//       repeat 重复 N 次（2–5），只作用于紧跟其后的那一张基础卡片，后面没有基础卡片时不起作用。
// 结果：arrived 踏上终点即成功并停止；wall 撞墙；out 出界；not_reached 卡片用完还没到。

export const DIRS = ['N', 'E', 'S', 'W']
const DELTA = { N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0] }
export const BASIC = ['forward', 'left', 'right']
export const REPEAT_MIN = 2
export const REPEAT_MAX = 5
const MAX_ACTIONS = 200

function turn(d, kind) {
  const i = DIRS.indexOf(d)
  return kind === 'left' ? DIRS[(i + 3) % 4] : DIRS[(i + 1) % 4]
}

export function clampTimes(times) {
  const n = Number.parseInt(times, 10)
  if (Number.isNaN(n)) return REPEAT_MIN
  return Math.max(REPEAT_MIN, Math.min(REPEAT_MAX, n))
}

export function simulate(level, program) {
  const w = level.grid.w
  const h = level.grid.h
  const walls = new Set((level.walls || []).map(([x, y]) => `${x},${y}`))
  const goal = `${level.goal.x},${level.goal.y}`
  let x = level.start.x
  let y = level.start.y
  let d = level.start.dir
  const frames = [{ x, y, dir: d, card: -1, rep: 0 }]
  let actions = 0

  function act(kind, idx, rep) {
    if (kind === 'left' || kind === 'right') {
      d = turn(d, kind)
    } else {
      const [dx, dy] = DELTA[d]
      const nx = x + dx
      const ny = y + dy
      if (!(nx >= 0 && nx < w && ny >= 0 && ny < h)) {
        frames.push({ x, y, dir: d, card: idx, rep })
        return 'out'
      }
      if (walls.has(`${nx},${ny}`)) {
        frames.push({ x, y, dir: d, card: idx, rep })
        return 'wall'
      }
      x = nx
      y = ny
    }
    frames.push({ x, y, dir: d, card: idx, rep })
    return `${x},${y}` === goal ? 'arrived' : null
  }

  const finish = (result) => ({ result, frames, cards_used: program.length })

  let i = 0
  while (i < program.length) {
    const kind = program[i]?.type
    if (kind === 'repeat') {
      const nxt = i + 1 < program.length ? program[i + 1] : null
      if (nxt && BASIC.includes(nxt.type)) {
        const times = clampTimes(program[i].times)
        for (let rep = 1; rep <= times; rep++) {
          actions += 1
          if (actions > MAX_ACTIONS) return finish('not_reached')
          const r = act(nxt.type, i + 1, rep)
          if (r) return finish(r)
        }
        i += 2
        continue
      }
      i += 1
      continue
    }
    if (BASIC.includes(kind)) {
      actions += 1
      if (actions > MAX_ACTIONS) return finish('not_reached')
      const r = act(kind, i, 0)
      if (r) return finish(r)
    }
    i += 1
  }
  return finish('not_reached')
}

// 学生当前卡槽与示范解第一处不同的位置（提示第 1 级"高亮下一张卡片"用）
export function firstDiff(program, solution) {
  const n = Math.min(program.length, solution.length)
  for (let i = 0; i < n; i++) {
    const a = program[i]
    const b = solution[i]
    if (a.type !== b.type) return i
    if (a.type === 'repeat' && clampTimes(a.times) !== clampTimes(b.times)) return i
  }
  return n < solution.length ? n : -1
}
