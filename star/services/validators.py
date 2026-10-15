"""
确定性校验器：大模型负责生成，这里负责把关。

    check_level(content)                  启蒙层关卡（含 BFS 可解性检查）
    check_steps(content, reference_lines) 入门层分步任务
    check_profile(data)                   P1 画像
    check_reply(data)                     P3 对话回复

每个校验分两级：
    format_errors  结构问题（缺字段、类型不对）——格式不合格就不再往下查规则
    rule_errors    规则问题（句长、步骤数、答案唯一、代码行来源、关卡可解……）

错误信息写成可以直接回填给大模型的中文句子：说清哪里错、应该改成什么样。
参考解能否通过测试数据（评测机验证）由 adapt.py 另行检查，不在这里跑代码。
"""
import re
from collections import Counter
from dataclasses import dataclass, field

from . import maze

SENTENCE_MAX = 20           # 单句不超过 20 字
TITLE_MAX = 12
STEPS_MIN, STEPS_MAX = 3, 6
KNOWLEDGE = {'sequence': '顺序', 'loop': '循环', 'condition': '条件'}
LEVEL_KNOWLEDGE = ('sequence', 'loop')      # 条件类关卡为选做，初版不支持
STEP_TYPES = ('choice', 'order', 'fill')
BLANK = '____'
GRID_MIN, GRID_MAX = 3, 8
SLOTS_MAX = 10
OPTION_MAX = 30
LAYERS = ('enlighten', 'intro')
PREFER = ('image', 'text', 'both')
INTENTS = {
    'ask_hint': '想要提示',
    'not_understand': '没听懂',
    'repeat': '再说一遍',
    'done': '做完了',
    'rest': '想休息',
    'chat': '聊兴趣',
    'help': '需要老师',
    'echo': '仿说',
    'other': '其他',
}
REPLY_MAX = 30
REPLY_OPTION_MAX = 8


@dataclass
class Check:
    format_errors: list = field(default_factory=list)
    rule_errors: list = field(default_factory=list)

    @property
    def format_ok(self):
        return not self.format_errors

    @property
    def ok(self):
        return not self.format_errors and not self.rule_errors

    @property
    def errors(self):
        return self.format_errors + self.rule_errors

    def as_dict(self):
        return {
            'format_ok': self.format_ok,
            'rules_ok': self.ok,
            'errors': self.errors,
        }


# ── 句子与长度 ──────────────────────────────────────────────────────

_INLINE_CODE = re.compile(r'`[^`]*`')
_SENT_SPLIT = re.compile(r'[。！？!?；;\n]+')
_NOT_COUNTED = re.compile(r'[\s，,、：:“”"‘’\'（）()《》<>【】\[\]…—\-·。！？!?；;]+')


def sentences(text):
    """按句号、问号、感叹号、分号、换行切句。行内代码 `x` 记作一个词，{name} 按两个字算。"""
    t = _INLINE_CODE.sub('代码', text or '').replace('{name}', '名字')
    return [s.strip() for s in _SENT_SPLIT.split(t) if s.strip()]


def char_len(text):
    """计字数：不算空白和标点。"""
    return len(_NOT_COUNTED.sub('', text or ''))


def avg_sentence_len(texts):
    """平均句长（字），用于测试报告里"改写前后平均句长"的对比。"""
    lens = [char_len(s) for t in texts for s in sentences(t)]
    return round(sum(lens) / len(lens), 1) if lens else 0.0


def _sentence_rule(errs, where, text):
    for s in sentences(text):
        n = char_len(s)
        if n > SENTENCE_MAX:
            errs.append(f'{where}中的句子"{s}"有 {n} 个字，超过 {SENTENCE_MAX} 字，请拆成更短的句子')


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _squash(s):
    return re.sub(r'\s+', '', s or '')


# ── 启蒙层：关卡 ────────────────────────────────────────────────────

