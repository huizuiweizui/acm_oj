"""社区功能：题解（AC 后可见）、提交结果分布、每日一题。"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Problem, Submission, Solution, DailyProblem


def _has_ac(user, problem_id):
    return (user.is_authenticated and
            Submission.objects.filter(user=user, problem_id=problem_id, status='AC').exists())


# ── 题解（AC 后可见，防剧透）────────────────────────────────────────────────────

def _sol_data(s, viewer):
    return {
        'id': s.id,
        'username': s.user.username,
        'title': s.title,
        'content': s.content,
        'language': s.language,
        'upvotes': s.upvotes,
        'created_at': s.created_at.isoformat(),
        'is_author': viewer.is_authenticated and viewer.id == s.user_id,
    }


class SolutionListCreateAPIView(APIView):
    """GET|POST /api/problems/<pk>/solutions/  仅 AC 该题者可看/可发。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        get_object_or_404(Problem, pk=pk)
        if not _has_ac(request.user, pk):
            return Response({'locked': True, 'detail': 'AC 本题后才能查看题解', 'solutions': []})
        sols = Solution.objects.filter(problem_id=pk).select_related('user')[:50]
        return Response({'locked': False, 'solutions': [_sol_data(s, request.user) for s in sols]})

    def post(self, request, pk):
        problem = get_object_or_404(Problem, pk=pk)
        if not _has_ac(request.user, pk):
            return Response({'detail': 'AC 本题后才能发布题解'}, status=status.HTTP_403_FORBIDDEN)
        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'detail': '题解内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        s = Solution.objects.create(
            problem=problem, user=request.user, content=content,
            title=(request.data.get('title') or '').strip()[:200],
            language=(request.data.get('language') or '')[:10],
        )
        return Response(_sol_data(s, request.user), status=status.HTTP_201_CREATED)


class SolutionDeleteAPIView(APIView):
    """DELETE /api/solutions/<pk>/  作者或管理员。"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        sol = get_object_or_404(Solution, pk=pk)
        profile = getattr(request.user, 'profile', None)
        is_admin = bool(profile and profile.role == 'admin')
        if sol.user_id != request.user.id and not is_admin:
            return Response({'detail': '无权删除'}, status=status.HTTP_403_FORBIDDEN)
        sol.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── 提交结果分布（LeetCode 式「击败 X%」）─────────────────────────────────────────

class ProblemDistributionAPIView(APIView):
    """GET /api/problems/<pk>/distribution/?metric=time|memory
    返回该题 AC 提交在耗时/内存上的分布直方图，附当前用户的最好成绩与击败百分比。
    """
    permission_classes = [AllowAny]
    BUCKETS = 10

    def get(self, request, pk):
        # 仅按耗时分布；内存峰值未测量（不碰评测核心 judger/sandbox，见 docs/07）
        metric = 'time_used'
        vals = sorted(
            Submission.objects.filter(problem_id=pk, status='AC', **{f'{metric}__isnull': False})
            .values_list(metric, flat=True)
        )
        n = len(vals)
        if n == 0:
            return Response({'metric': metric, 'count': 0, 'buckets': [],
                             'my_value': None, 'beats': None})

        lo, hi = vals[0], vals[-1]
        span = max(1, hi - lo)
        step = span / self.BUCKETS
        buckets = [{'lo': round(lo + i * step), 'hi': round(lo + (i + 1) * step), 'count': 0}
                   for i in range(self.BUCKETS)]
        for v in vals:
            idx = min(self.BUCKETS - 1, int((v - lo) / step)) if step else 0
            buckets[idx]['count'] += 1

        my_value, beats = None, None
        if request.user.is_authenticated:
            mine = (Submission.objects
                    .filter(problem_id=pk, user=request.user, status='AC', **{f'{metric}__isnull': False})
                    .values_list(metric, flat=True))
            if mine:
                my_value = min(mine)
                slower = sum(1 for v in vals if v > my_value)
                beats = round(slower / n * 100, 1)

        return Response({
            'metric': metric, 'count': n, 'min': lo, 'max': hi,
            'buckets': buckets, 'my_value': my_value, 'beats': beats,
        })


# ── 每日一题 ────────────────────────────────────────────────────────────────────

class DailyProblemAPIView(APIView):
    """GET /api/daily-problem/  今日推荐题：优先取管理员指定，否则按日期确定性挑一道已发布题。"""
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.localdate()
        dp = DailyProblem.objects.filter(date=today).select_related('problem').first()
        problem = dp.problem if dp else None
        if problem is None:
            pub_ids = list(Problem.objects.filter(is_published=True).order_by('id').values_list('id', flat=True))
            if not pub_ids:
                return Response({'date': str(today), 'problem': None})
            problem = Problem.objects.get(pk=pub_ids[today.toordinal() % len(pub_ids)])

        ac = _has_ac(request.user, problem.id)
        return Response({
            'date': str(today),
            'problem': {
                'id': problem.id,
                'title': problem.title,
                'difficulty': problem.difficulty,
                'ac': ac,
            },
        })
