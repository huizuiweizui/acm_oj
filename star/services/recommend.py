"""
推荐下一项任务（教师端学生详情页）。两条分支：

    规则分支  按知识点顺序（顺序 → 条件 → 循环）找第一类"还没掌握"的知识点，
             从这一类里还没布置过的素材按素材库顺序取前 3 项。
             掌握 = 这一类至少做对 MASTER_STEPS 步，且做对时的平均提示等级 ≤ MASTER_HINT。
    大模型分支（P6）把画像、作答统计、候选素材和规则分支的结果一起交给大模型，
             由它从候选里挑 1–3 项并写理由；输出经程序校验（只能选候选里的、不重复、理由不超长），
             不合格回填错误改一次，仍不合格或没配大模型时用规则分支的结果。

两条分支的结果都返回给前端：主推荐是大模型的，规则的作为对照展示。
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
TOP_N = 3
REASON_MAX = 60
MODES = ('llm', 'template')


def candidates(lp):
    """学生所在层级里还没布置过的素材（生成失败的不算布置过），保持素材库顺序。"""
    have = set(AdaptedTask.objects.filter(student=lp.user).exclude(status='failed')
               .values_list('template', flat=True))
    if lp.layer == 'enlighten':
        rows = [{'key': lv['key'], 'title': lv['title'], 'knowledge': lv['knowledge'], 'has_default': True}
                for lv in LEVELS]
    else:
        rows = [{'key': p['slug'], 'title': p['title'], 'knowledge': p['knowledge'],
                 'has_default': bool(p.get('default_steps'))} for p in PROBLEMS]
    return [r for r in rows if r['key'] not in have]


def _item(c, reason, mode):
    return {'material': c['key'], 'title': c['title'], 'knowledge': c['knowledge'],
            'knowledge_name': KNOWLEDGE.get(c['knowledge'], c['knowledge']),
            'has_default': c['has_default'], 'reason': reason, 'mode': mode}


def rule_recommend(lp, summary, cands):
    """最简单的推荐：找第一类没掌握的知识点，从这一类往后取。返回 (items, summary_text)。"""
    order = ORDER.get(lp.layer, ORDER['intro'])
    by_k = summary.get('by_knowledge') or {}
    target = order[-1]
    for k in order:
        s = by_k.get(k)
        if not s or s['steps'] < MASTER_STEPS or (s['avg_hint'] or 0) > MASTER_HINT:
            target = k
            break
    t = by_k.get(target)
    name = KNOWLEDGE[target]
    if t is None:
        prev = order[order.index(target) - 1] if order.index(target) else None
        why = (f'{KNOWLEDGE[prev]}已掌握，进入{name}' if prev and prev in by_k
               else f'还没有{name}类的作答记录，从{name}开始')
        text = f'按"{"→".join(KNOWLEDGE[k] for k in order)}"的学习路线，{why}。'
    elif (t['avg_hint'] or 0) > MASTER_HINT:
        why = f'{name}类做对时平均提示等级 {t["avg_hint"]}，再练同类题巩固'
        text = f'{name}类还要靠提示完成，先巩固{name}。'
    else:
        why = f'{name}类只做对了 {t["steps"]} 步，再多练几道'
        text = f'{name}类练得还不多，继续练{name}。'

    # 目标知识点的素材在前，后面的知识点依次跟上；目标之前的（已掌握的）放最后
    i = order.index(target)
    rank = {k: n for n, k in enumerate(order[i:] + order[:i])}
    picked = sorted(cands, key=lambda c: rank.get(c['knowledge'], len(rank)))[:TOP_N]
    mode = 'llm' if t is not None and (t['avg_hint'] or 0) > MASTER_HINT else 'template'
    items = []
    for c in picked:
        reason = why if c['knowledge'] == target else f'{name}之后接着学{KNOWLEDGE[c["knowledge"]]}'
        items.append(_item(c, reason, mode if c['has_default'] else 'llm'))
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
        'note': 大模型没用上时的原因,
    }
    """
    stats = learner_stats(lp.user)
    summary = stats['summary']
    cands = candidates(lp)
    rule_items, rule_text = rule_recommend(lp, summary, cands) if cands else ([], '')
    rule = {'summary': llm.fill_name(rule_text, lp.nickname), 'items': rule_items}
    out = {'source': 'rule', 'summary': rule['summary'], 'items': rule_items, 'rule': rule, 'note': ''}
    if not cands:
        out['summary'] = rule['summary'] = '这个层级的素材都已经布置过了。'
        return out
    if not llm.is_configured():
        out['note'] = '未配置大模型，使用规则推荐'
        return out

    names = [lp.user.username, lp.nickname]
    messages = prompts.p6_messages(
        llm.redact(prompts.profile_summary(lp.profile), names),
        lp.layer,
        {k: summary[k] for k in ('tasks_total', 'tasks_done', 'steps_solved', 'avg_hint',
                                 'avg_hint_early', 'avg_hint_late', 'by_knowledge')},
        [dict(r, title=llm.redact(r['title'], names)) for r in _task_rows(stats)],
        [{'material': c['key'], 'title': c['title'], 'knowledge': KNOWLEDGE[c['knowledge']],
          'has_default': c['has_default']} for c in cands],
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

