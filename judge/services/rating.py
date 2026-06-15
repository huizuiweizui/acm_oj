import math

from django.db import transaction
from django.db.models import F

from ..models import (
    UserProfile, ContestParticipant, ContestProblem, Submission, RatingChange,
)

_DIFFICULTY_RATING = {
    '入门': 5,
    '普及-': 8,
    '普及/提高-': 12,
    '普及+/提高': 18,
    '提高+/省选-': 25,
    '省选/NOI-': 35,
    'NOI/NOI+/CTSC': 50,
    '暂无评定': 10,
}


def _update_rating(user, problem):
    """首次 AC 某题时按难度增加练习积分 rating（与比赛 contest_rating 区分）。"""
    delta = _DIFFICULTY_RATING.get(problem.difficulty, 10)
    UserProfile.objects.filter(user=user).update(rating=F('rating') + delta)


# ── CF 式比赛 Rating 结算 ────────────────────────────────────────────────────

def _compute_ranks(contest):
    """按 ICPC 规则（解题数↓、罚时↑）算每位参赛者名次，返回 [(user_id, rank)]，并列同名次。
    IOI 赛制暂以解题数近似。"""
    user_ids = list(ContestParticipant.objects.filter(contest=contest).values_list('user_id', flat=True))
    if not user_ids:
        return []
    problem_ids = list(ContestProblem.objects.filter(contest=contest).values_list('problem_id', flat=True))

    cells = {u: {p: {'ac': None, 'wrong': 0} for p in problem_ids} for u in user_ids}
    for uid, pid, st, ts in (Submission.objects
                             .filter(contest=contest, user_id__in=user_ids, problem_id__in=problem_ids)
                             .order_by('submitted_at')
                             .values_list('user_id', 'problem_id', 'status', 'submitted_at')):
        cell = cells[uid][pid]
        if cell['ac'] is not None:
            continue
        if st == 'AC':
            cell['ac'] = ts
        elif st in ('WA', 'TLE', 'MLE', 'RE', 'CE'):
            cell['wrong'] += 1

    perf = []
    for u in user_ids:
        solved = penalty = 0
        for p in problem_ids:
            c = cells[u][p]
            if c['ac']:
                solved += 1
                minutes = int((c['ac'] - contest.start_time).total_seconds() / 60)
                penalty += minutes + 20 * c['wrong']
        perf.append((u, solved, penalty))
    perf.sort(key=lambda x: (-x[1], x[2]))

    ranks, prev, rank = [], None, 0
    for i, (u, solved, pen) in enumerate(perf):
        key = (solved, pen)
        if key != prev:
            rank, prev = i + 1, key
        ranks.append((u, rank))
    return ranks


def _win_prob(ra, rb):
    """Elo：rating=ra 的选手胜过 rating=rb 的概率。"""
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def apply_contest_rating(contest):
    """CF 式赛后 Rating 结算（幂等：rating_applied 为真则跳过）。返回变化列表（按名次）。

    算法（Codeforces）：
      seed_i = 1 + Σ_{j≠i} P(j 胜 i)         —— 期望排名（排除自身）
      m_i    = sqrt(seed_i · 实际名次_i)       —— 期望与实际的几何平均
      target = 反解使 (排除 i 的)getSeed(target)=m_i 的 rating
      Δ_i    = (target − R_i) / 2，再做零和校正 + 头部稳定
    """
    if contest.rating_applied:
        return None

    standings = _compute_ranks(contest)
    n = len(standings)
    if n < 2:
        contest.rating_applied = True
        contest.save(update_fields=['rating_applied'])
        return []

    uids = [u for u, _ in standings]
    rank = {u: r for u, r in standings}
    profiles = {p.user_id: p for p in UserProfile.objects.filter(user_id__in=uids)}
    R = {u: (profiles[u].contest_rating if u in profiles else 1500) for u in uids}

    def get_seed(r, exclude):
        return 1.0 + sum(_win_prob(R[u], r) for u in uids if u != exclude)

    def rating_for_seed(target, exclude):
        lo, hi = 1, 8000
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if get_seed(mid, exclude) > target:   # seed 随 rating 递减
                lo = mid
            else:
                hi = mid
        return lo

    delta = {}
    for u in uids:
        seed_u = get_seed(R[u], u)                  # 排除自身
        target = rating_for_seed(math.sqrt(seed_u * rank[u]), u)
        delta[u] = (target - R[u]) // 2

    # 零和校正：整体微调使总变化 ≈ 0
    inc = -(sum(delta.values()) // n) - 1
    for u in uids:
        delta[u] += inc

    # 头部稳定：对 rating 最高的一批做温和向下修正（CF 经典步骤）
    s = min(n, max(1, round(4 * math.sqrt(n))))
    top = sorted(uids, key=lambda u: -R[u])[:s]
    inc2 = max(min(-(sum(delta[u] for u in top) // s), 0), -10)
    for u in top:
        delta[u] += inc2

    changes = []
    with transaction.atomic():
        for u in uids:
            old = R[u]
            new = max(1, old + delta[u])
            UserProfile.objects.filter(user_id=u).update(contest_rating=new)
            RatingChange.objects.update_or_create(
                user_id=u, contest=contest,
                defaults={'rank': rank[u], 'old_rating': old, 'new_rating': new, 'delta': new - old},
            )
            changes.append({'user_id': u, 'rank': rank[u], 'old_rating': old,
                            'new_rating': new, 'delta': new - old})
        contest.rating_applied = True
        contest.save(update_fields=['rating_applied'])

    changes.sort(key=lambda c: c['rank'])
    return changes
