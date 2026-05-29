import json
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from ..models import Contest, ContestParticipant, ContestProblem, Problem, Submission, Tag


def contest_list(request):
    """比赛列表：进行中 / 即将开始 / 已结束"""
    now = timezone.now()
    contests = Contest.objects.annotate(problem_count=Count('contest_problems'))

    tab = request.GET.get('tab', 'all')
    if tab == 'running':
        contests = contests.filter(start_time__lte=now, end_time__gte=now)
    elif tab == 'upcoming':
        contests = contests.filter(start_time__gt=now)
    elif tab == 'ended':
        contests = contests.filter(end_time__lt=now)

    paginator = Paginator(contests, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'judge/contest_list.html', {'page_obj': page_obj, 'tab': tab})


def contest_detail(request, contest_id):
    """比赛详情：题目列表 + 排行榜入口"""
    contest = get_object_or_404(Contest, id=contest_id)
    contest_problems = contest.contest_problems.select_related('problem').order_by('sort_order')

    is_registered = False
    if request.user.is_authenticated:
        is_registered = ContestParticipant.objects.filter(
            contest=contest, user=request.user
        ).exists()

    problem_status = {}
    if request.user.is_authenticated:
        for cp in contest_problems:
            subs = Submission.objects.filter(
                user=request.user, problem=cp.problem, contest=contest
            )
            if subs.filter(status='AC').exists():
                problem_status[cp.problem_id] = 'ac'
            elif subs.exists():
                problem_status[cp.problem_id] = 'tried'
            else:
                problem_status[cp.problem_id] = 'todo'

    context = {
        'contest': contest,
        'contest_problems': contest_problems,
        'is_registered': is_registered,
        'problem_status': problem_status,
    }
    return render(request, 'judge/contest_detail.html', context)


@login_required
@require_POST
def contest_register(request, contest_id):
    """报名参加比赛"""
    contest = get_object_or_404(Contest, id=contest_id)

    if not contest.is_public and contest.password:
        pwd = request.POST.get('password', '')
        if pwd != contest.password:
            messages.error(request, '比赛密码错误')
            return redirect('contest_detail', contest_id=contest.id)

    ContestParticipant.objects.get_or_create(contest=contest, user=request.user)
    messages.success(request, '报名成功！')
    return redirect('contest_detail', contest_id=contest.id)


