import json
import shutil
import tempfile
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Contest, ContestParticipant, Problem, Submission, Tag, UserProfile
from ..forms import ProblemFilterForm, SubmissionForm
from ..tasks import custom_run_task, judge_submission_task


def problem_list(request):
    """题目列表：分页 + 筛选 + 搜索"""
    form = ProblemFilterForm(request.GET)
    problems = Problem.objects.filter(is_published=True).prefetch_related('tags').annotate(
        real_submit_count=Count('submissions', distinct=True),
        real_ac_count=Count('submissions', filter=Q(submissions__status='AC'), distinct=True),
    )

    keyword = request.GET.get('keyword', '').strip()
    difficulty = request.GET.get('difficulty', '')
    tag = request.GET.get('tag', '')
    status_filter = request.GET.get('status', '')  # ac / tried / todo

    if keyword:
        problems = problems.filter(Q(id__icontains=keyword) | Q(title__icontains=keyword))
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    if tag:
        problems = problems.filter(tags__name=tag)

    user_ac_set = set()
    user_tried_set = set()
    if request.user.is_authenticated:
        user_ac_set = set(
            Submission.objects.filter(user=request.user, status='AC')
            .values_list('problem_id', flat=True).distinct()
        )
        user_tried_set = set(
            Submission.objects.filter(user=request.user)
            .exclude(status='AC')
            .values_list('problem_id', flat=True).distinct()
        ) - user_ac_set

        if status_filter == 'ac':
            problems = problems.filter(id__in=user_ac_set)
        elif status_filter == 'tried':
            problems = problems.filter(id__in=user_tried_set)
        elif status_filter == 'todo':
            problems = problems.exclude(id__in=user_ac_set | user_tried_set)

    paginator = Paginator(problems, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    all_tags = list(Tag.objects.annotate(cnt=Count('problems')).order_by('-cnt'))

    CATEGORIES = [
        ('基础算法', ['模拟', '贪心', '暴力', '枚举', '搜索', '递归', '递推', '分治', '排序', '二分', '前缀和', '差分', '位运算', '思维', '入门', '高精度']),
        ('数据结构', ['数据结构', '并查集', '堆', '线段树', '树状数组', '树形结构', '树', '优先队列', '栈', '队列', '哈希']),
        ('图论',    ['图论', '广搜BFS', '深搜DFS', '拓扑排序', '最短路', '最小生成树', '二分图', '网络流']),
        ('动态规划', ['动态规划', '区间DP', '树形DP', '背包', '棋盘DP', '数位DP', '状压DP']),
        ('字符串',  ['字符串', 'AC自动机', 'KMP', '后缀数组', '哈希']),
        ('数学',    ['数学', '数论', '矩阵', '几何', '组合数学', '快速幂']),
    ]
    tag_map = {t.name: t for t in all_tags}
    used = set()
    tag_groups = []
    for cat_name, names in CATEGORIES:
        group = [tag_map[n] for n in names if n in tag_map]
        if group:
            tag_groups.append({'name': cat_name, 'tags': group})
            used.update(t.name for t in group)
    rest = [t for t in all_tags if t.name not in used]
    if rest:
        tag_groups.append({'name': '其他', 'tags': rest})

    context = {
        'form': form,
        'page_obj': page_obj,
        'all_tags': all_tags,
        'tag_groups': tag_groups,
        'current_tag': tag,
        'keyword': keyword,
        'difficulty': difficulty,
        'status_filter': status_filter,
        'user_ac_set': user_ac_set,
        'user_tried_set': user_tried_set,
    }
    return render(request, 'judge/problem_list.html', context)


def problem_detail(request, problem_id):
    """题目详情：左侧题面 + 右侧代码编辑器"""
    problem = Problem.objects.filter(id=problem_id, is_published=True).annotate(
        real_submit_count=Count('submissions', distinct=True),
        real_ac_count=Count('submissions', filter=Q(submissions__status='AC'), distinct=True),
    ).first()
    if problem is None:
        raise Http404
    form = SubmissionForm()

    user_submissions = []
    discussions = problem.discussions.select_related('user', 'user__profile')[:5]
    contest_id = request.GET.get('contest_id', '')
    contest_context = None

    if contest_id:
        now = timezone.now()
        c = Contest.objects.filter(id=contest_id).first()
        if c:
            is_active = c.start_time <= now <= c.end_time
            is_registered = (
                request.user.is_authenticated
                and ContestParticipant.objects.filter(contest=c, user=request.user).exists()
            )
            # 只有"比赛进行中 + 已报名"才显示比赛模式横幅；
            # 未报名或比赛已结束时仍保留 contest_id，让链接可以回溯，但不显示"将计入"提示。
            contest_context = c if (is_active and is_registered) else None

    if request.user.is_authenticated:
        user_submissions = (
            Submission.objects.filter(user=request.user, problem=problem)
            .order_by('-submitted_at')[:10]
        )

    context = {
        'problem': problem,
        'form': form,
        'user_submissions': user_submissions,
        'discussions': discussions,
        'contest_id': contest_id,
        'contest_context': contest_context,
    }
    return render(request, 'judge/problem_detail.html', context)


@login_required
@require_POST
def submit_code(request, problem_id):
    """提交代码（AJAX） — 对应技术方案书 §2.3"""
    problem = get_object_or_404(Problem, id=problem_id)
    form = SubmissionForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    now = timezone.now()
    contest_id = request.POST.get('contest_id')
    contest = None
    if contest_id:
        c = Contest.objects.filter(id=contest_id, start_time__lte=now, end_time__gte=now).first()
        if c and ContestParticipant.objects.filter(contest=c, user=request.user).exists():
            contest = c
    else:
        active = Contest.objects.filter(
            contest_problems__problem=problem,
            participants__user=request.user,
            start_time__lte=now,
            end_time__gte=now,
        ).distinct()
        if active.count() == 1:
            contest = active.first()

    submission = form.save(commit=False)
    submission.user = request.user
    submission.problem = problem
    submission.contest = contest
    submission.status = 'Pending'
    submission.save()

    Problem.objects.filter(id=problem_id).update(submit_count=F('submit_count') + 1)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    UserProfile.objects.filter(id=profile.id).update(submit_count=F('submit_count') + 1)

    # 与 API 一致：丢进 Celery 队列异步评测，不在请求线程里同步跑（避免绕过并发闸门）
    judge_submission_task.delay(submission.id)

    return JsonResponse({
        'success': True,
        'submission_id': submission.id,
        'result': {'status': 'Pending'},
    })


@login_required
@require_POST
def custom_run(request, problem_id):
    """自定义测试：编译并运行用户代码，输出结果，不保存提交记录。"""
    get_object_or_404(Problem, id=problem_id, is_published=True)

    code = request.POST.get('code', '').strip()
    language = request.POST.get('language', 'C++')
    custom_input = request.POST.get('input', '')

    if not code:
        return JsonResponse({'success': False, 'error': '代码不能为空'})
    if language not in ('C', 'C++', 'Java', 'Python'):
        return JsonResponse({'success': False, 'error': '不支持的语言'})

    # 经 Celery 执行，与评测共用并发闸门；等待结果以保持原同步返回契约
    from django.conf import settings
    if settings.CELERY_TASK_ALWAYS_EAGER:
        r = custom_run_task.apply(args=[code, language, custom_input]).get()
    else:
        r = custom_run_task.delay(code, language, custom_input).get(timeout=30)

    return JsonResponse({
        'success': True,
        'result': {
            'status': 'ok' if r['status'] == 'OK' else r['status'],
            'output': r['output'],
            'error_info': r['error'],
        },
    })


def api_problems(request):
    """题目列表 JSON API — 供比赛创建题目选择器使用"""
    problems = Problem.objects.filter(is_published=True).prefetch_related('tags')

    keyword = request.GET.get('keyword', '').strip()
    difficulty = request.GET.get('difficulty', '').strip()
    tag = request.GET.get('tag', '').strip()

    if keyword:
        problems = problems.filter(Q(title__icontains=keyword) | Q(id__icontains=keyword))
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    if tag:
        problems = problems.filter(tags__name=tag)

    paginator = Paginator(problems, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    data = {
        'problems': [
            {
                'id': p.id,
                'title': p.title,
                'difficulty': p.difficulty,
                'tags': [t.name for t in p.tags.all()],
                'ac_count': p.ac_count,
                'submit_count': p.submit_count,
            }
            for p in page_obj
        ],
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'page': page_obj.number,
        'total_pages': page_obj.paginator.num_pages,
        'total_count': page_obj.paginator.count,
    }
    return JsonResponse(data)


def learn_view(request):
    """算法研习社：算法标签首页 + SPA 详情页（纯前端渲染）"""
    return render(request, 'judge/learn.html')


def learn_tag_problems(request):
    """按标签分组返回已发布题目列表，供算法学习页动态加载（无需登录）。"""
    tag_map = defaultdict(list)
    problems = (
        Problem.objects.filter(is_published=True)
        .prefetch_related('tags')
        .only('id', 'title', 'difficulty', 'ac_count', 'submit_count')
    )
    for prob in problems:
        pass_rate = (
            f'{round(prob.ac_count / prob.submit_count * 100, 1)}%'
            if prob.submit_count > 0 else '0.0%'
        )
        entry = {
            'id': prob.id,
            'title': prob.title,
            'difficulty': prob.difficulty,
            'pass_rate': pass_rate,
        }
        for tag in prob.tags.all():
            tag_map[tag.name].append(entry)
    return JsonResponse(dict(tag_map))
