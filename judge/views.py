"""
ACM 算法竞赛平台 视图函数
对应技术方案书的功能需求：用户体系、题库、提交评测、比赛、排行榜、讨论区
"""
import json
import subprocess
import tempfile
import os
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
    problems = Problem.objects.filter(is_published=True).prefetch_related('tags')

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
    all_tags = Tag.objects.annotate(cnt=Count('problems')).order_by('-cnt')[:20]

    context = {
        'form': form,
        'page_obj': page_obj,
        'all_tags': all_tags,
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
    problem = get_object_or_404(Problem, id=problem_id, is_published=True)
    form = SubmissionForm()

    user_submissions = []
    discussions = problem.discussions.select_related('user', 'user__profile')[:5]

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
    contest_id = request.POST.get('contest_id')
    contest = None
    if contest_id:
        contest = Contest.objects.filter(id=contest_id).first()

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
        }
    })


def judge_submission(submission, problem):
    """
    评测引擎 — 对应技术方案书 §8.2
    简化方案：子进程 + timeout 命令
    依次编译→运行每个测试点→对比输出
    """
    test_cases = problem.test_cases.all().order_by('sort_order')
    if not test_cases.exists():
        submission.status = 'AC'
        submission.save(update_fields=['status'])
        return {'status': 'AC'}

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
                return {'status': 'CE', 'error_info': proc.stderr[:2000]}
        except subprocess.TimeoutExpired:
            submission.status = 'CE'
            submission.error_info = '编译超时'
            submission.save(update_fields=['status', 'error_info'])
            return {'status': 'CE', 'error_info': '编译超时'}

    # 运行阶段：逐测试点执行
    time_limit_sec = problem.time_limit / 1000.0 + 1  # 多给 1 秒容差
    max_time = 0

    RUN_CMD = {
        'C': './main',
        'C++': './main',
        'Java': f'java -cp {tmp_dir} Main',
        'Python': f'python3 {src_file}',
    }
    run_cmd = RUN_CMD[lang]

    for tc in test_cases:
        try:
            proc = subprocess.run(
                f'timeout {time_limit_sec} {run_cmd}',
                shell=True, input=tc.input_data, capture_output=True,
                text=True, timeout=time_limit_sec + 2, cwd=tmp_dir,
            )
        except subprocess.TimeoutExpired:
            submission.status = 'TLE'
            submission.save(update_fields=['status'])
            return {'status': 'TLE'}

        if proc.returncode != 0:
            # timeout 命令返回 124 表示超时
            if proc.returncode == 124:
                submission.status = 'TLE'
                submission.save(update_fields=['status'])
                return {'status': 'TLE'}
            submission.status = 'RE'
            submission.error_info = proc.stderr[:1000]
            submission.save(update_fields=['status', 'error_info'])
            return {'status': 'RE', 'error_info': proc.stderr[:500]}

        # 比较输出（忽略行尾空格和末尾空行）
        actual = proc.stdout.rstrip()
        expected = tc.expected_output.rstrip()
        if actual != expected:
            submission.status = 'WA'
            submission.save(update_fields=['status'])
            return {'status': 'WA'}

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

    # 比赛提交：更新罚时
    if submission.contest:
        update_contest_score(submission)

    return {'status': 'AC', 'time_used': submission.time_used}


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
    """提交记录列表（全站 / 个人）"""
    submissions = Submission.objects.select_related('user', 'problem', 'user__profile')
    mine = request.GET.get('mine', '')
    if mine and request.user.is_authenticated:
        submissions = submissions.filter(user=request.user)

    paginator = Paginator(submissions, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'judge/submission_list.html', {'page_obj': page_obj, 'mine': mine})


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
    contests = Contest.objects.all()

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
    """比赛排行榜 — 对应技术方案书 §2.4.3"""
    contest = get_object_or_404(Contest, id=contest_id)

    if contest.rule_type == 'ICPC':
        ranking = (
            ContestParticipant.objects.filter(contest=contest)
            .select_related('user', 'user__profile')
            .order_by('-score', 'penalty')
        )
    else:  # IOI
        ranking = (
            ContestParticipant.objects.filter(contest=contest)
            .select_related('user', 'user__profile')
            .order_by('-score')
        )

    contest_problems = contest.contest_problems.select_related('problem').order_by('sort_order')

    context = {
        'contest': contest,
        'ranking': ranking,
        'contest_problems': contest_problems,
    }
    return render(request, 'judge/contest_ranking.html', context)


# ==================== 排行榜 ====================

def leaderboard(request):
    """全站排行榜：AC数 / Rating"""
    tab = request.GET.get('tab', 'ac')
    if tab == 'rating':
        users = UserProfile.objects.select_related('user').order_by('-rating')[:100]
    else:
        users = UserProfile.objects.select_related('user').filter(ac_count__gt=0).order_by('-ac_count', 'submit_count')[:100]
    return render(request, 'judge/leaderboard.html', {'users': users, 'tab': tab})


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
