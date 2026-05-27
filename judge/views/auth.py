from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import Contest, Problem, Submission, UserProfile
from ..forms import LoginForm, RegisterForm


def index(request):
    """首页：公告、最近比赛、热门题目"""
    recent_problems = Problem.objects.filter(is_published=True)[:8]
    total_problems = Problem.objects.filter(is_published=True).count()
    total_submissions = Submission.objects.count()
    total_users = UserProfile.objects.count()

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
