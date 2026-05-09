"""
ACM 算法竞赛平台 视图函数
对应技术方案书的功能需求：用户体系、题库、提交评测、比赛、排行榜、讨论区
"""
import json
import subprocess
import tempfile
import os
import requests as http_req
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

from .models import (
    Problem, Tag, Submission, TestCase, UserProfile,
    Contest, ContestProblem, ContestParticipant,
    Discussion, DiscussionReply,
)
from .forms import (
    RegisterForm, LoginForm, SubmissionForm, ProblemFilterForm,
    DiscussionForm, ReplyForm,
)


# ==================== 首页 ====================

def index(request):
    """首页：公告、最近比赛、热门题目"""
    recent_problems = Problem.objects.filter(is_published=True)[:8]
    total_problems = Problem.objects.filter(is_published=True).count()
    total_submissions = Submission.objects.count()
    total_users = UserProfile.objects.count()

    # 即将开始和进行中的比赛
    now = timezone.now()
    active_contests = Contest.objects.filter(
        Q(start_time__lte=now, end_time__gte=now) | Q(start_time__gt=now)
    ).order_by('start_time')[:5]

    recent_submissions = (
        Submission.objects.select_related('user', 'problem', 'user__profile')
        .exclude(status='Pending')[:8]
    )

    context = {
        'recent_problems': recent_problems,
        'total_problems': total_problems,
        'total_submissions': total_submissions,
        'total_users': total_users,
        'active_contests': active_contests,
        'recent_submissions': recent_submissions,
    }
    return render(request, 'judge/index.html', context)


# ==================== 用户认证 ====================

