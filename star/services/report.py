"""
教师看板与学习报告的数据，全部从 StepAttempt 汇总。

提示等级的口径：每一步取"第一次做对时用到的最高提示等级"（0 = 没看提示，3 = 看了完整示范）。
它反映学生独立完成这一步需要多少帮助；练习一段时间后这个数应逐步下降——即提示渐褪。
"""
from statistics import mean

from ..models import AdaptedTask
from . import llm, prompts
from .learning import steps_total
from .validators import KNOWLEDGE


def _avg(xs):
    return round(mean(xs), 2) if xs else None


def task_stats(task):
    attempts = list(task.attempts.all())
    content = task.content or {}
    steps = content.get('steps') or []
    per_step = []
    for i in range(steps_total(task)):
        mine = [a for a in attempts if a.step_index == i]
        first_ok = next((a for a in mine if a.is_correct), None)
        upto = mine[:mine.index(first_ok) + 1] if first_ok else mine
        per_step.append({
            'step': i,
            'knowledge': content.get('knowledge') if task.layer == 'enlighten'
            else (steps[i].get('knowledge') if i < len(steps) else None),
            'attempts': len(mine),
            'done': first_ok is not None,
            'hint_level': first_ok.hint_level if first_ok else None,
            'duration_ms': sum(a.duration_ms for a in upto),
            'done_at': first_ok.created_at.isoformat() if first_ok else None,
        })
    row = {
        'task_id': task.id,
        'title': content.get('title') or task.template,
        'layer': task.layer,
        'steps': per_step,
        'done': bool(per_step) and all(s['done'] for s in per_step),
        'attempts': len(attempts),
    }
    if task.layer == 'enlighten':
        wins = [a.answer for a in attempts if a.is_correct]
        row['level'] = {
            'cleared': bool(wins),
            'best_cards': min((w.get('cards_used') for w in wins if w.get('cards_used')), default=None),
            'shortest': (attempts[-1].answer.get('shortest') if attempts else None),
            'runs': len(attempts),
        }
    return row


def learner_stats(user):
    tasks = (AdaptedTask.objects.filter(student=user, status='approved')
             .prefetch_related('attempts').order_by('sort_order', 'id'))
    rows = [task_stats(t) for t in tasks]
    solved = sorted((s for r in rows for s in r['steps'] if s['done']), key=lambda s: s['done_at'])
    levels = [s['hint_level'] for s in solved]
    half = len(levels) // 2
    by_knowledge = {}
    for k, name in KNOWLEDGE.items():
        ls = [s['hint_level'] for s in solved if s['knowledge'] == k]
        if ls:
            by_knowledge[k] = {'name': name, 'steps': len(ls), 'avg_hint': _avg(ls)}
    summary = {
        'tasks_total': len(rows),
        'tasks_done': sum(1 for r in rows if r['done']),
        'steps_solved': len(solved),
        'attempts': sum(r['attempts'] for r in rows),
        'avg_hint': _avg(levels),
        # 前一半与后一半已完成步骤的平均提示等级：后者更低，说明提示在渐褪
        'avg_hint_early': _avg(levels[:half]) if half else None,
        'avg_hint_late': _avg(levels[half:]) if half else None,
        'by_knowledge': by_knowledge,
        'levels_cleared': sum(1 for r in rows if r.get('level', {}).get('cleared')),
    }
    return {'summary': summary, 'tasks': rows,
            'hint_series': [{'hint_level': s['hint_level'], 'knowledge': s['knowledge']} for s in solved]}


def _rule_report(summary, audience):
    s = summary
    if not s['tasks_total']:
        return '{name}还没有已审核的学习任务。'
    knowledge = '、'.join(v['name'] for v in s['by_knowledge'].values()) or '编程基础'
    if audience == 'parent':
        text = f'{{name}}最近完成了 {s["tasks_done"]} 个编程小任务，练习了{knowledge}。'
        if s['avg_hint'] is not None and s['avg_hint'] <= 1:
            text += '大部分步骤是自己独立完成的。'
        else:
            text += '遇到困难时会使用提示，一步一步完成。'
        return text + '在家可以请孩子讲一讲今天让小角色走到了哪里，或者代码做了什么。'
    text = (f'{{name}}共有 {s["tasks_total"]} 个任务，已完成 {s["tasks_done"]} 个，'
            f'做对 {s["steps_solved"]} 个步骤，共作答 {s["attempts"]} 次。')
    if s['avg_hint'] is not None:
        text += f'做对时的平均提示等级为 {s["avg_hint"]}（0 为不看提示，3 为完整示范）。'
    if s['avg_hint_early'] is not None and s['avg_hint_late'] is not None:
        if s['avg_hint_late'] < s['avg_hint_early']:
            text += f'提示等级从 {s["avg_hint_early"]} 降到 {s["avg_hint_late"]}，出现提示渐褪。'
        else:
            text += f'前后提示等级为 {s["avg_hint_early"]} 与 {s["avg_hint_late"]}，暂未出现渐褪，建议重复练习同类任务。'
    hardest = max(s['by_knowledge'].values(), key=lambda v: v['avg_hint'] or 0, default=None)
    if hardest and hardest['avg_hint']:
        text += f'{hardest["name"]}类步骤用到的提示最多，可优先安排练习。'
    return text


def make_report(lp, audience):
    """返回 {'text': 报告正文, 'source': 'llm' | 'rule'}。"""
    stats = learner_stats(lp.user)
    summary = stats['summary']
    fallback = {'text': llm.fill_name(_rule_report(summary, audience), lp.nickname), 'source': 'rule'}
    if not llm.is_configured() or not summary['tasks_total']:
        return fallback
    res = llm.chat_json('P4', prompts.p4_messages(summary, audience), temperature=0.3,
                        max_tokens=600, learner=lp.user)
    text = (res.data or {}).get('report')
    if not isinstance(text, str) or not text.strip():
        return fallback
    return {'text': llm.fill_name(text.strip(), lp.nickname), 'source': 'llm'}
