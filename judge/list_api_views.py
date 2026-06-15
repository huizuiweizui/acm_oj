"""题单 / 训练计划 API。"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProblemList, ProblemListItem, Problem, Submission, Team


def _is_admin(user):
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.role == 'admin')


def _can_view(plist, user):
    if plist.is_public or plist.owner_id == user.id or _is_admin(user):
        return True
    if plist.team_id and plist.team.memberships.filter(user=user).exists():
        return True
    return False


def _can_manage(plist, user):
    return plist.owner_id == user.id or _is_admin(user)


def _list_data(plist, viewer=None, with_items=False):
    qs = plist.items.select_related('problem').order_by('sort_order', 'id')
    items = list(qs) if with_items else None
    pids = [it.problem_id for it in items] if with_items \
        else list(qs.values_list('problem_id', flat=True))

    ac_ids = set()
    if viewer and pids:
        ac_ids = set(Submission.objects.filter(
            user=viewer, status='AC', problem_id__in=pids
        ).values_list('problem_id', flat=True).distinct())

    data = {
        'id': plist.id,
        'title': plist.title,
        'description': plist.description,
        'is_public': plist.is_public,
        'owner_id': plist.owner_id,
        'owner_username': plist.owner.username if plist.owner else '',
        'team_id': plist.team_id,
        'created_at': plist.created_at.isoformat(),
        'updated_at': plist.updated_at.isoformat(),
        'problem_count': len(pids),
        'solved_count': len(ac_ids),
    }
    if with_items:
        data['items'] = [{
            'problem_id': it.problem_id,
            'title': it.problem.title,
            'difficulty': it.problem.difficulty,
            'note': it.note,
            'ac': it.problem_id in ac_ids,
        } for it in items]
    return data


def _set_items(plist, problem_ids):
    plist.items.all().delete()
    for order, pid in enumerate(problem_ids or []):
        if Problem.objects.filter(pk=pid, is_published=True).exists():
            ProblemListItem.objects.get_or_create(
                problem_list=plist, problem_id=pid, defaults={'sort_order': order})


class ProblemListListCreateAPIView(APIView):
    """GET|POST /api/problem-lists/   ?scope=mine|public  ?team=<id>"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get('scope', 'mine')
        team_id = request.query_params.get('team')
        if team_id:
            qs = ProblemList.objects.filter(team_id=team_id)
            is_member = (Team.objects.filter(pk=team_id, memberships__user=request.user).exists()
                         or Team.objects.filter(pk=team_id, creator=request.user).exists())
            if not is_member and not _is_admin(request.user):
                qs = qs.filter(is_public=True)
        elif scope == 'public':
            qs = ProblemList.objects.filter(is_public=True)
        else:
            qs = ProblemList.objects.filter(owner=request.user)
        qs = qs.select_related('owner').prefetch_related('items')[:100]
        return Response([_list_data(p, viewer=request.user) for p in qs])

    def post(self, request):
        title = (request.data.get('title') or '').strip()
        if not title:
            return Response({'detail': '标题不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        team = None
        team_id = request.data.get('team_id')
        if team_id:
            t = Team.objects.filter(pk=team_id).first()
            if t and (t.creator_id == request.user.id or _is_admin(request.user)):
                team = t

        plist = ProblemList.objects.create(
            title=title,
            description=request.data.get('description', '') or '',
            owner=request.user,
            team=team,
            is_public=bool(request.data.get('is_public', True)),
        )
        _set_items(plist, request.data.get('problem_ids', []))
        return Response(_list_data(plist, viewer=request.user, with_items=True),
                        status=status.HTTP_201_CREATED)


class ProblemListDetailAPIView(APIView):
    """GET|PATCH|DELETE /api/problem-lists/<id>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        plist = get_object_or_404(ProblemList.objects.select_related('owner', 'team'), pk=pk)
        if not _can_view(plist, request.user):
            return Response({'detail': '无权访问该题单'}, status=status.HTTP_403_FORBIDDEN)
        data = _list_data(plist, viewer=request.user, with_items=True)
        data['can_manage'] = _can_manage(plist, request.user)
        return Response(data)

    def patch(self, request, pk):
        plist = get_object_or_404(ProblemList, pk=pk)
        if not _can_manage(plist, request.user):
            return Response({'detail': '仅创建者可编辑'}, status=status.HTTP_403_FORBIDDEN)
        if 'title' in request.data:
            plist.title = (request.data['title'] or '').strip() or plist.title
        if 'description' in request.data:
            plist.description = request.data['description'] or ''
        if 'is_public' in request.data:
            plist.is_public = bool(request.data['is_public'])
        plist.save()
        if 'problem_ids' in request.data:
            _set_items(plist, request.data['problem_ids'])
        return Response(_list_data(plist, viewer=request.user, with_items=True))

    def delete(self, request, pk):
        plist = get_object_or_404(ProblemList, pk=pk)
        if not _can_manage(plist, request.user):
            return Response({'detail': '仅创建者可删除'}, status=status.HTTP_403_FORBIDDEN)
        plist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProblemListAddProblemAPIView(APIView):
    """POST /api/problem-lists/<id>/add/  body: {problem_id}  收藏：加入题单。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        plist = get_object_or_404(ProblemList, pk=pk)
        if not _can_manage(plist, request.user):
            return Response({'detail': '仅创建者可添加'}, status=status.HTTP_403_FORBIDDEN)
        pid = request.data.get('problem_id')
        if not Problem.objects.filter(pk=pid, is_published=True).exists():
            return Response({'detail': '题目不存在或未公开'}, status=status.HTTP_404_NOT_FOUND)
        _, created = ProblemListItem.objects.get_or_create(
            problem_list=plist, problem_id=pid, defaults={'sort_order': plist.items.count()})
        return Response({'added': created, 'problem_count': plist.items.count()})
