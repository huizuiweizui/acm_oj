import random
import shutil
import tempfile
import threading
from datetime import date, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import (
    Algorithm, AlgorithmEdge, KnowledgeChunk,
    Contest, ContestParticipant, ContestProblem,
    DailyCheckIn,
    Discussion, DiscussionReply,
    Problem, Submission, UserProfile,
    Team, Assignment, RatingChange,
)

_FORTUNE_MOODS   = ['大吉', '中吉', '小吉', '末吉', '凶']
_FORTUNE_LUCKY   = ['刷题', '写代码', '喝水', '早睡', '复习', '读书', '运动', '做笔记', '整理思路', '看题解']
_FORTUNE_UNLUCKY = ['摸鱼', '熬夜', '拖延', '乱投代码', '不测样例', '忘记保存', '跳过样例', '不读题']
from .serializers import (
    AlgorithmListSerializer, AlgorithmDetailSerializer,
    ContestSerializer, DiscussionReplySerializer, DiscussionSerializer,
    ProblemListSerializer, ProblemDetailSerializer,
    SubmissionSerializer, UserSerializer,
)
from .services.rating import apply_contest_rating


# ==================== 认证 ====================

class RegisterAPIView(APIView):
    """POST /api/auth/register/"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        password2 = request.data.get('password2', '').strip()

        if not username or not password:
            return Response({'detail': '用户名和密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if len(username) < 3 or len(username) > 20:
            return Response({'detail': '用户名长度须在 3~20 位之间'}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 6:
            return Response({'detail': '密码至少 6 位'}, status=status.HTTP_400_BAD_REQUEST)
        if password2 and password != password2:
            return Response({'detail': '两次密码不一致'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'detail': '用户名已被占用'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """POST /api/auth/login/"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()

        if not username or not password:
            return Response({'detail': '用户名和密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'detail': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class MeAPIView(APIView):
    """GET /api/auth/me/  PATCH /api/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        profile = request.user.profile
        profile_fields = {'bio', 'avatar_color', 'avatar_url', 'real_name', 'student_id'}
        changed_profile = list(profile_fields & set(request.data.keys()))
        for field in changed_profile:
            setattr(profile, field, request.data[field])
        if changed_profile:
            profile.save(update_fields=changed_profile)

        email = request.data.get('email', '').strip()
        if email:
            request.user.email = email
            request.user.save(update_fields=['email'])

        new_username = request.data.get('username', '').strip()
        if new_username and new_username != request.user.username:
            if len(new_username) < 3 or len(new_username) > 20:
                return Response({'detail': '用户名长度须在 3~20 位之间'}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                return Response({'detail': '用户名已被占用'}, status=status.HTTP_400_BAD_REQUEST)
            request.user.username = new_username
            request.user.save(update_fields=['username'])

        return Response(UserSerializer(request.user).data)


class LogoutAPIView(APIView):
    """POST /api/auth/logout/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': '需要提供 refresh token'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({'detail': 'token 无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': '已退出登录'})


class ChangePasswordAPIView(APIView):
    """POST /api/auth/password/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')

        if not request.user.check_password(old_password):
            return Response({'detail': '原密码错误'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 6:
            return Response({'detail': '新密码至少 6 位'}, status=status.HTTP_400_BAD_REQUEST)
        if old_password == new_password:
            return Response({'detail': '新密码不能与原密码相同'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        # 清除首次登录强制改密标志
        try:
            if request.user.profile.must_change_password:
                request.user.profile.must_change_password = False
                request.user.profile.save(update_fields=['must_change_password'])
        except Exception:
            pass
        return Response({'detail': '密码修改成功'})


# ==================== 题目 ====================

class ProblemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def _annotate_problems(qs):
    """给题目查询集附加真实提交/AC统计"""
    return qs.annotate(
        real_submit_count=Count('submissions', distinct=True),
        real_ac_count=Count('submissions', filter=Q(submissions__status='AC'), distinct=True),
    )


class ProblemListAPIView(generics.ListAPIView):
    """
    GET /api/problems/
    查询参数：keyword, difficulty, tag, page, page_size
    """
    serializer_class = ProblemListSerializer
    pagination_class = ProblemPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Problem.objects.filter(is_published=True).prefetch_related('tags').order_by('id')
        qs = _annotate_problems(qs)

        keyword = self.request.query_params.get('keyword', '').strip()
        difficulty = self.request.query_params.get('difficulty', '').strip()
        tag = self.request.query_params.get('tag', '').strip()

        if keyword:
            qs = qs.filter(Q(id__icontains=keyword) | Q(title__icontains=keyword))
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if tag:
            qs = qs.filter(tags__name=tag)

        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # 附加当前用户的做题状态
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
            )
            # 标注每道题的状态
            for p in response.data['results']:
                pid = p['id']
                if pid in user_ac_set:
                    p['user_status'] = 'ac'
                elif pid in user_tried_set:
                    p['user_status'] = 'tried'
                else:
                    p['user_status'] = 'todo'
        else:
            for p in response.data['results']:
                p['user_status'] = None

        return response


class ProblemDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/problems/<id>/
    """
    serializer_class = ProblemDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        problem_id = self.kwargs['pk']
        qs = Problem.objects.filter(id=problem_id, is_published=True)
        qs = _annotate_problems(qs).prefetch_related('tags')
        obj = qs.first()
        if obj is None:
            raise NotFound('题目不存在或未公开')
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = dict(self.get_serializer(instance).data)
        pub_ids = list(
            Problem.objects.filter(is_published=True).order_by('id').values_list('id', flat=True)
        )
        try:
            pos = pub_ids.index(instance.id)
            data['prev_id'] = pub_ids[pos - 1] if pos > 0 else None
            data['next_id'] = pub_ids[pos + 1] if pos < len(pub_ids) - 1 else None
        except ValueError:
            data['prev_id'] = data['next_id'] = None
        return Response(data)


# ==================== 提交记录 ====================

class SubmissionListAPIView(generics.ListAPIView):
    """
    GET /api/submissions/
    查询参数：all=1（全站）、problem_id、status、page
    未登录或不传 all=1 时只返回自己的提交
    """
    serializer_class = SubmissionSerializer
    pagination_class = ProblemPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Submission.objects.select_related('user', 'problem').order_by('-submitted_at')

        show_all = self.request.query_params.get('all', '')
        if self.request.user.is_authenticated and not show_all:
            qs = qs.filter(user=self.request.user)

        problem_id = self.request.query_params.get('problem_id', '').strip()
        status_filter = self.request.query_params.get('status', '').strip()
        user_id = self.request.query_params.get('user_id', '').strip()

        if problem_id:
            qs = qs.filter(problem_id=problem_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs


class SubmissionDetailAPIView(generics.RetrieveAPIView):
    """GET /api/submissions/<id>/"""
    serializer_class = SubmissionSerializer
    permission_classes = [AllowAny]
    queryset = Submission.objects.select_related('user', 'problem')


# ==================== 用户主页 ====================

class UserProfileAPIView(APIView):
    """
    GET /api/users/<id>/
    返回用户基本信息 + 近期提交 + 语言分布 + AC 统计
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        target = User.objects.filter(id=pk).select_related('profile').first()
        if target is None:
            raise NotFound('用户不存在')

        # 确保 profile 存在
        UserProfile.objects.get_or_create(user=target)
        target.refresh_from_db()

        # 近期提交（最近 20 条）
        recent_subs = (
            Submission.objects.filter(user=target)
            .select_related('problem')
            .order_by('-submitted_at')[:20]
        )

        # 语言分布
        from django.db.models import Count as _Count
        lang_stats = list(
            Submission.objects.filter(user=target)
            .values('language').annotate(count=_Count('id'))
        )

        # AC 题目数（去重）
        ac_problem_ids = (
            Submission.objects.filter(user=target, status='AC')
            .values_list('problem_id', flat=True).distinct()
        )

        # AC 题目列表（用于个人主页展示）
        ac_problems = list(
            Problem.objects.filter(id__in=ac_problem_ids)
            .order_by('id')
            .values('id', 'title')
        )

        # 比赛历史
        contest_history = [
            {
                'contest_id': cp.contest.id,
                'contest_title': cp.contest.title,
                'rule_type': cp.contest.rule_type,
                'score': cp.score,
                'penalty': cp.penalty,
                'date': cp.contest.start_time.strftime('%Y-%m-%d'),
            }
            for cp in ContestParticipant.objects.filter(user=target)
            .select_related('contest')
            .order_by('-contest__start_time')[:10]
        ]

        return Response({
            'user': UserSerializer(target).data,
            'recent_submissions': SubmissionSerializer(recent_subs, many=True).data,
            'language_dist': {item['language']: item['count'] for item in lang_stats},
            'ac_problem_count': ac_problem_ids.count(),
            'ac_problems': ac_problems,
            'contest_history': contest_history,
        })


# ==================== 用户统计（图表数据）====================

class UserStatsAPIView(APIView):
    """
    GET /api/users/<id>/stats/
    返回用于可视化图表的聚合数据：
      - ac_by_date:       近一年每日 AC 提交数（日历热力图）
      - ac_by_difficulty: AC 题目按难度分布（柱状图）
      - language_dist:    提交语言分布（饼图）
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        from datetime import date, timedelta
        from django.db.models import Count as _Count

        target = User.objects.filter(id=pk).first()
        if target is None:
            raise NotFound('用户不存在')

        # 1. 近一年每日 AC 提交数
        one_year_ago = date.today() - timedelta(days=365)
        ac_subs = (
            Submission.objects.filter(
                user=target, status='AC',
                submitted_at__date__gte=one_year_ago,
            )
            .values('submitted_at__date')
            .annotate(cnt=_Count('id'))
        )
        ac_by_date = {str(row['submitted_at__date']): row['cnt'] for row in ac_subs}

        # 2. AC 题目按难度分布
        ac_problem_ids = (
            Submission.objects.filter(user=target, status='AC')
            .values_list('problem_id', flat=True).distinct()
        )
        difficulty_qs = (
            Problem.objects.filter(id__in=ac_problem_ids)
            .values('difficulty').annotate(cnt=_Count('id'))
        )
        ac_by_difficulty = {row['difficulty']: row['cnt'] for row in difficulty_qs}

        # 3. 语言分布（全部提交）
        lang_qs = (
            Submission.objects.filter(user=target)
            .values('language').annotate(cnt=_Count('id'))
        )
        language_dist = {row['language']: row['cnt'] for row in lang_qs}

        return Response({
            'ac_by_date': ac_by_date,
            'ac_by_difficulty': ac_by_difficulty,
            'language_dist': language_dist,
        })


# ==================== 提交代码 ====================

VALID_LANGUAGES = ['C', 'C++', 'Java', 'Python']


def _run_judge_in_background(submission_id: int, problem_id: int):
    """在独立线程里执行评测，避免阻塞请求线程。"""
    # 延迟导入，避免模块循环引用
    from .views import judge_submission as _judge

    try:
        sub = Submission.objects.get(id=submission_id)
        prob = Problem.objects.get(id=problem_id)
        sub.status = 'Judging'
        sub.save(update_fields=['status'])
        _judge(sub, prob)
    except Exception:
        # 评测异常时把状态置为 RE，保证前端不会一直轮询
        Submission.objects.filter(id=submission_id).update(status='RE', error_info='Internal judge error')


class SubmitCodeAPIView(APIView):
    """
    POST /api/problems/<id>/submit/
    立即返回 submission_id（状态 Pending），后台线程评测。
    前端每 2 秒轮询 GET /api/submissions/<id>/ 直到状态不为 Pending/Judging。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        problem = Problem.objects.filter(id=pk, is_published=True).first()
        if problem is None:
            raise NotFound('题目不存在或未公开')

        language = request.data.get('language', '').strip()
        code = request.data.get('code', '').strip()

        if language not in VALID_LANGUAGES:
            return Response(
                {'detail': f'语言须为 {VALID_LANGUAGES} 之一'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not code:
            return Response({'detail': '代码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if len(code) > 65536:
            return Response({'detail': '代码不能超过 64 KB'}, status=status.HTTP_400_BAD_REQUEST)

        # 函数题：用隐藏驱动包裹学生函数体，拼成完整程序后再评测；原始函数另存
        raw_code = ''
        judged_code = code
        if problem.problem_type == 'function':
            wrapped = problem.wrap_code(language, code)
            if wrapped is None:
                return Response({'detail': '该函数题未配置此语言的评测模板'}, status=status.HTTP_400_BAD_REQUEST)
            raw_code = code
            judged_code = wrapped

        # 检测是否属于比赛提交
        now = timezone.now()
        contest = None
        contest_id = request.data.get('contest_id')
        if contest_id:
            c = Contest.objects.filter(
                id=contest_id, start_time__lte=now, end_time__gte=now
            ).first()
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

        # 检测是否属于作业/考试提交
        assignment = None
        assignment_id = request.data.get('assignment_id')
        if assignment_id:
            a = Assignment.objects.filter(
                id=assignment_id, problems__problem=problem
            ).first()
            if a and (a.team.creator_id == request.user.id
                      or a.team.memberships.filter(user=request.user).exists()):
                if a.category == 'exam':
                    if (not a.start_time or now >= a.start_time) and (not a.end_time or now <= a.end_time):
                        assignment = a
                elif a.is_active:
                    assignment = a

        submission = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=language,
            code=judged_code,
            raw_code=raw_code,
            status='Pending',
            contest=contest,
            assignment=assignment,
        )

        # 更新计数
        Problem.objects.filter(id=pk).update(submit_count=F('submit_count') + 1)
        UserProfile.objects.filter(user=request.user).update(submit_count=F('submit_count') + 1)

        # 后台线程评测（不阻塞响应）
        t = threading.Thread(
            target=_run_judge_in_background,
            args=(submission.id, problem.id),
            daemon=True,
        )
        t.start()

        return Response(
            {'submission_id': submission.id, 'status': 'Pending'},
            status=status.HTTP_201_CREATED,
        )


# ==================== 比赛 ====================

class ContestListAPIView(generics.ListAPIView):
    """
    GET /api/contests/
    查询参数：tab=all|running|upcoming|ended
    """
    serializer_class = ContestSerializer
    pagination_class = ProblemPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        now = timezone.now()
        qs = Contest.objects.filter(team__isnull=True).annotate(problem_count=Count('contest_problems')).order_by('-start_time')
        tab = self.request.query_params.get('tab', 'all')
        if tab == 'running':
            qs = qs.filter(start_time__lte=now, end_time__gte=now)
        elif tab == 'upcoming':
            qs = qs.filter(start_time__gt=now)
        elif tab == 'ended':
            qs = qs.filter(end_time__lt=now)
        return qs


class ContestDetailAPIView(APIView):
    """GET /api/contests/<id>/"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        contest = Contest.objects.filter(id=pk).first()
        if contest is None:
            raise NotFound('比赛不存在')

        contest_problems = (
            ContestProblem.objects.filter(contest=contest)
            .select_related('problem')
            .order_by('sort_order')
        )

        is_registered = False
        problem_status = {}
        if request.user.is_authenticated:
            is_registered = ContestParticipant.objects.filter(
                contest=contest, user=request.user
            ).exists()
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

        problems_data = [
            {
                'label': cp.label,
                'problem_id': cp.problem_id,
                'title': cp.problem.title,
                'difficulty': cp.problem.difficulty,
                'user_status': problem_status.get(cp.problem_id, 'todo'),
            }
            for cp in contest_problems
        ]

        return Response({
            'contest': ContestSerializer(contest).data,
            'problems': problems_data,
            'is_registered': is_registered,
            'participant_count': ContestParticipant.objects.filter(contest=contest).count(),
        })


class ContestRegisterAPIView(APIView):
    """POST /api/contests/<id>/register/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        contest = Contest.objects.filter(id=pk).first()
        if contest is None:
            raise NotFound('比赛不存在')

        now = timezone.now()
        if now > contest.end_time:
            return Response({'detail': '比赛已结束，无法报名'}, status=status.HTTP_400_BAD_REQUEST)

        _, created = ContestParticipant.objects.get_or_create(
            contest=contest, user=request.user
        )
        return Response(
            {'detail': '报名成功' if created else '已报名'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ContestCreateAPIView(APIView):
    """POST /api/contests/create/"""
    permission_classes = [IsAuthenticated]

    def _can_create(self, user):
        profile = getattr(user, 'profile', None)
        if profile is None:
            return False
        return profile.role in ('teacher', 'admin') or profile.can_create_contest

    def post(self, request):
        if not self._can_create(request.user):
            return Response({'detail': '无权创建比赛'}, status=status.HTTP_403_FORBIDDEN)
        from django.utils.dateparse import parse_datetime

        title = request.data.get('title', '').strip()
        description = request.data.get('description', '').strip()
        start_time_str = request.data.get('start_time', '')
        end_time_str = request.data.get('end_time', '')
        rule_type = request.data.get('rule_type', 'ICPC')
        problem_ids = request.data.get('problem_ids', [])

        if not title:
            return Response({'detail': '比赛名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if len(title) > 100:
            return Response({'detail': '比赛名称不能超过 100 字符'}, status=status.HTTP_400_BAD_REQUEST)
        if rule_type not in ('ICPC', 'IOI'):
            return Response({'detail': '赛制参数错误'}, status=status.HTTP_400_BAD_REQUEST)

        start_time = parse_datetime(start_time_str)
        end_time = parse_datetime(end_time_str)
        if not start_time or not end_time:
            return Response({'detail': '时间格式错误'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if start_time < now:
            return Response({'detail': '开始时间不能早于当前时间'}, status=status.HTTP_400_BAD_REQUEST)
        if end_time <= start_time:
            return Response({'detail': '结束时间必须晚于开始时间'}, status=status.HTTP_400_BAD_REQUEST)
        if (end_time - start_time).total_seconds() < 300:
            return Response({'detail': '结束时间必须晚于开始时间至少 5 分钟'}, status=status.HTTP_400_BAD_REQUEST)

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

        return Response({'id': contest.id}, status=status.HTTP_201_CREATED)


class ContestProblemPoolAPIView(APIView):
    """GET /api/contests/problem-pool/ — 题目选择器使用"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.core.paginator import Paginator

        qs = Problem.objects.filter(is_published=True).prefetch_related('tags')

        keyword = request.query_params.get('keyword', '').strip()
        difficulty = request.query_params.get('difficulty', '').strip()
        tag = request.query_params.get('tag', '').strip()

        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(id__icontains=keyword))
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if tag:
            qs = qs.filter(tags__name=tag)

        paginator = Paginator(qs, 15)
        page_obj = paginator.get_page(request.query_params.get('page', 1))

        return Response({
            'problems': [
                {
                    'id': p.id,
                    'title': p.title,
                    'difficulty': p.difficulty,
                    'tags': [t.name for t in p.tags.all()],
                }
                for p in page_obj
            ],
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page': page_obj.number,
            'total_pages': page_obj.paginator.num_pages,
            'total_count': page_obj.paginator.count,
        })


class UserContestPermAPIView(APIView):
    """
    PATCH /api/users/<pk>/contest-perm/
    教师或管理员授予/撤销学生创建比赛的权限
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        operator = request.user
        op_role = getattr(getattr(operator, 'profile', None), 'role', 'student')
        if op_role not in ('teacher', 'admin'):
            return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

        target = User.objects.filter(pk=pk).select_related('profile').first()
        if target is None:
            raise NotFound('用户不存在')

        target_role = getattr(target.profile, 'role', 'student')
        # 教师只能操作学生；管理员可以操作任何人
        if op_role == 'teacher' and target_role != 'student':
            return Response({'detail': '只能修改学生的权限'}, status=status.HTTP_403_FORBIDDEN)

        can = request.data.get('can_create_contest')
        if not isinstance(can, bool):
            return Response({'detail': 'can_create_contest 必须为布尔值'}, status=status.HTTP_400_BAD_REQUEST)

        target.profile.can_create_contest = can
        target.profile.save(update_fields=['can_create_contest'])
        return Response({'can_create_contest': can})


# ==================== 排行榜 ====================

class LeaderboardAPIView(APIView):
    """
    GET /api/rank/
    查询参数：tab=ac|rating（默认 ac）
    """
    permission_classes = [AllowAny]

    def get(self, request):
        tab = request.query_params.get('tab', 'ac')

        ac_counts = dict(
            Submission.objects.filter(status='AC')
            .values('user_id')
            .annotate(cnt=Count('problem_id', distinct=True))
            .values_list('user_id', 'cnt')
        )
        if not ac_counts:
            return Response({'tab': tab, 'ranked_users': []})

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
            profiles.sort(key=lambda p: (-p.rating, -p.real_ac, p.real_submit))
            key_fn = lambda p: p.rating
        else:
            profiles.sort(key=lambda p: (-p.real_ac, p.real_submit))
            key_fn = lambda p: p.real_ac

        profiles = profiles[:100]

        ranked = []
        rank = 0
        prev_val = None
        for i, p in enumerate(profiles):
            val = key_fn(p)
            if val != prev_val:
                rank = i + 1
                prev_val = val
            ranked.append({
                'rank': rank,
                'user_id': p.user_id,
                'username': p.user.username,
                'avatar_url': p.avatar_url,
                'avatar_color': p.avatar_color,
                'rating': p.rating,
                'ac_count': p.real_ac,
                'submit_count': p.real_submit,
            })

        return Response({'tab': tab, 'ranked_users': ranked})


# ==================== 算法学习 ====================

class AlgorithmListAPIView(generics.ListAPIView):
    serializer_class = AlgorithmListSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Algorithm.objects.all()


class AlgorithmDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AlgorithmDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'algo_id'

    def get_queryset(self):
        return Algorithm.objects.all()


# ==================== 讨论区 ====================

class DiscussionListAPIView(generics.ListAPIView):
    """
    GET /api/discussions/
    查询参数：problem_id
    """
    serializer_class = DiscussionSerializer
    pagination_class = ProblemPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Discussion.objects.select_related('user', 'problem').annotate(
            reply_count=Count('replies')
        ).order_by('-created_at')
        problem_id = self.request.query_params.get('problem_id', '').strip()
        if problem_id:
            qs = qs.filter(problem_id=problem_id)
        return qs


class DiscussionCreateAPIView(APIView):
    """POST /api/discussions/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        problem_id = request.data.get('problem_id')

        if not title:
            return Response({'detail': '标题不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not content:
            return Response({'detail': '内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        problem = None
        if problem_id:
            problem = Problem.objects.filter(id=problem_id).first()

        disc = Discussion.objects.create(
            user=request.user,
            title=title,
            content=content,
            problem=problem,
        )
        return Response(DiscussionSerializer(disc).data, status=status.HTTP_201_CREATED)


class DiscussionDetailAPIView(APIView):
    """GET /api/discussions/<id>/  DELETE /api/discussions/<id>/"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        disc = Discussion.objects.filter(id=pk).select_related('user', 'problem').annotate(reply_count=Count('replies')).first()
        if disc is None:
            raise NotFound('帖子不存在')

        Discussion.objects.filter(id=pk).update(view_count=F('view_count') + 1)
        disc.view_count += 1

        replies = disc.replies.select_related('user').order_by('created_at')

        return Response({
            'discussion': DiscussionSerializer(disc).data,
            'replies': DiscussionReplySerializer(replies, many=True).data,
        })

    def delete(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'detail': '请先登录'}, status=status.HTTP_401_UNAUTHORIZED)
        disc = Discussion.objects.filter(id=pk).first()
        if disc is None:
            raise NotFound('帖子不存在')
        if disc.user_id != request.user.id:
            return Response({'detail': '无权删除他人帖子'}, status=status.HTTP_403_FORBIDDEN)
        disc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== 比赛排行榜 ====================

def _ac_ratio(test_results):
    """编程题测试点通过率，用于 IOI 部分分。"""
    if not test_results:
        return 0.0
    total = len(test_results)
    return (sum(1 for c in test_results if c.get('status') == 'AC') / total) if total else 0.0


class ContestRankingAPIView(APIView):
    """GET /api/contests/<id>/rank/  支持 ICPC（解题+罚时）/ IOI（分数制）+ 封榜。"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        contest = Contest.objects.filter(id=pk).first()
        if contest is None:
            raise NotFound('比赛不存在')

        contest_problems = list(
            ContestProblem.objects.filter(contest=contest)
            .select_related('problem').order_by('sort_order')
        )
        problem_ids = [cp.problem_id for cp in contest_problems]
        labels = {cp.problem_id: cp.label for cp in contest_problems}
        points = {cp.problem_id: cp.points for cp in contest_problems}
        is_ioi = contest.rule_type == 'IOI'

        # 封榜：赛末 freeze_minutes 内的提交在榜上隐藏，赛后揭晓
        now = timezone.now()
        freeze_start = None
        frozen = False
        if contest.freeze_minutes and contest.freeze_minutes > 0:
            freeze_start = contest.end_time - timedelta(minutes=contest.freeze_minutes)
            frozen = freeze_start <= now < contest.end_time

        def base_resp(ranked_users):
            return {
                'contest': ContestSerializer(contest).data,
                'rule_type': contest.rule_type,
                'frozen': frozen,
                'freeze_minutes': contest.freeze_minutes,
                'problem_labels': [cp.label for cp in contest_problems],
                'problem_points': [points[cp.problem_id] for cp in contest_problems] if is_ioi else None,
                'ranked_users': ranked_users,
            }

        participants = list(
            ContestParticipant.objects.filter(contest=contest)
            .select_related('user', 'user__profile')
        )
        if not participants:
            return Response(base_resp([]))

        participant_ids = [p.user_id for p in participants]
        subs = list(
            Submission.objects.filter(
                contest=contest, user_id__in=participant_ids, problem_id__in=problem_ids,
            ).order_by('submitted_at')
        )

        cells = {
            uid: {pid: {'ac_time': None, 'wrong_count': 0, 'best_ratio': 0.0, 'frozen': 0}
                  for pid in problem_ids}
            for uid in participant_ids
        }
        for sub in subs:
            c = cells[sub.user_id][sub.problem_id]
            if frozen and freeze_start is not None and sub.submitted_at >= freeze_start:
                c['frozen'] += 1
                continue
            if is_ioi:
                ratio = 1.0 if sub.status == 'AC' else _ac_ratio(sub.test_results)
                c['best_ratio'] = max(c['best_ratio'], ratio)
            else:
                if c['ac_time'] is not None:
                    continue
                if sub.status == 'AC':
                    c['ac_time'] = sub.submitted_at
                elif sub.status in ('WA', 'TLE', 'MLE', 'RE', 'CE'):
                    c['wrong_count'] += 1

        start_time = contest.start_time
        ranked = []
        for p in participants:
            uid = p.user_id
            problem_results = {}
            try:
                avatar_color = p.user.profile.avatar_color
            except Exception:
                avatar_color = '#4F46E5'
            row = {'user_id': uid, 'username': p.user.username,
                   'avatar_color': avatar_color, 'problems': problem_results}

            if is_ioi:
                total = 0
                for pid in problem_ids:
                    c = cells[uid][pid]
                    sc = round(points[pid] * c['best_ratio'])
                    total += sc
                    problem_results[labels[pid]] = {'score': sc, 'max': points[pid], 'frozen': c['frozen']}
                row['score'] = total
            else:
                solved = penalty = 0
                for pid in problem_ids:
                    c = cells[uid][pid]
                    if c['ac_time'] is not None:
                        solved += 1
                        minutes = int((c['ac_time'] - start_time).total_seconds() / 60)
                        penalty += minutes + 20 * c['wrong_count']
                        problem_results[labels[pid]] = {'ac': True, 'wrong_count': c['wrong_count'],
                                                        'time_min': minutes, 'frozen': c['frozen']}
                    else:
                        problem_results[labels[pid]] = {'ac': False, 'wrong_count': c['wrong_count'],
                                                        'time_min': None, 'frozen': c['frozen']}
                row['solved'] = solved
                row['penalty'] = penalty
            ranked.append(row)

        if is_ioi:
            ranked.sort(key=lambda x: -x['score'])
            key_fn = lambda r: (r['score'],)
        else:
            ranked.sort(key=lambda x: (-x['solved'], x['penalty']))
            key_fn = lambda r: (r['solved'], r['penalty'])

        prev = None
        for i, r in enumerate(ranked):
            val = key_fn(r)
            if val != prev:
                r['rank'] = i + 1
                prev = val
            else:
                r['rank'] = ranked[i - 1]['rank']

        return Response(base_resp(ranked))


class ContestFinalizeRatingAPIView(APIView):
    """POST /api/contests/<pk>/finalize-rating/  比赛结束后结算 Rating（创建者/管理员）。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        contest = Contest.objects.filter(pk=pk).first()
        if contest is None:
            raise NotFound('比赛不存在')
        profile = getattr(request.user, 'profile', None)
        is_admin = bool(profile and profile.role == 'admin')
        if contest.created_by_id != request.user.id and not is_admin:
            return Response({'detail': '仅创建者或管理员可结算'}, status=status.HTTP_403_FORBIDDEN)
        if contest.status != 'ended':
            return Response({'detail': '比赛结束后才能结算 Rating'}, status=status.HTTP_400_BAD_REQUEST)
        if contest.rating_applied:
            return Response({'detail': '该比赛已结算过', 'applied': True}, status=status.HTTP_400_BAD_REQUEST)
        changes = apply_contest_rating(contest) or []
        return Response({'applied': True, 'count': len(changes), 'changes': changes})


class UserRatingHistoryAPIView(APIView):
    """GET /api/users/<pk>/rating-history/  Rating 变化曲线。"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        changes = (RatingChange.objects.filter(user_id=pk)
                   .select_related('contest').order_by('created_at'))
        return Response([{
            'contest_id': c.contest_id,
            'contest_title': c.contest.title,
            'rank': c.rank,
            'old_rating': c.old_rating,
            'new_rating': c.new_rating,
            'delta': c.delta,
            'date': c.created_at.isoformat(),
        } for c in changes])


# ==================== 平台统计 ====================

class PlatformStatsAPIView(APIView):
    """GET /api/stats/"""
    permission_classes = [AllowAny]

    def get(self, request):
        total_problems = Problem.objects.count()
        total_submissions = Submission.objects.count()
        total_users = UserProfile.objects.count()

        submissions_by_status = dict(
            Submission.objects.values('status')
            .annotate(cnt=Count('id'))
            .values_list('status', 'cnt')
        )

        today = date.today()
        start = today - timedelta(days=29)
        daily_map = {str(start + timedelta(days=i)): 0 for i in range(30)}

        for row in (
            Submission.objects
            .filter(submitted_at__date__gte=start)
            .annotate(day=TruncDate('submitted_at'))
            .values('day')
            .annotate(cnt=Count('id'))
        ):
            key = str(row['day'])
            if key in daily_map:
                daily_map[key] = row['cnt']

        # 近期比赛（进行中 + 即将开始 + 近14天已结束）
        now = timezone.now()
        cutoff = now - timedelta(days=14)
        active_contests = list(
            Contest.objects.filter(end_time__gt=cutoff)
            .order_by('-start_time')[:6]
            .values('id', 'title', 'start_time', 'end_time', 'rule_type', 'is_public')
        )
        for c in active_contests:
            if c['end_time'] < now:
                c['status'] = 'ended'
            elif c['start_time'] > now:
                c['status'] = 'upcoming'
            else:
                c['status'] = 'running'
            c['start_time'] = c['start_time'].strftime('%Y-%m-%d %H:%M')
            c['end_time'] = c['end_time'].strftime('%Y-%m-%d %H:%M')

        # 最新题目
        recent_problems = list(
            Problem.objects.filter(is_published=True)
            .order_by('-id')[:5]
            .values('id', 'title', 'difficulty')
        )
        for p in recent_problems:
            total = Submission.objects.filter(problem_id=p['id']).count()
            ac = Submission.objects.filter(problem_id=p['id'], status='AC').count()
            p['ac_rate'] = round(ac / total * 100, 1) if total else 0

        # 实时评测（全站最近 8 条）
        recent_subs_qs = (
            Submission.objects
            .select_related('user', 'user__profile', 'problem')
            .order_by('-submitted_at')[:8]
        )
        recent_submissions = [
            {
                'id': s.id,
                'username': s.user.username,
                'avatar_color': getattr(s.user, 'profile', None) and s.user.profile.avatar_color or '#4F46E5',
                'problem_id': s.problem.id,
                'problem_title': s.problem.title,
                'status': s.status,
                'submitted_at': s.submitted_at.isoformat(),
            }
            for s in recent_subs_qs
        ]

        return Response({
            'total_problems': total_problems,
            'total_submissions': total_submissions,
            'total_users': total_users,
            'submissions_by_status': submissions_by_status,
            'daily_submissions': [
                {'date': d, 'count': c} for d, c in daily_map.items()
            ],
            'active_contests': active_contests,
            'recent_problems': recent_problems,
            'recent_submissions': recent_submissions,
        })


# ==================== 用户仪表盘 ====================

class UserDashboardAPIView(APIView):
    """GET /api/dashboard/ — 登录用户首页所需的个人数据"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = date.today()

        # 1. 已AC题目数（去重）
        ac_count = (
            Submission.objects.filter(user=user, status='AC')
            .values('problem_id').distinct().count()
        )

        # 2. 总提交数
        total_submissions = Submission.objects.filter(user=user).count()

        # 3. 连续打卡天数（基于 DailyCheckIn）
        checkin_dates = set(
            DailyCheckIn.objects.filter(user=user)
            .values_list('date', flat=True)
        )
        streak = 0
        check = today
        while check in checkin_dates:
            streak += 1
            check -= timedelta(days=1)

        # 4. 热力图：近16周（112天）每日提交数
        cutoff = today - timedelta(days=111)
        heatmap_qs = (
            Submission.objects.filter(user=user, submitted_at__date__gte=cutoff)
            .values('submitted_at__date')
            .annotate(cnt=Count('id'))
        )
        heatmap = [{'date': str(row['submitted_at__date']), 'count': row['cnt']} for row in heatmap_qs]

        # 5. 近期比赛（进行中 + 即将开始 + 近14天已结束）
        now = timezone.now()
        contest_cutoff = now - timedelta(days=14)
        contests_qs = (
            Contest.objects.filter(end_time__gt=contest_cutoff)
            .order_by('-start_time')[:5]
            .values('id', 'title', 'start_time', 'end_time', 'rule_type')
        )
        recent_contests = [
            {
                'id': c['id'],
                'title': c['title'],
                'startTime': c['start_time'].isoformat(),
                'endTime': c['end_time'].isoformat(),
                'mode': c['rule_type'],
            }
            for c in contests_qs
        ]

        # 6. 今日打卡状态
        today_checkin = DailyCheckIn.objects.filter(user=user, date=today).first()
        checked_in_today = today_checkin is not None
        fortune = today_checkin.fortune if today_checkin else None

        return Response({
            'ac_count': ac_count,
            'total_submissions': total_submissions,
            'streak': streak,
            'heatmap': heatmap,
            'recent_contests': recent_contests,
            'checked_in_today': checked_in_today,
            'fortune': fortune,
        })


# ==================== 每日打卡 ====================

class CheckInAPIView(APIView):
    """
    GET  /api/checkin/ — 查询今日打卡状态
    POST /api/checkin/ — 执行今日打卡（已打卡返回 400）
    """
    permission_classes = [IsAuthenticated]

    def _build_response(self, checkin, streak):
        return Response({
            'checked_in': True,
            'date': str(checkin.date),
            'streak': streak,
            'fortune': checkin.fortune,
        })

    def _get_streak(self, user, today):
        checkin_dates = set(
            DailyCheckIn.objects.filter(user=user).values_list('date', flat=True)
        )
        streak, check = 0, today
        while check in checkin_dates:
            streak += 1
            check -= timedelta(days=1)
        return streak

    def get(self, request):
        today = date.today()
        checkin = DailyCheckIn.objects.filter(user=request.user, date=today).first()
        if checkin is None:
            return Response({'checked_in': False, 'date': str(today), 'streak': self._get_streak(request.user, today), 'fortune': None})
        return self._build_response(checkin, self._get_streak(request.user, today))

    def post(self, request):
        today = date.today()
        existing = DailyCheckIn.objects.filter(user=request.user, date=today).first()
        if existing:
            return Response(
                {'detail': '今天已经打卡了', **self._build_response(existing, self._get_streak(request.user, today)).data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fortune = {
            'mood':    random.choice(_FORTUNE_MOODS),
            'lucky':   random.sample(_FORTUNE_LUCKY, 2),
            'unlucky': random.sample(_FORTUNE_UNLUCKY, 2),
        }
        checkin = DailyCheckIn.objects.create(user=request.user, date=today, fortune=fortune)
        streak = self._get_streak(request.user, today)
        return self._build_response(checkin, streak)


def _is_admin(user):
    return hasattr(user, 'profile') and user.profile.role == 'admin'


def _is_super_admin(user):
    return _is_admin(user) and user.profile.is_super_admin


# ==================== 管理员 API ====================

class AdminStatsAPIView(APIView):
    """GET /api/admin/stats/ — 管理员专用扩展统计"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': '无权限'}, status=403)

        roles = dict(
            UserProfile.objects.values('role').annotate(cnt=Count('id')).values_list('role', 'cnt')
        )
        total_teams = Team.objects.count()
        today = date.today()
        today_reg = User.objects.filter(date_joined__date=today).count()
        week_start = today - timedelta(days=6)
        week_reg = User.objects.filter(date_joined__date__gte=week_start).count()

        recent_users = list(
            User.objects.order_by('-date_joined')
            .values('id', 'username', 'date_joined', 'profile__role',
                    'profile__real_name', 'profile__student_id')[:10]
        )
        for u in recent_users:
            u['date_joined'] = u['date_joined'].strftime('%Y-%m-%d %H:%M')
            u['role'] = u.pop('profile__role') or 'student'
            u['display_name'] = u.pop('profile__real_name') or ''
            u['student_id'] = u.pop('profile__student_id') or ''

        return Response({
            'roles': roles,
            'total_teams': total_teams,
            'today_reg': today_reg,
            'week_reg': week_reg,
            'recent_users': recent_users,
        })


class AdminUserListAPIView(APIView):
    """GET /api/admin/users/?page=1&search=&role= — 用户列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': '无权限'}, status=403)

        qs = User.objects.select_related('profile').order_by('-date_joined')
        search = request.query_params.get('search', '').strip()
        role = request.query_params.get('role', '').strip()

        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(profile__real_name__icontains=search) |
                Q(profile__student_id__icontains=search)
            )
        if role in ('student', 'teacher', 'admin'):
            qs = qs.filter(profile__role=role)

        page_size = 20
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        total = qs.count()
        start = (page - 1) * page_size
        users = list(qs.values(
            'id', 'username', 'date_joined',
            'profile__role', 'profile__real_name',
            'profile__student_id', 'profile__major', 'profile__grade',
            'profile__is_super_admin',
        )[start:start + page_size])
        for u in users:
            u['date_joined'] = u['date_joined'].strftime('%Y-%m-%d')
            u['role'] = u.pop('profile__role') or 'student'
            u['display_name'] = u.pop('profile__real_name') or ''
            u['student_id'] = u.pop('profile__student_id') or ''
            u['major'] = u.pop('profile__major') or ''
            u['grade'] = u.pop('profile__grade') or ''
            u['is_super_admin'] = u.pop('profile__is_super_admin') or False
            ac = Submission.objects.filter(user_id=u['id'], status='AC').values('problem_id').distinct().count()
            u['ac_count'] = ac

        return Response({'total': total, 'page': page, 'page_size': page_size, 'users': users})


class AdminUserUpdateAPIView(APIView):
    """PATCH /api/admin/users/<id>/ — 修改用户角色

    权限规则：
    - 任何管理员都可以将用户在 student / teacher 之间切换
    - 只有总管理员（is_super_admin）可以授予或撤销 admin 角色
    - 任何人都不能修改自己的角色
    - 总管理员的角色不可被普通管理员修改
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': '无权限'}, status=403)

        if request.user.pk == pk:
            return Response({'detail': '不能修改自己的角色'}, status=403)

        target = User.objects.filter(pk=pk).select_related('profile').first()
        if not target:
            return Response({'detail': '用户不存在'}, status=404)

        target_profile = target.profile
        new_role = request.data.get('role')

        if new_role not in ('student', 'teacher', 'admin'):
            return Response({'detail': '无效的角色值'}, status=400)

        # 总管理员受保护：只有总管理员自己可以操作涉及 admin 角色的变更
        if target_profile.is_super_admin:
            return Response({'detail': '总管理员角色受保护，无法通过此接口修改'}, status=403)

        # 非总管理员不能涉及 admin 角色（无论是设置还是从 admin 降级）
        caller_is_super = _is_super_admin(request.user)
        if not caller_is_super:
            if new_role == 'admin':
                return Response({'detail': '只有总管理员才能授予管理员权限'}, status=403)
            if target_profile.role == 'admin':
                return Response({'detail': '只有总管理员才能撤销管理员权限'}, status=403)

        target_profile.role = new_role
        target_profile.save()
        return Response({'ok': True, 'role': target_profile.role})


class AdminTransferSuperAdminAPIView(APIView):
    """POST /api/admin/transfer-super-admin/ — 总管理员转让

    body: { user_id: int }
    目标用户必须已经是 admin 角色。
    操作成功后：caller.is_super_admin = False, target.is_super_admin = True。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _is_super_admin(request.user):
            return Response({'detail': '只有总管理员才能执行转让操作'}, status=403)

        target_id = request.data.get('user_id')
        if not target_id:
            return Response({'detail': '缺少 user_id'}, status=400)

        if int(target_id) == request.user.pk:
            return Response({'detail': '不能将总管理员转让给自己'}, status=400)

        target = User.objects.filter(pk=target_id).select_related('profile').first()
        if not target:
            return Response({'detail': '目标用户不存在'}, status=404)
        if target.profile.role != 'admin':
            return Response({'detail': '目标用户必须先是管理员才能接受总管理员权限'}, status=400)

        # 原子操作：一次性切换
        my_profile = request.user.profile
        my_profile.is_super_admin = False
        my_profile.save(update_fields=['is_super_admin'])

        target.profile.is_super_admin = True
        target.profile.save(update_fields=['is_super_admin'])

        return Response({'ok': True, 'new_super_admin': target.username})


class DiscussionReplyCreateAPIView(APIView):
    """POST /api/discussions/<id>/replies/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        disc = Discussion.objects.filter(id=pk).first()
        if disc is None:
            raise NotFound('帖子不存在')

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': '回复内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        reply = DiscussionReply.objects.create(
            discussion=disc,
            user=request.user,
            content=content,
        )
        return Response(DiscussionReplySerializer(reply).data, status=status.HTTP_201_CREATED)


class DiscussionReplyDeleteAPIView(APIView):
    """DELETE /api/discussions/<id>/replies/<reply_id>/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, reply_id):
        reply = DiscussionReply.objects.filter(id=reply_id, discussion_id=pk).first()
        if reply is None:
            raise NotFound('回复不存在')
        if reply.user_id != request.user.id:
            return Response({'detail': '无权删除他人回复'}, status=status.HTTP_403_FORBIDDEN)
        reply.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── 算法知识图谱 ──────────────────────────────────────────────

CATEGORY_GROUP = {
    '基础算法': 0,
    '排序':    1,
    '搜索':    2,
    '贪心':    3,
    '动态规划': 4,
    '图论':    5,
    '数据结构': 6,
    '字符串':  7,
    '数学':    8,
}


class AlgorithmChunksAPIView(APIView):
    """GET /api/algorithms/<algo_id>/chunks/ — 返回该算法的知识片段列表"""
    permission_classes = [AllowAny]

    def get(self, request, algo_id):
        try:
            algo = Algorithm.objects.get(algo_id=algo_id)
        except Algorithm.DoesNotExist:
            raise NotFound()
        chunks = (KnowledgeChunk.objects
                  .filter(algo=algo)
                  .order_by('id')
                  .values('section', 'content'))
        return Response(list(chunks))


class AlgorithmGraphAPIView(APIView):
    """GET /api/algorithms/graph/"""
    permission_classes = [AllowAny]

    def get(self, request):
        algos = Algorithm.objects.all()
        nodes = [
            {
                'id':         a.algo_id,
                'name':       a.name,
                'name_en':    a.name_en,
                'category':   a.category,
                'difficulty': a.difficulty,
                'group':      CATEGORY_GROUP.get(a.category, 9),
            }
            for a in algos
        ]

        edges = AlgorithmEdge.objects.select_related('source', 'target').all()
        edge_list = [
            {
                'source': e.source.algo_id,
                'target': e.target.algo_id,
                'type':   e.edge_type,
            }
            for e in edges
        ]

        return Response({'nodes': nodes, 'edges': edge_list})


# ── AI 问答（RAG） ────────────────────────────────────────────

class AskAIAPIView(APIView):
    """POST /api/ai/ask/  — SSE 流式返回"""
    permission_classes = [AllowAny]

    def post(self, request):
        from judge.services.rag import retrieve, stream_answer

        question = (request.data.get('question') or '').strip()
        algo_id  = (request.data.get('algo_id')  or '').strip() or None
        if not question:
            return Response({'detail': '问题不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        chunks = retrieve(question, algo_id=algo_id, top_k=5)
        resp = StreamingHttpResponse(
            stream_answer(question, chunks),
            content_type='text/event-stream; charset=utf-8',
        )
        resp['Cache-Control']     = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


class CustomRunAPIView(APIView):
    """POST /api/problems/<pk>/run/  — 自定义测试，不保存提交记录"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from .services.sandbox import compile_code, run_code, source_path

        get_object_or_404(Problem, id=pk, is_published=True)

        code = request.data.get('code', '').strip()
        language = request.data.get('language', 'C++')
        custom_input = request.data.get('input', '')

        if not code:
            return Response({'detail': '代码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if language not in VALID_LANGUAGES:
            return Response({'detail': f'语言须为 {VALID_LANGUAGES} 之一'}, status=status.HTTP_400_BAD_REQUEST)

        tmp_dir = tempfile.mkdtemp(prefix='api_run_')
        try:
            src = source_path(language, tmp_dir)
            with open(src, 'w', encoding='utf-8') as f:
                f.write(code)

            ok, err_msg = compile_code(language, tmp_dir)
            if not ok:
                return Response({'status': 'CE', 'output': '', 'error': err_msg[:2000]})

            returncode, stdout_data, stderr_data, timed_out = run_code(
                language, tmp_dir, custom_input, timeout_sec=10.0, memory_mb=256,
            )

            if timed_out:
                run_status = 'TLE'
            elif returncode == 137:
                run_status = 'MLE'
            elif returncode != 0:
                run_status = 'RE'
            else:
                run_status = 'OK'

            return Response({
                'status': run_status,
                'output': stdout_data[:4096],
                'error': stderr_data[:1024] if run_status != 'OK' else '',
            })
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