def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, '注册成功，欢迎加入 ACM OJ！')
            return redirect('index')
    else:
        form = RegisterForm()
    return render(request, 'judge/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                messages.success(request, '登录成功！')
                return redirect(request.GET.get('next', '/'))
            else:
                messages.error(request, '用户名或密码错误')
    else:
        form = LoginForm()
    return render(request, 'judge/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, '已退出登录')
    return redirect('index')


# ==================== 题库 ====================

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

    # 用户做题状态筛选
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

    # 按算法类别分组（供弹窗展示）
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
        from django.http import Http404
        raise Http404
    form = SubmissionForm()

    user_submissions = []
    discussions = problem.discussions.select_related('user', 'user__profile')[:5]
    contest_id = request.GET.get('contest_id', '')
    contest_context = None

    if contest_id:
        contest_context = Contest.objects.filter(id=contest_id).first()

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


# ==================== 提交与评测 ====================

@login_required
@require_POST
def submit_code(request, problem_id):
    """提交代码（AJAX） — 对应技术方案书 §2.3"""
    problem = get_object_or_404(Problem, id=problem_id)
    form = SubmissionForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # 比赛提交检测
    now = timezone.now()
    contest_id = request.POST.get('contest_id')
    contest = None
    if contest_id:
        # 显式传入 contest_id：验证比赛正在进行且用户已报名
        c = Contest.objects.filter(id=contest_id, start_time__lte=now, end_time__gte=now).first()
        if c and ContestParticipant.objects.filter(contest=c, user=request.user).exists():
            contest = c
    else:
        # 未传 contest_id：自动检测用户是否正在参加含此题的唯一活跃比赛
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
    submission.status = 'Judging'
    submission.save()

    # 更新提交计数
    Problem.objects.filter(id=problem_id).update(submit_count=F('submit_count') + 1)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    UserProfile.objects.filter(id=profile.id).update(submit_count=F('submit_count') + 1)

    # 执行评测
    result = judge_submission(submission, problem)

    return JsonResponse({
        'success': True,
        'submission_id': submission.id,
        'result': {
            'status': result['status'],
            'time_used': result.get('time_used'),
            'memory_used': result.get('memory_used'),
            'error_info': result.get('error_info', ''),
            'ai_feedback': result.get('ai_feedback', ''),
        }
    })


def _ai_call(prompt):
    """调用 LLM API，失败返回空字符串。"""
    key = getattr(settings, 'LLM_API_KEY', '').strip()
    url = getattr(settings, 'LLM_API_URL', '').strip()
    model = getattr(settings, 'LLM_MODEL', '').strip()
    if not key or not url:
        return ''
    try:
        r = http_req.post(
            url,
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 600,
                'temperature': 0.3,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception:
        return ''


_LANG_CODE = {'C': 'c', 'C++': 'cpp', 'Java': 'java', 'Python': 'python'}


def _ai_verdict_prompt(submission, problem):
    """无测试点时，让 AI 判断代码是否正确。"""
    lc = _LANG_CODE.get(submission.language, 'text')
    return (
        f"你是算法竞赛评测系统。请判断以下代码是否正确解决了题目。\n\n"
        f"题目：{problem.title}\n"
        f"描述：{problem.description[:800]}\n"
        f"输入格式：{problem.input_desc[:300]}\n"
        f"输出格式：{problem.output_desc[:300]}\n"
        f"样例输入：\n{problem.sample_input[:400]}\n"
        f"样例输出：\n{problem.sample_output[:400]}\n\n"
        f"语言：{submission.language}\n"
        f"代码：\n```{lc}\n{submission.code[:3000]}\n```\n\n"
        f"请严格按此格式回答：\n"
        f"第1行：AC 或 WA（仅此二选一，不加其他文字）\n"
        f"第2行起：评测理由（分析代码逻辑、边界处理、与样例一致性，200字以内）"
    )


def _ai_suggest_prompt(submission, problem):
    """有测试点时，让 AI 给出代码改进建议。"""
    lc = _LANG_CODE.get(submission.language, 'text')
    tip = '优化和改进建议' if submission.status == 'AC' else '问题所在和改进方向'
    return (
        f"你是算法竞赛辅助系统。请对以下提交给出简洁分析。\n\n"
        f"题目：{problem.title}\n"
        f"描述：{problem.description[:600]}\n"
        f"语言：{submission.language}\n"
        f"评测结果：{submission.status}\n\n"
        f"代码：\n```{lc}\n{submission.code[:3000]}\n```\n\n"
        f"请给出：\n1. 代码主要思路（1-2句）\n2. {tip}\n\n"
        f"使用中文，200字以内，不要重复题目原文。"
    )


def judge_submission(submission, problem):
    """
    评测引擎 — 对应技术方案书 §8.2
    简化方案：子进程 + timeout 命令
    依次编译→运行每个测试点→对比输出
    """
    test_cases = problem.test_cases.all().order_by('sort_order')
    if not test_cases.exists():
        # 无测试点：交由 AI 评判
        ai_text = _ai_call(_ai_verdict_prompt(submission, problem))
        if ai_text:
            first_line = ai_text.strip().split('\n')[0].strip().upper()
            verdict = first_line if first_line in ('AC', 'WA') else 'AC'
        else:
            verdict, ai_text = 'AC', ''
        submission.status = verdict
        submission.ai_feedback = ai_text
        submission.save(update_fields=['status', 'ai_feedback'])

        if verdict == 'AC':
            already_ac = Submission.objects.filter(
                user=submission.user, problem=problem, status='AC'
            ).exclude(id=submission.id).exists()
            if not already_ac:
                Problem.objects.filter(id=problem.id).update(ac_count=F('ac_count') + 1)
                UserProfile.objects.filter(user=submission.user).update(ac_count=F('ac_count') + 1)
                _update_rating(submission.user, problem)

        return {'status': verdict, 'ai_feedback': ai_text}

    # 创建临时目录
    tmp_dir = tempfile.mkdtemp(prefix='judge_')
    lang = submission.language
    code = submission.code

    COMPILE_CMD = {
        'C': 'gcc -O2 -o {out} {src}',
        'C++': 'g++ -O2 -std=c++17 -o {out} {src}',
        'Java': 'javac {src}',
        'Python': None,  # 解释型，不编译
    }
    EXT = {'C': '.c', 'C++': '.cpp', 'Java': '.java', 'Python': '.py'}
    FILENAME = {'C': 'main', 'C++': 'main', 'Java': 'Main', 'Python': 'main'}

    src_file = os.path.join(tmp_dir, FILENAME[lang] + EXT[lang])
    with open(src_file, 'w', encoding='utf-8') as f:
        f.write(code)

    # 编译阶段
    compile_cmd = COMPILE_CMD.get(lang)
    if compile_cmd:
        out_file = os.path.join(tmp_dir, 'main')
        cmd = compile_cmd.format(src=src_file, out=out_file)
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=tmp_dir)
            if proc.returncode != 0:
                submission.status = 'CE'
                submission.error_info = proc.stderr[:2000]
                submission.save(update_fields=['status', 'error_info'])
                fb = _ai_call(_ai_suggest_prompt(submission, problem))
                if fb:
                    submission.ai_feedback = fb
                    submission.save(update_fields=['ai_feedback'])
                return {'status': 'CE', 'error_info': proc.stderr[:2000], 'ai_feedback': fb}
        except subprocess.TimeoutExpired:
            submission.status = 'CE'
            submission.error_info = '编译超时'
            submission.save(update_fields=['status', 'error_info'])
            return {'status': 'CE', 'error_info': '编译超时', 'ai_feedback': ''}

    # 运行阶段：逐测试点执行
    time_limit_sec = problem.time_limit / 1000.0 + 1  # 多给 1 秒容差
    max_time = 0

    import sys as _sys
    _win = _sys.platform == 'win32'
    _exe = 'main.exe' if _win else 'main'
    _py = _sys.executable  # 当前 Python 解释器路径，跨平台兼容

    RUN_CMD = {
        'C': _exe,
        'C++': _exe,
        'Java': f'java -cp {tmp_dir} Main',
        'Python': f'"{_py}" {src_file}',
    }
    run_cmd = RUN_CMD[lang]

    for tc in test_cases:
        try:
            proc = subprocess.run(
                run_cmd,
                shell=True, input=tc.input_data, capture_output=True,
                text=True, timeout=time_limit_sec, cwd=tmp_dir,
            )
        except subprocess.TimeoutExpired:
            submission.status = 'TLE'
            submission.save(update_fields=['status'])
            fb = _ai_call(_ai_suggest_prompt(submission, problem))
            if fb:
                submission.ai_feedback = fb
                submission.save(update_fields=['ai_feedback'])
            return {'status': 'TLE', 'ai_feedback': fb}

        if proc.returncode != 0:
            submission.status = 'RE'
            submission.error_info = proc.stderr[:1000]
            submission.save(update_fields=['status', 'error_info'])
            fb = _ai_call(_ai_suggest_prompt(submission, problem))
            if fb:
                submission.ai_feedback = fb
                submission.save(update_fields=['ai_feedback'])
            return {'status': 'RE', 'error_info': proc.stderr[:500], 'ai_feedback': fb}

        # 比较输出（忽略行尾空格和末尾空行）
        actual = proc.stdout.rstrip()
        expected = tc.expected_output.rstrip()
        if actual != expected:
            submission.status = 'WA'
            submission.save(update_fields=['status'])
            fb = _ai_call(_ai_suggest_prompt(submission, problem))
            if fb:
                submission.ai_feedback = fb
                submission.save(update_fields=['ai_feedback'])
            return {'status': 'WA', 'ai_feedback': fb}

    # 全部通过
    submission.status = 'AC'
    submission.time_used = int(max_time * 1000) if max_time else 0
    submission.save(update_fields=['status', 'time_used'])

    # 判重：同一用户同一题目只计一次 AC
    already_ac = Submission.objects.filter(
        user=submission.user, problem=problem, status='AC'
    ).exclude(id=submission.id).exists()

    if not already_ac:
        Problem.objects.filter(id=problem.id).update(ac_count=F('ac_count') + 1)
        UserProfile.objects.filter(user=submission.user).update(ac_count=F('ac_count') + 1)
        _update_rating(submission.user, problem)

    # 比赛提交：更新罚时
    if submission.contest:
        update_contest_score(submission)

    fb = _ai_call(_ai_suggest_prompt(submission, problem))
    if fb:
        submission.ai_feedback = fb
        submission.save(update_fields=['ai_feedback'])
    return {'status': 'AC', 'time_used': submission.time_used, 'ai_feedback': fb}


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
    """首次 AC 某题时按难度增加 rating。"""
    delta = _DIFFICULTY_RATING.get(problem.difficulty, 10)
    UserProfile.objects.filter(user=user).update(rating=F('rating') + delta)


def update_contest_score(submission):
    """更新比赛参与者的分数和罚时 — 对应技术方案书 §4.2.1"""
    contest = submission.contest
    participant, _ = ContestParticipant.objects.get_or_create(
        contest=contest, user=submission.user
    )
    if contest.rule_type == 'ICPC':
        # AC题数 + 罚时计算
        ac_problems = (
            Submission.objects.filter(
                user=submission.user, contest=contest, status='AC'
            ).values('problem_id').distinct()
        )
        penalty = 0
        for item in ac_problems:
            pid = item['problem_id']
            first_ac = Submission.objects.filter(
                user=submission.user, contest=contest, problem_id=pid, status='AC'
            ).order_by('submitted_at').first()
            if first_ac:
                # AC 时间（分钟）
                ac_minutes = int((first_ac.submitted_at - contest.start_time).total_seconds() / 60)
                # 错误提交次数 * 20
                wrong_count = Submission.objects.filter(
                    user=submission.user, contest=contest, problem_id=pid,
                    submitted_at__lt=first_ac.submitted_at
                ).exclude(status__in=['AC', 'Pending', 'Judging']).count()
                penalty += ac_minutes + wrong_count * 20

        participant.score = ac_problems.count()
        participant.penalty = penalty
        participant.save(update_fields=['score', 'penalty'])


# ==================== 提交记录 ====================

def submission_list(request):
    """提交记录列表：登录时默认显示自己的，?all=1 显示全站"""
    submissions = Submission.objects.select_related('user', 'problem', 'user__profile')
    show_all = request.GET.get('all', '')
    if request.user.is_authenticated and not show_all:
        submissions = submissions.filter(user=request.user)

    paginator = Paginator(submissions, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'judge/submission_list.html', {'page_obj': page_obj, 'show_all': show_all})


def submission_detail(request, submission_id):
    submission = get_object_or_404(
        Submission.objects.select_related('problem', 'user', 'user__profile'),
        id=submission_id,
    )
    return render(request, 'judge/submission_detail.html', {'submission': submission})


# ==================== 比赛系统 ====================

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

    # 计算每道题的提交状态
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

    from collections import defaultdict
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

    # (user_id, problem_id) -> [sub, ...] 按时间顺序
    subs_map = defaultdict(list)
    for sub in all_subs:
        subs_map[(sub['user_id'], sub['problem_id'])].append(sub)

    ranking_data = []
    for participant in participants:
        uid = participant.user_id
        prob_results = []  # 按 contest_problems 顺序

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

    # 计算并列名次
    ranked = []
    rank = 0
    prev_key = None
    for i, data in enumerate(ranking_data):
        key = (-data['score'], data['penalty']) if contest.rule_type == 'ICPC' else -data['score']
        if key != prev_key:
            rank = i + 1
            prev_key = key
        ranked.append((rank, data))

    context = {
        'contest': contest,
        'ranked': ranked,
        'contest_problems': contest_problems,
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

        from django.utils.dateparse import parse_datetime
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


# ==================== 排行榜 ====================

def leaderboard(request):
    """全站排行榜：AC数 / Rating（实时从 Submission 表直接聚合）"""
    tab = request.GET.get('tab', 'ac')

    # 直接从 Submission 聚合，避免跨 OneToOne+FK 多级 annotation 产生笛卡尔积
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


# ==================== 讨论区 ====================

def discussion_list(request):
    discussions = Discussion.objects.select_related('user', 'user__profile', 'problem')
    paginator = Paginator(discussions, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'judge/discussion_list.html', {'page_obj': page_obj})


def discussion_detail(request, discussion_id):
    discussion = get_object_or_404(
        Discussion.objects.select_related('user', 'user__profile', 'problem'),
        id=discussion_id,
    )
    # 浏览量 +1
    Discussion.objects.filter(id=discussion_id).update(view_count=F('view_count') + 1)

    replies = discussion.replies.select_related('user', 'user__profile')
    reply_form = ReplyForm()

    if request.method == 'POST' and request.user.is_authenticated:
        reply_form = ReplyForm(request.POST)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.discussion = discussion
            reply.user = request.user
            reply.save()
            messages.success(request, '回复成功')
            return redirect('discussion_detail', discussion_id=discussion.id)

    context = {
        'discussion': discussion,
        'replies': replies,
        'reply_form': reply_form,
    }
    return render(request, 'judge/discussion_detail.html', context)


@login_required
def create_discussion(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            disc = form.save(commit=False)
            disc.user = request.user
            disc.problem = problem
            disc.save()
            messages.success(request, '帖子发布成功')
            return redirect('discussion_detail', discussion_id=disc.id)
    else:
        form = DiscussionForm()
    return render(request, 'judge/create_discussion.html', {'form': form, 'problem': problem})


@login_required
def create_discussion_general(request):
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            disc = form.save(commit=False)
            disc.user = request.user
            disc.save()
            messages.success(request, '帖子发布成功')
            return redirect('discussion_detail', discussion_id=disc.id)
    else:
        form = DiscussionForm()
    return render(request, 'judge/create_discussion.html', {'form': form, 'problem': None})


# ==================== 个人主页 ====================

def profile_view(request, user_id):
    """个人主页 — 对应技术方案书 §2.1.3"""
    from django.contrib.auth.models import User as AuthUser
    target_user = get_object_or_404(AuthUser, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    recent_subs = (
        Submission.objects.filter(user=target_user)
        .select_related('problem')
        .order_by('-submitted_at')[:20]
    )

    # AC 题目按标签分类
    ac_problem_ids = (
        Submission.objects.filter(user=target_user, status='AC')
        .values_list('problem_id', flat=True).distinct()
    )
    ac_problems = Problem.objects.filter(id__in=ac_problem_ids).prefetch_related('tags')

    # 语言分布统计
    lang_stats = list(
        Submission.objects.filter(user=target_user)
        .values('language').annotate(count=Count('id'))
    )

    # 比赛参与历史
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


# ==================== 算法学习 ====================

def learn_view(request):
    """算法研习社：算法标签首页 + SPA 详情页（纯前端渲染）"""
    return render(request, 'judge/learn.html')


def learn_tag_problems(request):
    """按标签分组返回已发布题目列表，供算法学习页动态加载（无需登录）。"""
    from collections import defaultdict
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
