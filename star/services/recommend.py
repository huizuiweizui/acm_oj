"""
推荐下一项任务（教师端学生详情页）。两条分支：

    规则分支  1. 掌握度：每个知识点一个 0–1 的分数。每一步按"提示等级 × 做对前错了几次"打分，
                 越近的步骤权重越大（提示渐褪之后，早期吃力的记录不再一直拖后腿），做了没做对的步骤记 0 分。
                 有记录但分数 < MASTER_SCORE = 薄弱；分数够但做对不满 MASTER_STEPS 步 = 学习中；
                 两样都够 = 掌握；没有记录 = 未学。
              2. 目标：按知识点顺序（顺序 → 条件 → 循环）找第一类没掌握的知识点。
              3. 排序：候选素材分组——目标类 → 下一类预习 → 已掌握类复习；素材各步用到的知识点里
                 有还没学到或薄弱的（例如"偶数之和"要用到条件），算前置不足，放到最后。
                 组内按难度（用到几类知识点、几步）从易到难，难度相同保持素材库顺序。
              4. 配额：目标类"学习中"（做对的步骤表现不错、只是还不够多）时目标类 2 项、留 1 项预习下一类；
                 未学或薄弱时 3 项都给目标类，保持同一类反复练；
                 全部掌握后先推综合题（用到多类知识点的），再复习掌握度最低的一类。
              5. 有已布置却没做完的任务时，在总结里提醒教师。
    大模型分支（P6）把画像、作答统计、各知识点掌握度、候选素材和规则分支的结果一起交给大模型，
             由它从候选里挑 1–3 项并写理由；输出经程序校验（只能选候选里的、不重复、理由不超长），
             不合格回填错误改一次，仍不合格或没配大模型时用规则分支的结果。

两条分支的结果都返回给前端：主推荐是大模型的，规则的作为对照展示；掌握度也一起返回。
"""
from ..content.levels import LEVELS
from ..content.problems import PROBLEMS
from ..models import AdaptedTask
from . import llm, prompts
from .report import learner_stats
from .validators import KNOWLEDGE, Check

ORDER = {'intro': ('sequence', 'condition', 'loop'), 'enlighten': ('sequence', 'loop')}
MASTER_STEPS = 3
MASTER_HINT = 1.0
MASTER_SCORE = 1 - MASTER_HINT / 3      # 每步第一次就做对、只看到一级提示时的分数
RETRY_DECAY = 0.75                      # 做对前每多错一次，这一步的分数乘一次
RETRY_FLOOR = 0.25
RECENCY = 0.8                           # 从最近一步往前，每早一步权重乘一次
TOP_N = 3
REASON_MAX = 60
MODES = ('llm', 'template')
STATUS_TEXT = {'new': '未学', 'learning': '学习中', 'weak': '薄弱', 'mastered': '已掌握'}
PRE_LACK = 9                            # 前置不足的分组号，排在最后


def _material_knowledge(p):
    """素材各步实际用到的知识点（没有默认步骤时只算主知识点）。"""
    steps = (p.get('default_steps') or {}).get('steps') or []
    return {s['knowledge'] for s in steps if s.get('knowledge')} | {p['knowledge']}


def candidates(lp):
    """学生所在层级里还没布置过的素材（生成失败的不算布置过），保持素材库顺序。"""
    have = set(AdaptedTask.objects.filter(student=lp.user).exclude(status='failed')
               .values_list('template', flat=True))
    if lp.layer == 'enlighten':
        rows = [{'key': lv['key'], 'title': lv['title'], 'knowledge': lv['knowledge'], 'has_default': True,
                 'needs': [lv['knowledge']], 'size': 0} for lv in LEVELS]
    else:
        rows = [{'key': p['slug'], 'title': p['title'], 'knowledge': p['knowledge'],
                 'has_default': bool(p.get('default_steps')), 'needs': sorted(_material_knowledge(p)),
                 'size': len((p.get('default_steps') or {}).get('steps') or [])} for p in PROBLEMS]
    return [r for r in rows if r['key'] not in have]


def _item(c, reason, mode):
    return {'material': c['key'], 'title': c['title'], 'knowledge': c['knowledge'],
            'knowledge_name': KNOWLEDGE.get(c['knowledge'], c['knowledge']),
            'has_default': c['has_default'], 'reason': reason, 'mode': mode}


def _step_score(s):
    if not s['done']:
        return 0.0
    retry = max(RETRY_FLOOR, RETRY_DECAY ** max(0, s['attempts'] - 1))
    return (1 - (s['hint_level'] or 0) / 3) * retry


