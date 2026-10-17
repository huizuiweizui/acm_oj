"""
首页"今日推荐"：给学生挑接下来做的题。

三档，按顺序填满 n 道：
    1. 作业   所在团队进行中的作业里还没通过的题，截止时间近的在前。
    2. 重做   最近 RETRY_DAYS 天交过但没通过的题，最多 RETRY_MAX 道。
    3. 练习   其余公开且没通过的题，按得分从低到高取：
              - 难度：学生的水平 = 通过至少 LEVEL_AC 道的最高难度（一道没过算"入门"）；
                这一档通过满 STRETCH_AC 道就往上挑一档。离目标难度越远扣分越多，低于水平的扣得更多。
              - 薄弱标签：交过没通过的题按标签计数，题目带这些标签的加分（越薄弱加得越多）；
                没做过的标签小幅加分，扩大覆盖面。
              - 通过率：同样合适时优先通过率高的，提交太少的题按中等通过率算。
              - 每日扰动：按"用户 + 日期"定种子加一点随机，同一天结果稳定，第二天换一批。
每道题带一句推荐理由。
"""
import random
from collections import Counter
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from ..models import Assignment, Problem, Submission

LADDER = [d for d, _ in Problem.DIFFICULTY_CHOICES if d != '暂无评定']
LEVEL_AC = 3
STRETCH_AC = 8
RETRY_DAYS = 14
RETRY_MAX = 1
MIN_SUBMITS = 5
JITTER = 0.3
POOL = 300          # 练习档最多参与打分的题数


def _item(p, reason, kind):
    return {'id': p.id, 'title': p.title, 'difficulty': p.difficulty, 'reason': reason, 'kind': kind,
            'tags': [t.name for t in p.tags.all()]}


def user_level(solved):
    """返回 (目标难度下标, 说明)。solved 是已通过题目的 Problem 列表。"""
    cnt = Counter(p.difficulty for p in solved if p.difficulty in LADDER)
    level = 0
    for i, d in enumerate(LADDER):
        if cnt[d] >= LEVEL_AC:
            level = i
    if cnt[LADDER[level]] >= STRETCH_AC and level + 1 < len(LADDER):
        return level + 1, f'{LADDER[level]}题已通过 {cnt[LADDER[level]]} 道，试试{LADDER[level + 1]}'
    return level, ''


def _assignment_items(user, solved_ids, now):
    rows = (Assignment.objects
            .filter(team__memberships__user=user, team__is_active=True, is_active=True)
            .filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
            .filter(Q(deadline__isnull=True) | Q(deadline__gte=now))
            .prefetch_related('problems__problem__tags').distinct())
    out = []
    for a in sorted(rows, key=lambda a: (a.deadline is None, a.deadline or now)):
        if a.deadline:
            days = (a.deadline - now).days
            when = '今天截止' if days < 1 else f'还有 {days} 天截止'
        else:
            when = '没有截止时间'
        for ap in a.problems.order_by('sort_order', 'id'):
            if ap.problem_id not in solved_ids:
                out.append(_item(ap.problem, f'作业《{a.title}》里的题，{when}', 'assignment'))
    return out


def recommend_problems(user, n=3, today=None):
    now = timezone.now()
    today = today or timezone.localdate()
    subs = list(Submission.objects.filter(user=user).exclude(status__in=('Pending', 'Judging'))
                .values('problem_id', 'status', 'submitted_at'))
    solved_ids = {s['problem_id'] for s in subs if s['status'] == 'AC'}
    tried = {}                                   # 没通过的题 → 最近一次的结果
    for s in sorted(subs, key=lambda s: s['submitted_at']):
        if s['problem_id'] not in solved_ids:
            tried[s['problem_id']] = s

    picked, seen = [], set()

    def take(items):
        for it in items:
            if len(picked) >= n:
                return
            if it['id'] not in seen:
                seen.add(it['id'])
                picked.append(it)

    take(_assignment_items(user, solved_ids, now))

    recent = sorted((s for s in tried.values() if s['submitted_at'] >= now - timedelta(days=RETRY_DAYS)),
                    key=lambda s: s['submitted_at'], reverse=True)
    retry = {p.id: p for p in Problem.objects.filter(id__in=[s['problem_id'] for s in recent], is_published=True)
             .prefetch_related('tags')}
    take([_item(retry[s['problem_id']], f'上次结果是 {s["status"]}，再试一次', 'retry')
          for s in recent if s['problem_id'] in retry][:RETRY_MAX])
    if len(picked) >= n:
        return picked

    touched = Problem.objects.filter(id__in=solved_ids | set(tried)).prefetch_related('tags')
    solved = [p for p in touched if p.id in solved_ids]
    level, stretch_why = user_level(solved)
    weak = Counter(t.name for p in touched if p.id in tried for t in p.tags.all())
    done_tags = {t.name for p in solved for t in p.tags.all()}

    pool = (Problem.objects.filter(is_published=True).exclude(id__in=solved_ids | seen)
            .prefetch_related('tags').order_by('id'))
    # 先粗筛到目标难度附近，题库很大时也只给少量题打分
    near = [LADDER[i] for i in range(max(0, level - 1), min(len(LADDER), level + 2))]
    pool = list(pool.filter(difficulty__in=near)[:POOL]) or list(pool[:POOL])

    rng = random.Random(f'{user.id}-{today.isoformat()}')
    scored = []
    for p in pool:
        tags = [t.name for t in p.tags.all()]
        if p.difficulty in LADDER:
            d = LADDER.index(p.difficulty) - level
            score = 0 if d == 0 else (0.6 if d == 1 else (1.5 * -d if d < 0 else 3 + d))
        else:
            score = 1.0
        weak_tag = max(tags, key=lambda t: weak[t], default=None)
        new_tag = next((t for t in tags if t not in done_tags), None)
        if weak_tag and weak[weak_tag]:
            score -= min(1.0, 0.4 * weak[weak_tag])
            why = f'「{weak_tag}」类还有 {weak[weak_tag]} 道没通过，练一道同类题'
        elif new_tag and solved:
            score -= 0.3
            why = f'还没通过过「{new_tag}」类的题，扩展一下'
        elif stretch_why and p.difficulty == LADDER[level]:
            why = stretch_why
        else:
            why = f'难度和你现在的水平相当（{LADDER[level]}）' if solved else '从入门题开始，先熟悉评测流程'
        rate = p.ac_count / p.submit_count if p.submit_count >= MIN_SUBMITS else 0.5
        score -= 0.5 * rate
        score += rng.uniform(0, JITTER)
        scored.append((score, p.id, p, why))
    scored.sort(key=lambda x: (x[0], x[1]))
    take([_item(p, why, 'practice') for _, _, p, why in scored])
    return picked