def check_level(c):
    chk = Check()
    f = chk.format_errors
    if not isinstance(c, dict):
        f.append('输出必须是一个 JSON 对象')
        return chk

    spec = [
        ('title', str, '标题，字符串'),
        ('story', list, '故事，1 到 3 个短句组成的字符串列表'),
        ('theme', dict, '主题 {"name", "hero", "goal", "wall"}'),
        ('grid', dict, '网格 {"w": 宽, "h": 高}'),
        ('start', dict, '起点 {"x", "y", "dir"}'),
        ('goal', dict, '终点 {"x", "y"}'),
        ('walls', list, '障碍坐标列表 [[x, y], ...]'),
        ('cards', list, '可用卡片列表'),
        ('slots', int, '卡槽数，整数'),
        ('knowledge', str, '知识点 sequence 或 loop'),
    ]
    for key, typ, label in spec:
        if not isinstance(c.get(key), typ) or (typ is int and isinstance(c.get(key), bool)):
            f.append(f'缺少字段 {key}（{label}）或类型不对')
    if f:
        return chk

    grid, start, goal = c['grid'], c['start'], c['goal']
    if not (_is_int(grid.get('w')) and _is_int(grid.get('h'))):
        f.append('grid 的 w、h 必须是整数')
    if not (_is_int(start.get('x')) and _is_int(start.get('y'))) or start.get('dir') not in maze.DIRS:
        f.append('start 必须是 {"x": 整数, "y": 整数, "dir": "N"/"E"/"S"/"W"}')
    if not (_is_int(goal.get('x')) and _is_int(goal.get('y'))):
        f.append('goal 必须是 {"x": 整数, "y": 整数}')
    if not all(isinstance(p, list) and len(p) == 2 and all(_is_int(v) for v in p) for p in c['walls']):
        f.append('walls 的每一项必须是 [x, y] 两个整数')
    bad_cards = [x for x in c['cards'] if x not in maze.CARD_TYPES]
    if bad_cards:
        f.append(f'cards 只能取 forward / left / right / repeat，出现了 {bad_cards}')
    if not all(isinstance(s, str) for s in c['story']):
        f.append('story 的每一项必须是字符串')
    if not all(isinstance(c['theme'].get(k), str) for k in ('name', 'hero', 'goal', 'wall')):
        f.append('theme 必须包含 name、hero、goal、wall 四个字符串')
    if f:
        return chk

    r = chk.rule_errors
    w, h = grid['w'], grid['h']
    if not (GRID_MIN <= w <= GRID_MAX and GRID_MIN <= h <= GRID_MAX):
        r.append(f'网格大小应在 {GRID_MIN}×{GRID_MIN} 到 {GRID_MAX}×{GRID_MAX} 之间，现在是 {w}×{h}')
        return chk

    def inside(x, y):
        return 0 <= x < w and 0 <= y < h

    walls = {tuple(p) for p in c['walls']}
    if not inside(start['x'], start['y']):
        r.append('起点在地图外')
    if not inside(goal['x'], goal['y']):
        r.append('终点在地图外')
    if (start['x'], start['y']) == (goal['x'], goal['y']):
        r.append('起点和终点不能是同一格')
    if any(not inside(x, y) for x, y in walls):
        r.append('有障碍在地图外')
    if (start['x'], start['y']) in walls or (goal['x'], goal['y']) in walls:
        r.append('起点或终点上不能放障碍')
    if len(walls) > w * h // 2:
        r.append('障碍太多，不能超过格子总数的一半')

    cards, knowledge, slots = c['cards'], c['knowledge'], c['slots']
    if 'forward' not in cards:
        r.append('可用卡片里必须有"前进"（forward）')
    if knowledge not in LEVEL_KNOWLEDGE:
        r.append('knowledge 只能是 sequence（顺序）或 loop（循环）')
    elif knowledge == 'sequence' and 'repeat' in cards:
        r.append('顺序关卡不提供"重复"卡，请从 cards 中去掉 repeat')
    elif knowledge == 'loop' and 'repeat' not in cards:
        r.append('循环关卡必须提供"重复"卡，请在 cards 中加入 repeat')
    if not 1 <= slots <= SLOTS_MAX:
        r.append(f'卡槽数应在 1 到 {SLOTS_MAX} 之间')

    if char_len(c['title']) > TITLE_MAX:
        r.append(f'标题"{c["title"]}"超过 {TITLE_MAX} 个字')
    if not 1 <= len(c['story']) <= 3:
        r.append('story 应为 1 到 3 个短句')
    for i, s in enumerate(c['story'], 1):
        _sentence_rule(r, f'故事第 {i} 句', s)
    if char_len(c['theme']['name']) > 6:
        r.append('主题名不超过 6 个字')
    for k in ('hero', 'goal', 'wall'):
        v = c['theme'][k].strip()
        if not 1 <= len(v) <= 4 or re.search(r'[A-Za-z0-9一-鿿]', v):
            r.append(f'theme.{k} 必须是一个 emoji 图标，现在是"{v}"')
    if r:
        return chk          # 地图本身不合法，不必再搜

    sol = maze.shortest_solution(c)
    if sol is None:
        r.append('关卡无解：用现有卡片走不到终点，请调整障碍或终点位置')
        return chk
    n = len(sol)
    if n > slots:
        r.append(f'最少需要 {n} 张卡片，但只有 {slots} 个卡槽；请把卡槽数改为 {n} 到 {n + 2} 之间，或缩短路线')
    elif slots > n + 2:
        r.append(f'卡槽太多：最少 {n} 张卡片就能到终点，卡槽数应在 {n} 到 {n + 2} 之间')
    if knowledge == 'loop':
        if not maze.uses_repeat(sol):
            r.append('循环关卡的最短走法没有用到"重复"卡：请把直线路段加长到连续 3 格以上')
        else:
            plain = maze.shortest_solution(dict(c, cards=[x for x in cards if x != 'repeat']))
            if plain is not None and len(plain) <= slots:
                r.append(f'不用"重复"卡也能在 {slots} 个卡槽内完成，练不到循环：'
                         f'请把卡槽数减到 {n} 到 {len(plain) - 1} 之间，或加长直线路段')
    return chk