def mastery(stats, order):
    """
    每个知识点的掌握情况 {k: {'name', 'status', 'status_text', 'score', 'solved', 'tried', 'avg_hint'}}。
    tried 是有作答记录的步骤数（含没做对的），score 是按时间加权的平均步骤分（没有记录为 None）。
    """
    steps = [s for t in stats['tasks'] for s in t['steps'] if s['knowledge'] and s['attempts']]
    steps.sort(key=lambda s: (not s['done'], s['done_at'] or ''))     # 没做对的算最近（正卡着）
    by_hint = stats['summary'].get('by_knowledge') or {}
    out = {}
    for k in order:
        mine = [s for s in steps if s['knowledge'] == k]
        solved = sum(1 for s in mine if s['done'])
        score = None
        if mine:
            weights = [RECENCY ** (len(mine) - 1 - i) for i in range(len(mine))]
            score = round(sum(w * _step_score(s) for w, s in zip(weights, mine)) / sum(weights), 2)
        if not mine:
            status = 'new'
        elif score + 1e-9 < MASTER_SCORE:
            status = 'weak'
        elif solved < MASTER_STEPS:
            status = 'learning'
        else:
            status = 'mastered'
        out[k] = {'name': KNOWLEDGE[k], 'status': status, 'status_text': STATUS_TEXT[status], 'score': score,
                  'solved': solved, 'tried': len(mine), 'avg_hint': (by_hint.get(k) or {}).get('avg_hint')}
    return out


def _weak_why(name, m):
    if m['avg_hint'] is not None and m['avg_hint'] > MASTER_HINT:
        return f'{name}类做对时平均提示等级 {m["avg_hint"]}，再练同类题巩固'
    if m['solved'] < m['tried']:
        return f'{name}类有 {m["tried"] - m["solved"]} 步还没做对，换一道同类题再练'
    return f'{name}类做对前错的次数较多（掌握度 {m["score"]}），再练同类题巩固'


def rule_recommend(lp, stats, cands, m=None):
    """规则推荐，返回 (items, summary_text)。"""
    order = ORDER.get(lp.layer, ORDER['intro'])
    m = m or mastery(stats, order)
    pos = {k: i for i, k in enumerate(order)}
    target = next((k for k in order if m[k]['status'] != 'mastered'), None)
    weak = target is not None and m[target]['status'] == 'weak'
    nxt = order[pos[target] + 1] if target and pos[target] + 1 < len(order) else None

    if target is None:
        review = min(order, key=lambda k: m[k]['score'])
        why = '各类都已掌握，做一道用到多类知识点的综合题'
        text = f'{"、".join(KNOWLEDGE[k] for k in order)}都已掌握，先做综合题，再复习掌握度最低的{KNOWLEDGE[review]}。'
    else:
        name, t = KNOWLEDGE[target], m[target]
        if t['status'] == 'new':
            prev = order[pos[target] - 1] if pos[target] else None
            why = (f'{KNOWLEDGE[prev]}已掌握，进入{name}' if prev and m[prev]['tried']
                   else f'还没有{name}类的作答记录，从{name}开始')
            text = f'按"{"→".join(KNOWLEDGE[k] for k in order)}"的学习路线，{why}。'
        elif weak:
            why = _weak_why(name, t)
            text = f'{name}类还要靠提示或多次尝试才能完成（掌握度 {t["score"]}），先巩固{name}。'
        else:
            why = f'{name}类只做对了 {t["solved"]} 步，再多练几道'
            text = f'{name}类练得还不多，继续练{name}。'

    def lacking(c):
        """素材用到、但还没学到（在目标之后或没做过）或薄弱的知识点。"""
        if target is None:
            return []
        return [k for k in c['needs'] if k != target and k in m
                and (pos[k] > pos[target] or not m[k]['tried'] or m[k]['status'] == 'weak')]

    def group(c):
        if target is None:
            return 0 if len(c['needs']) > 1 else 1
        if lacking(c) and c['knowledge'] != nxt:
            return PRE_LACK
        if c['knowledge'] == target:
            return 0
        if c['knowledge'] == nxt:
            return 1 if not lacking(c) or lacking(c) == [nxt] else PRE_LACK
        return 2

    lib = {c['key']: n for n, c in enumerate(cands)}
    ranked = sorted(cands, key=lambda c: (group(c), len(c['needs']), c['size'], lib[c['key']]))
    if target is not None and m[target]['status'] == 'learning':
        head = [c for c in ranked if group(c) == 0][:TOP_N - 1]
        preview = [c for c in ranked if group(c) == 1][:1]
        if preview:
            ranked = head + preview + [c for c in ranked if c not in head and c not in preview]

    items = []
    for c in ranked[:TOP_N]:
        g, k = group(c), c['knowledge']
        if target is None:
            reason = why if g == 0 else f'复习{KNOWLEDGE[k]}（掌握度 {m[k]["score"]}）'
        elif g == 0:
            reason = why
        elif g == 1:
            reason = f'{KNOWLEDGE[target]}之后接着学{KNOWLEDGE[k]}，先预习一道'
        elif g == PRE_LACK:
            reason = f'要用到{"、".join(KNOWLEDGE[x] for x in lacking(c))}，前置还不够，放在后面'
        else:
            reason = f'复习{KNOWLEDGE[k]}（掌握度 {m[k]["score"]}）'
        mode = 'llm' if weak and g == 0 else 'template'
        items.append(_item(c, reason, mode if c['has_default'] else 'llm'))

    pending = sum(1 for t in stats['tasks'] if not t['done'])
    if pending:
        text += f'另有 {pending} 个已布置的任务还没做完，可以先做完。'
    return items, text