def contest_ranking(request, contest_id):
    """比赛排行榜（实时计算）"""
    contest = get_object_or_404(Contest, id=contest_id)
    contest_problems = list(
        contest.contest_problems.select_related('problem').order_by('sort_order')
    )
    problem_ids = {cp.problem_id for cp in contest_problems}

    participants = list(
        ContestParticipant.objects.filter(contest=contest)
        .select_related('user', 'user__profile')
    )

    if not participants:
        return render(request, 'judge/contest_ranking.html', {
            'contest': contest, 'ranked': [], 'contest_problems': contest_problems,
        })

    participant_user_ids = [p.user_id for p in participants]

    all_subs = list(
        Submission.objects.filter(
            contest=contest,
            user_id__in=participant_user_ids,
            problem_id__in=problem_ids,
            submitted_at__gte=contest.start_time,
            submitted_at__lte=contest.end_time,
        )
        .exclude(status__in=['Pending', 'Judging'])
        .order_by('submitted_at')
        .values('user_id', 'problem_id', 'status', 'submitted_at')
    )

    subs_map = defaultdict(list)
    for sub in all_subs:
        subs_map[(sub['user_id'], sub['problem_id'])].append(sub)

    ranking_data = []
    for participant in participants:
        uid = participant.user_id
        prob_results = []

        if contest.rule_type == 'ICPC':
            ac_count = 0
            total_penalty = 0
            for cp in contest_problems:
                subs = subs_map.get((uid, cp.problem_id), [])
                first_ac = None
                wrong_before_ac = 0
                for sub in subs:
                    if first_ac:
                        break
                    if sub['status'] == 'AC':
                        first_ac = sub
                    else:
                        wrong_before_ac += 1
                if first_ac:
                    ac_count += 1
                    ac_min = int((first_ac['submitted_at'] - contest.start_time).total_seconds() / 60)
                    prob_penalty = ac_min + wrong_before_ac * 20
                    total_penalty += prob_penalty
                    prob_results.append({'status': 'AC', 'wrong': wrong_before_ac, 'time': ac_min})
                elif subs:
                    prob_results.append({'status': 'WA', 'wrong': len(subs)})
                else:
                    prob_results.append(None)
            ranking_data.append({
                'participant': participant,
                'score': ac_count,
                'penalty': total_penalty,
                'prob_results': prob_results,
            })

        else:  # IOI
            total_score = 0
            for cp in contest_problems:
                subs = subs_map.get((uid, cp.problem_id), [])
                has_ac = any(s['status'] == 'AC' for s in subs)
                if has_ac:
                    total_score += 100
                    prob_results.append({'status': 'AC', 'points': 100})
                elif subs:
                    prob_results.append({'status': 'WA', 'wrong': len(subs)})
                else:
                    prob_results.append(None)
            ranking_data.append({
                'participant': participant,
                'score': total_score,
                'penalty': 0,
                'prob_results': prob_results,
            })

    if contest.rule_type == 'ICPC':
        ranking_data.sort(key=lambda x: (-x['score'], x['penalty']))
    else:
        ranking_data.sort(key=lambda x: -x['score'])

    ranked = []
    rank = 0
    prev_key = None
    for i, data in enumerate(ranking_data):
        key = (-data['score'], data['penalty']) if contest.rule_type == 'ICPC' else -data['score']
        if key != prev_key:
            rank = i + 1
            prev_key = key
        ranked.append((rank, data))

    now2 = timezone.now()
    context = {
        'contest': contest,
        'ranked': ranked,
        'contest_problems': contest_problems,
        'contest_is_active': contest.start_time <= now2 <= contest.end_time,
    }
    return render(request, 'judge/contest_ranking.html', context)


@login_required
def contest_create(request):
    """创建比赛（两步：基本信息 → 选题）— POST 接收 JSON"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'success': False, 'error': '请求数据格式错误'}, status=400)

        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        start_time_str = data.get('start_time', '')
        end_time_str = data.get('end_time', '')
        problem_ids = data.get('problem_ids', [])

        if not title:
            return JsonResponse({'success': False, 'error': '比赛名称不能为空'}, status=400)
        if len(title) > 100:
            return JsonResponse({'success': False, 'error': '比赛名称不能超过 100 字符'}, status=400)

        start_time = parse_datetime(start_time_str)
        end_time = parse_datetime(end_time_str)

        if not start_time or not end_time:
            return JsonResponse({'success': False, 'error': '时间格式错误'}, status=400)

        now = timezone.now()
        if start_time < now:
            return JsonResponse({'success': False, 'error': '开始时间不能早于当前时间'}, status=400)
        if end_time <= start_time:
            return JsonResponse({'success': False, 'error': '结束时间必须晚于开始时间'}, status=400)
        if (end_time - start_time).total_seconds() < 300:
            return JsonResponse({'success': False, 'error': '结束时间必须晚于开始时间至少 5 分钟'}, status=400)

        rule_type = data.get('rule_type', 'ICPC')
        if rule_type not in ('ICPC', 'IOI'):
            return JsonResponse({'success': False, 'error': '赛制参数错误'}, status=400)

        contest = Contest.objects.create(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            rule_type=rule_type,
            created_by=request.user,
        )

        labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for idx, pid in enumerate(problem_ids):
            problem = Problem.objects.filter(id=pid, is_published=True).first()
            if problem:
                ContestProblem.objects.create(
                    contest=contest,
                    problem=problem,
                    label=labels[idx] if idx < len(labels) else str(idx + 1),
                    sort_order=idx,
                )

        return JsonResponse({'success': True, 'contest_id': contest.id})

    all_tags = Tag.objects.annotate(cnt=Count('problems')).order_by('-cnt')
    has_problems = Problem.objects.filter(is_published=True).exists()
    return render(request, 'judge/contest_create.html', {
        'all_tags': all_tags,
        'has_problems': has_problems,
    })