# ── 入门层：分步任务 ────────────────────────────────────────────────

def reference_lines(code):
    """参考解的非空代码行：保留缩进，去掉行尾空白。"""
    return [line.rstrip() for line in (code or '').splitlines() if line.strip()]


def normalize_blank(code):
    return re.sub(r'_{3,}', BLANK, code or '')


def check_steps(c, ref_lines):
    chk = Check()
    f = chk.format_errors
    if not isinstance(c, dict):
        f.append('输出必须是一个 JSON 对象')
        return chk
    if not isinstance(c.get('title'), str) or not c['title'].strip():
        f.append('缺少字段 title（标题，字符串）')
    if not isinstance(c.get('intro'), list) or not all(isinstance(s, str) for s in c['intro']):
        f.append('缺少字段 intro（开场说明，1 到 3 个短句组成的字符串列表）')
    steps = c.get('steps')
    if not isinstance(steps, list) or not steps:
        f.append('缺少字段 steps（步骤列表）')
        return chk

    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict):
            f.append(f'第 {i} 步必须是 JSON 对象')
            continue
        t = st.get('type')
        if t not in STEP_TYPES:
            f.append(f'第 {i} 步的 type 只能是 choice / order / fill，现在是 {t!r}')
            continue
        if not isinstance(st.get('prompt'), str) or not st['prompt'].strip():
            f.append(f'第 {i} 步缺少 prompt（题干）')
        hints = st.get('hints')
        if not (isinstance(hints, list) and len(hints) == 3
                and all(isinstance(x, str) and x.strip() for x in hints)):
            f.append(f'第 {i} 步的 hints 必须恰好是 3 条非空字符串（由少到多的三级提示）')
        if st.get('knowledge') not in KNOWLEDGE:
            f.append(f'第 {i} 步的 knowledge 只能是 sequence / loop / condition')
        if t == 'choice':
            opts = st.get('options')
            if not (isinstance(opts, list) and all(isinstance(o, str) for o in opts)):
                f.append(f'第 {i} 步（选择题）缺少 options（字符串列表）')
            if not _is_int(st.get('answer')):
                f.append(f'第 {i} 步（选择题）的 answer 必须是正确选项的下标（整数，从 0 开始）')
        elif t == 'order':
            lines = st.get('lines')
            if not (isinstance(lines, list) and all(isinstance(x, str) for x in lines)):
                f.append(f'第 {i} 步（排序题）缺少 lines（代码行列表）')
        elif t == 'fill':
            if not isinstance(st.get('code'), str):
                f.append(f'第 {i} 步（填空题）缺少 code（带 ____ 的一行代码）')
            if not isinstance(st.get('answer'), str):
                f.append(f'第 {i} 步（填空题）的 answer 必须是字符串')
    if f:
        return chk

    r = chk.rule_errors
    if char_len(c['title']) > TITLE_MAX:
        r.append(f'标题"{c["title"]}"超过 {TITLE_MAX} 个字')
    if not 1 <= len(c['intro']) <= 3:
        r.append('intro 应为 1 到 3 个短句')
    for k, s in enumerate(c['intro'], 1):
        _sentence_rule(r, f'开场说明第 {k} 句', s)

    n = len(steps)
    if not STEPS_MIN <= n <= STEPS_MAX:
        r.append(f'现在有 {n} 个步骤，应为 {STEPS_MIN} 到 {STEPS_MAX} 步')
    order_at = [i for i, st in enumerate(steps) if st['type'] == 'order']
    if len(order_at) != 1 or order_at[0] != n - 1:
        r.append('必须恰好有一个排序步骤（type 为 order），并且放在最后一步')

    ref = Counter(ref_lines)
    ref_squashed = {_squash(x) for x in ref_lines}
    for i, st in enumerate(steps, 1):
        _sentence_rule(r, f'第 {i} 步的题干', st['prompt'])
        for k, hint in enumerate(st['hints'], 1):
            _sentence_rule(r, f'第 {i} 步的第 {k} 条提示', hint)

        if st['type'] == 'choice':
            opts = st['options']
            if not 2 <= len(opts) <= 4:
                r.append(f'第 {i} 步（选择题）应有 2 到 4 个选项，现在有 {len(opts)} 个')
            if any(not o.strip() for o in opts):
                r.append(f'第 {i} 步（选择题）有空选项')
            squashed = [_squash(o).lower() for o in opts]
            if len(set(squashed)) != len(squashed):
                r.append(f'第 {i} 步（选择题）有重复的选项，正确答案必须唯一')
            if any(len(o) > OPTION_MAX for o in opts):
                r.append(f'第 {i} 步（选择题）的选项不超过 {OPTION_MAX} 个字符')
            if not 0 <= st['answer'] < len(opts):
                r.append(f'第 {i} 步（选择题）的 answer 下标超出选项范围')

        elif st['type'] == 'order':
            got = Counter(x.rstrip() for x in st['lines'] if x.strip())
            if got != ref:
                msg = f'第 {i} 步（排序题）的 lines 必须逐字复制参考解的全部代码行（保留缩进，不增不减）'
                extra, missing = got - ref, ref - got
                if extra:
                    msg += f'；多出或改动了：{list(extra)}'
                if missing:
                    msg += f'；缺少：{list(missing)}'
                r.append(msg)

        elif st['type'] == 'fill':
            code = normalize_blank(st['code'])
            ans = st['answer'].strip()
            if code.count(BLANK) != 1:
                r.append(f'第 {i} 步（填空题）的 code 中必须恰好有一个 ____（四个下划线）')
            elif not ans or len(ans) > 20:
                r.append(f'第 {i} 步（填空题）的 answer 不能为空，且不超过 20 个字符')
            elif _squash(code.replace(BLANK, ans)) not in ref_squashed:
                r.append(f'第 {i} 步（填空题）把 answer 填回 ____ 后，应与参考解中的某一行完全一致；'
                         f'现在得到"{code.replace(BLANK, ans).strip()}"')
    return chk