def _task_rows(stats):
    """给大模型看的每个任务一行：标题、知识点、是否完成、各步提示等级。"""
    rows = []
    for t in stats['tasks']:
        ks = sorted({s['knowledge'] for s in t['steps'] if s['knowledge']})
        rows.append({'title': t['title'], 'knowledge': [KNOWLEDGE.get(k, k) for k in ks], 'done': t['done'],
                     'hint_levels': [s['hint_level'] for s in t['steps']], 'attempts': t['attempts']})
    return rows


def check(data, cands):
    """校验 P6 输出，返回 (items, summary, errors)。"""
    errors, items = [], []
    if not isinstance(data, dict):
        return [], '', ['输出不是 JSON 对象']
    by_key = {c['key']: c for c in cands}
    raw = data.get('items')
    if not isinstance(raw, list) or not raw:
        errors.append('items 必须是非空数组')
        raw = []
    seen = set()
    for n, it in enumerate(raw[:TOP_N], 1):
        if not isinstance(it, dict):
            errors.append(f'第 {n} 项不是对象')
            continue
        key = str(it.get('material', '')).strip()
        reason = str(it.get('reason', '')).strip()
        mode = it.get('mode') if it.get('mode') in MODES else 'llm'
        if key not in by_key:
            errors.append(f'第 {n} 项的 material "{key}" 不在候选素材里')
            continue
        if key in seen:
            errors.append(f'第 {n} 项的 material "{key}" 重复了')
            continue
        if not reason:
            errors.append(f'第 {n} 项缺少 reason')
            continue
        if len(reason) > REASON_MAX:
            errors.append(f'第 {n} 项的 reason 有 {len(reason)} 字，不能超过 {REASON_MAX} 字')
            continue
        seen.add(key)
        c = by_key[key]
        items.append(_item(c, reason, mode if c['has_default'] else 'llm'))
    if len(raw) > TOP_N:
        errors.append(f'最多推荐 {TOP_N} 项')
    summary = data.get('summary')
    summary = summary.strip() if isinstance(summary, str) else ''
    if not summary:
        errors.append('缺少 summary')
    return items, summary, errors


def recommend(lp):
    """
    返回 {
        'source': 'llm' | 'rule',      主推荐来自哪条分支
        'summary': 一句总体判断,
        'items': 主推荐,
        'rule': {'summary', 'items'},  规则分支的结果（对照）
        'mastery': 各知识点掌握度,
        'note': 大模型没用上时的原因,
    }
    """
    stats = learner_stats(lp.user)
    summary = stats['summary']
    cands = candidates(lp)
    m = mastery(stats, ORDER.get(lp.layer, ORDER['intro']))
    rule_items, rule_text = rule_recommend(lp, stats, cands, m) if cands else ([], '')
    rule = {'summary': llm.fill_name(rule_text, lp.nickname), 'items': rule_items}
    out = {'source': 'rule', 'summary': rule['summary'], 'items': rule_items, 'rule': rule,
           'mastery': m, 'note': ''}
    if not cands:
        out['summary'] = rule['summary'] = '这个层级的素材都已经布置过了。'
        return out
    if not llm.is_configured():
        out['note'] = '未配置大模型，使用规则推荐'
        return out

    names = [lp.user.username, lp.nickname]
    stat = {k: summary[k] for k in ('tasks_total', 'tasks_done', 'steps_solved', 'avg_hint',
                                    'avg_hint_early', 'avg_hint_late', 'by_knowledge')}
    stat['mastery'] = {v['name']: {'status': v['status_text'], 'score': v['score'],
                                   'solved': v['solved'], 'tried': v['tried']} for v in m.values()}
    messages = prompts.p6_messages(
        llm.redact(prompts.profile_summary(lp.profile), names),
        lp.layer,
        stat,
        [dict(r, title=llm.redact(r['title'], names)) for r in _task_rows(stats)],
        [{'material': c['key'], 'title': c['title'], 'knowledge': KNOWLEDGE[c['knowledge']],
          'uses': [KNOWLEDGE[k] for k in c['needs']], 'has_default': c['has_default']} for c in cands],
        {'summary': llm.redact(rule_text, names),
         'items': [{'material': i['material'], 'reason': i['reason']} for i in rule_items]},
    )
    for attempt in (1, 2):
        res = llm.chat_json('P6', messages, temperature=0.2, max_tokens=2000, attempt=attempt, learner=lp.user)
        if res.error and not res.raw:
            out['note'] = f'大模型接口调用失败（{res.error}），使用规则推荐'
            return out
        items, text, errors = check(res.data, cands)
        llm.mark(res.log, Check(format_errors=[] if res.data is not None else errors,
                                rule_errors=errors if res.data is not None else []))
        if not errors:
            out.update(source='llm', summary=llm.fill_name(text, lp.nickname),
                       items=llm.fill_name(items, lp.nickname))
            return out
        messages = messages + [{'role': 'assistant', 'content': res.raw},
                               {'role': 'user', 'content': prompts.refine_message(errors)}]
    out['note'] = '大模型输出两次未通过校验，使用规则推荐'
    return out
