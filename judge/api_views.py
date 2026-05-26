import threading
from datetime import date, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Contest, ContestParticipant, ContestProblem,
    Discussion, DiscussionReply,
    Problem, Submission, UserProfile,
)
from .serializers import (
    ContestSerializer, DiscussionReplySerializer, DiscussionSerializer,
    ProblemListSerializer, ProblemDetailSerializer,
    SubmissionSerializer, UserSerializer,
)


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
    """GET /api/auth/me/  —  获取当前登录用户信息"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


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

        return Response({
            'user': UserSerializer(target).data,
            'recent_submissions': SubmissionSerializer(recent_subs, many=True).data,
            'language_dist': {item['language']: item['count'] for item in lang_stats},
            'ac_problem_count': ac_problem_ids.count(),
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

        submission = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=language,
            code=code,
            status='Pending',
            contest=contest,
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
        qs = Contest.objects.annotate(problem_count=Count('contest_problems')).order_by('-start_time')
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
        disc.reply_count = 0
        return Response(DiscussionSerializer(disc).data, status=status.HTTP_201_CREATED)


class DiscussionDetailAPIView(APIView):
    """GET /api/discussions/<id>/"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        disc = Discussion.objects.filter(id=pk).select_related('user', 'problem').first()
        if disc is None:
            raise NotFound('帖子不存在')

        Discussion.objects.filter(id=pk).update(view_count=F('view_count') + 1)
        disc.view_count += 1

        replies = disc.replies.select_related('user').order_by('created_at')
        disc.reply_count = replies.count()

        return Response({
            'discussion': DiscussionSerializer(disc).data,
            'replies': DiscussionReplySerializer(replies, many=True).data,
        })


# ==================== 比赛排行榜 ====================

class ContestRankingAPIView(APIView):
    """GET /api/contests/<id>/rank/"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        contest = Contest.objects.filter(id=pk).first()
        if contest is None:
            raise NotFound('比赛不存在')

        contest_problems = list(
            ContestProblem.objects.filter(contest=contest)
            .select_related('problem')
            .order_by('sort_order')
        )
        problem_ids = [cp.problem_id for cp in contest_problems]
        problem_labels = {cp.problem_id: cp.label for cp in contest_problems}

        participants = list(
            ContestParticipant.objects.filter(contest=contest)
            .select_related('user', 'user__profile')
        )
        if not participants:
            return Response({
                'contest': ContestSerializer(contest).data,
                'problem_labels': [cp.label for cp in contest_problems],
                'ranked_users': [],
            })

        participant_ids = [p.user_id for p in participants]

        subs = list(
            Submission.objects.filter(
                contest=contest,
                user_id__in=participant_ids,
                problem_id__in=problem_ids,
            ).order_by('submitted_at')
        )

        # user_id → problem_id → {ac_time, wrong_count}
        user_problem = {
            uid: {pid: {'ac_time': None, 'wrong_count': 0} for pid in problem_ids}
            for uid in participant_ids
        }
        for sub in subs:
            up = user_problem[sub.user_id][sub.problem_id]
            if up['ac_time'] is not None:
                continue
            if sub.status == 'AC':
                up['ac_time'] = sub.submitted_at
            elif sub.status in ('WA', 'TLE', 'MLE', 'RE', 'CE'):
                up['wrong_count'] += 1

        start_time = contest.start_time
        ranked = []
        for p in participants:
            uid = p.user_id
            solved = 0
            penalty = 0
            problem_results = {}

            for pid in problem_ids:
                up = user_problem[uid][pid]
                label = problem_labels[pid]
                if up['ac_time'] is not None:
                    solved += 1
                    minutes = int((up['ac_time'] - start_time).total_seconds() / 60)
                    penalty += minutes + 20 * up['wrong_count']
                    problem_results[label] = {
                        'ac': True, 'wrong_count': up['wrong_count'], 'time_min': minutes,
                    }
                else:
                    problem_results[label] = {
                        'ac': False, 'wrong_count': up['wrong_count'], 'time_min': None,
                    }

            try:
                profile = p.user.profile
                avatar_color = profile.avatar_color
            except Exception:
                avatar_color = '#4F46E5'

            ranked.append({
                'user_id': uid,
                'username': p.user.username,
                'avatar_color': avatar_color,
                'solved': solved,
                'penalty': penalty,
                'problems': problem_results,
            })

        ranked.sort(key=lambda x: (-x['solved'], x['penalty']))
        prev = None
        for i, r in enumerate(ranked):
            val = (r['solved'], r['penalty'])
            if val != prev:
                r['rank'] = i + 1
                prev = val
            else:
                r['rank'] = ranked[i - 1]['rank']

        return Response({
            'contest': ContestSerializer(contest).data,
            'problem_labels': [cp.label for cp in contest_problems],
            'ranked_users': ranked,
        })


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

        return Response({
            'total_problems': total_problems,
            'total_submissions': total_submissions,
            'total_users': total_users,
            'submissions_by_status': submissions_by_status,
            'daily_submissions': [
                {'date': d, 'count': c} for d, c in daily_map.items()
            ],
        })


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