# ── P1：画像 ────────────────────────────────────────────────────────

def check_profile(d):
    chk = Check()
    f = chk.format_errors
    if not isinstance(d, dict):
        f.append('输出必须是一个 JSON 对象')
        return chk
    if d.get('layer') not in LAYERS:
        f.append('layer 只能是 enlighten（启蒙层）或 intro（入门层）')
    if not isinstance(d.get('interests'), list) or not all(isinstance(x, str) for x in d['interests']):
        f.append('interests 必须是字符串列表')
    if not isinstance(d.get('presentation'), dict) or d['presentation'].get('prefer') not in PREFER:
        f.append('presentation.prefer 只能是 image / text / both')
    comm = d.get('communication')
    if not isinstance(comm, dict) or not all(isinstance(comm.get(k), bool)
                                             for k in ('pronoun_reversal', 'echolalia')):
        f.append('communication 必须包含布尔值 pronoun_reversal 和 echolalia')
    vocab = d.get('vocabulary')
    if not isinstance(vocab, list) or not all(
            isinstance(v, dict) and isinstance(v.get('word'), str) and isinstance(v.get('meaning'), str)
            for v in vocab):
        f.append('vocabulary 必须是 [{"word": 学生的说法, "meaning": 标准说法}] 列表')
    if f:
        return chk

    r = chk.rule_errors
    if not 1 <= len(d['interests']) <= 3:
        r.append('interests 应有 1 到 3 项')
    if any(char_len(x) > 8 for x in d['interests']):
        r.append('每项兴趣不超过 8 个字')
    if len(d['vocabulary']) > 20:
        r.append('个人词表不超过 20 条')
    for v in d['vocabulary']:
        if not v['word'].strip() or not v['meaning'].strip() or len(v['word']) > 10 or len(v['meaning']) > 10:
            r.append(f'词表条目 {v} 的 word、meaning 都不能为空且不超过 10 个字')
    return chk


# ── P3：对话回复 ────────────────────────────────────────────────────

def check_reply(d):
    chk = Check()
    f = chk.format_errors
    if not isinstance(d, dict):
        f.append('输出必须是一个 JSON 对象')
        return chk
    if d.get('intent') not in INTENTS:
        f.append(f'intent 只能取 {list(INTENTS)}')
    if not isinstance(d.get('reply'), str) or not d['reply'].strip():
        f.append('缺少 reply（一句话回复）')
    opts = d.get('options')
    if not isinstance(opts, list) or not all(isinstance(o, str) for o in opts):
        f.append('options 必须是字符串列表')
    if f:
        return chk

    r = chk.rule_errors
    if char_len(d['reply']) > REPLY_MAX or len(sentences(d['reply'])) > 2:
        r.append(f'reply 只能是一句话，不超过 {REPLY_MAX} 个字')
    if not 2 <= len(opts) <= 4:
        r.append('options 应有 2 到 4 个')
    if any(not o.strip() or char_len(o) > REPLY_OPTION_MAX for o in opts):
        r.append(f'每个选项不能为空且不超过 {REPLY_OPTION_MAX} 个字')
    if len({o.strip() for o in opts}) != len(opts):
        r.append('options 不能重复')
    return chk
