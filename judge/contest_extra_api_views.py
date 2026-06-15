"""补题 / 虚拟参赛 API。"""
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Contest, ContestProblem, Submission, VirtualParticipation


# ── 补题：赛中 / 赛后 / 未解 ────────────────────────────────────────────────────

class ContestMyProgressAPIView(APIView):
    """GET /api/contests/<pk>/my-progress/  当前用户对该比赛各题的解决状态。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        contest = get_object_or_404(Contest, pk=pk)
        cps = list(ContestProblem.objects.filter(contest=contest)
                   .select_related('problem').order_by('sort_order'))
        pids = [cp.problem_id for cp in cps]

        in_contest = set(Submission.objects.filter(
            contest=contest, user=request.user, status='AC', problem_id__in=pids
        ).values_list('problem_id', flat=True))
        any_ac = set(Submission.objects.filter(
            user=request.user, status='AC', problem_id__in=pids
        ).values_list('problem_id', flat=True))

        items = []
        for cp in cps:
            pid = cp.problem_id
            state = 'in_contest' if pid in in_contest else ('upsolved' if pid in any_ac else 'unsolved')
            items.append({
                'problem_id': pid, 'label': cp.label, 'title': cp.problem.title,
                'difficulty': cp.problem.difficulty, 'state': state,
            })
        return Response({
            'problems': items,
            'in_contest_count': sum(1 for i in items if i['state'] == 'in_contest'),
            'upsolved_count': sum(1 for i in items if i['state'] == 'upsolved'),
        })


# ── 虚拟参赛 ────────────────────────────────────────────────────────────────────

def _virtual_data(contest, vp, with_progress=False):
    duration = int((contest.end_time - contest.start_time).total_seconds())
    deadline = vp.started_at + timedelta(seconds=duration)
    now = timezone.now()
    data = {
        'started': True,
        'started_at': vp.started_at.isoformat(),
        'duration_seconds': duration,
        'deadline': deadline.isoformat(),
        'server_now': now.isoformat(),
        'ended': now >= deadline,
    }
    if with_progress:
        cps = list(ContestProblem.objects.filter(contest=contest)
                   .select_related('problem').order_by('sort_order'))
        pids = [cp.problem_id for cp in cps]
        # 个人窗口 [started_at, min(now, deadline)] 内的 AC 计为虚拟通过
        ac = set(Submission.objects.filter(
            user=vp.user, problem_id__in=pids, status='AC',
            submitted_at__gte=vp.started_at, submitted_at__lte=min(now, deadline),
        ).values_list('problem_id', flat=True))
        data['problems'] = [{
            'problem_id': cp.problem_id, 'label': cp.label, 'title': cp.problem.title,
            'difficulty': cp.problem.difficulty, 'ac': cp.problem_id in ac,
        } for cp in cps]
        data['solved'] = len(ac)
    return data


class ContestVirtualStartAPIView(APIView):
    """POST /api/contests/<pk>/virtual-start/  开始虚拟参赛（仅赛后）。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        contest = get_object_or_404(Contest, pk=pk)
        if contest.status != 'ended':
            return Response({'detail': '比赛结束后才能虚拟参赛'}, status=status.HTTP_400_BAD_REQUEST)
        vp, created = VirtualParticipation.objects.get_or_create(contest=contest, user=request.user)
        return Response(_virtual_data(contest, vp),
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ContestVirtualStatusAPIView(APIView):
    """GET /api/contests/<pk>/virtual-status/  虚拟参赛进度（个人计时）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        contest = get_object_or_404(Contest, pk=pk)
        vp = VirtualParticipation.objects.filter(contest=contest, user=request.user).first()
        if not vp:
            return Response({'started': False})
        return Response(_virtual_data(contest, vp, with_progress=True))
