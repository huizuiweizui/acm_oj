from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User as AuthUser
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from ..models import ContestParticipant, Problem, Submission, UserProfile
from ..services.rating import _DIFFICULTY_RATING


def leaderboard(request):
    """全站排行榜：AC数 / Rating（实时从 Submission 表直接聚合）"""
    tab = request.GET.get('tab', 'ac')

    ac_counts = dict(
        Submission.objects.filter(status='AC')
        .values('user_id')
        .annotate(cnt=Count('problem_id', distinct=True))
        .values_list('user_id', 'cnt')
    )
    if not ac_counts:
        return render(request, 'judge/leaderboard.html', {'ranked_users': [], 'tab': tab})

    submit_counts = dict(
        Submission.objects.filter(user_id__in=ac_counts)
        .values('user_id')
        .annotate(cnt=Count('id'))
        .values_list('user_id', 'cnt')
    )

    profiles = list(
        UserProfile.objects.select_related('user').filter(user_id__in=ac_counts)
    )
    for p in profiles:
        p.real_ac = ac_counts.get(p.user_id, 0)
        p.real_submit = submit_counts.get(p.user_id, 0)

    if tab == 'rating':
        ac_difficulties = (
            Submission.objects.filter(status='AC', user_id__in=ac_counts)
            .values('user_id', 'problem_id', 'problem__difficulty')
            .distinct()
        )
        user_ratings: dict = {}
        for item in ac_difficulties:
            uid = item['user_id']
            diff = item['problem__difficulty']
            user_ratings[uid] = user_ratings.get(uid, 1500) + _DIFFICULTY_RATING.get(diff, 10)
        for p in profiles:
            p.display_rating = user_ratings.get(p.user_id, 1500)
        profiles.sort(key=lambda p: (-p.display_rating, -p.real_ac, p.real_submit))
        key_fn = lambda p: p.display_rating
    else:
        profiles.sort(key=lambda p: (-p.real_ac, p.real_submit))
        key_fn = lambda p: p.real_ac

    profiles = profiles[:100]

    ranked_users = []
    rank = 0
    prev_val = None
    for i, p in enumerate(profiles):
        val = key_fn(p)
        if val != prev_val:
            rank = i + 1
            prev_val = val
        ranked_users.append((rank, p))

    return render(request, 'judge/leaderboard.html', {'ranked_users': ranked_users, 'tab': tab})


def profile_view(request, user_id):
    """个人主页 — 对应技术方案书 §2.1.3"""
    target_user = get_object_or_404(AuthUser, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    recent_subs = (
        Submission.objects.filter(user=target_user)
        .select_related('problem')
        .order_by('-submitted_at')[:20]
    )

    ac_problem_ids = (
        Submission.objects.filter(user=target_user, status='AC')
        .values_list('problem_id', flat=True).distinct()
    )
    ac_problems = Problem.objects.filter(id__in=ac_problem_ids).prefetch_related('tags')

    lang_stats = list(
        Submission.objects.filter(user=target_user)
        .values('language').annotate(count=Count('id'))
    )

    contest_history = (
        ContestParticipant.objects.filter(user=target_user)
        .select_related('contest')
        .order_by('-contest__start_time')[:10]
    )

    context = {
        'target_user': target_user,
        'profile': profile,
        'recent_subs': recent_subs,
        'ac_problems': ac_problems,
        'lang_stats': lang_stats,
        'contest_history': contest_history,
    }
    return render(request, 'judge/profile.html', context)


@login_required
def my_profile(request):
    return redirect('profile', user_id=request.user.id)
