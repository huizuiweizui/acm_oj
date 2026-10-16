"""团队（班级）相关 API"""
import io
import secrets
from datetime import datetime, time, timedelta
from urllib.parse import quote

import openpyxl
from django.db.models import Count, Max, Min, Q
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Team, TeamMembership, TeamJoinRequest, Submission, Announcement, Assignment, AssignmentProblem, Problem
from .permissions import IsTeacherOrAdmin

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# 不代表有效评测结果的状态：不计入"尝试"，但计入提交数
_NON_RESULT_STATUSES = ('NT', 'Pending', 'Judging')


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _gen_invite_code():
    """生成 8 位唯一邀请码（大写字母+数字）"""
    while True:
        code = secrets.token_hex(4).upper()
        if not Team.objects.filter(invite_code=code).exists():
            return code


def _member_data(ms):
    """序列化单个成员"""
    profile = getattr(ms.user, 'profile', None)
    display = ms.remark or (profile.real_name if profile and profile.real_name else ms.user.username)
    return {
        'user_id': ms.user_id,
        'username': ms.user.username,
        'display_name': display,
        'remark': ms.remark,
        'real_name': profile.real_name if profile else '',
        'student_id': profile.student_id if profile else '',
        'major': profile.major if profile else '',
        'grade': profile.grade if profile else '',
        'role': ms.role,
        'joined_at': ms.joined_at,
        'can_create_contest': profile.can_create_contest if profile else False,
    }


def _team_data(team, include_code=False):
    """序列化团队基本信息"""
    d = {
        'id': team.id,
        'name': team.name,
        'description': team.description,
        'creator_id': team.creator_id,
        'creator_username': team.creator.username,
        'need_review': team.need_review,
        'is_active': team.is_active,
        'created_at': team.created_at,
        'member_count': team.memberships.count(),
        'pending_count': team.join_requests.filter(status='pending').count(),
    }
    if include_code:
        d['invite_code'] = team.invite_code
    return d


def _is_creator_or_admin(user, team):
    return team.creator_id == user.id or getattr(user, 'profile', None) and user.profile.role == 'admin'


def _is_team_viewer(user, team):
    """creator / admin / captain 可查看团队数据"""
    if _is_creator_or_admin(user, team):
        return True
    ms = team.memberships.filter(user=user).first()
    return ms is not None and ms.role == 'captain'


def _is_team_member_or_manager(user, team):
    """团队成员（含队员）或创建者 / 管理员：可看公告、作业、团队内排行"""
    return _is_creator_or_admin(user, team) or team.memberships.filter(user=user).exists()


def _xlsx_response(wb, filename):
    buf = io.BytesIO()
    wb.save(buf)
    resp = HttpResponse(buf.getvalue(), content_type=XLSX_CONTENT_TYPE)
    # RFC 5987：中文文件名需 UTF-8 编码，否则部分浏览器乱码
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return resp


def _ranked(items, key):
    """按 key 降序排序并赋予并列名次（同值同名次，与全站排行榜一致）。"""
    items = sorted(items, key=lambda x: -x[key])
    prev, rank = None, 0
    for i, it in enumerate(items):
        if it[key] != prev:
            rank, prev = i + 1, it[key]
        it['rank'] = rank
    return items


def _team_ac_ranking(team):
    """团队内 AC 排行（实时聚合 Submission，不读冗余字段），返回带 rank 的列表。"""
    memberships = list(team.memberships.select_related('user__profile'))
    ac = dict(
        Submission.objects.filter(user_id__in=[m.user_id for m in memberships], status='AC')
        .values('user_id').annotate(cnt=Count('problem_id', distinct=True))
        .values_list('user_id', 'cnt')
    )
    return _ranked(
        [{'user_id': m.user_id, 'display_name': m.display_name, 'role': m.role,
          'total_ac': ac.get(m.user_id, 0)} for m in memberships],
        'total_ac',
    )


# ── 团队列表 / 创建 ─────────────────────────────────────────────────────────────

class TeamListCreateAPIView(APIView):
    """
    GET  /api/teams/  → 教师：我创建的团队；学生/队长：我加入的团队
    POST /api/teams/  → 教师创建团队
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, 'profile', None) and request.user.profile.role
        if role in ('teacher', 'admin'):
            if role == 'admin':
                teams = Team.objects.all().select_related('creator').order_by('-created_at')
            else:
                teams = Team.objects.filter(creator=request.user).select_related('creator')
            return Response([_team_data(t, include_code=True) for t in teams])
        else:
            memberships = (TeamMembership.objects
                           .filter(user=request.user)
                           .select_related('team__creator'))
            result = []
            for ms in memberships:
                d = _team_data(ms.team)
                d['my_role'] = ms.role
                d['my_remark'] = ms.remark
                me = next((r for r in _team_ac_ranking(ms.team) if r['user_id'] == request.user.id), None)
                d['my_rank'] = me['rank'] if me else None
                d['my_ac'] = me['total_ac'] if me else 0
                result.append(d)
            return Response(result)

    def post(self, request):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'detail': '需要教师权限'}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name', '').strip()
        if not name:
            return Response({'detail': '团队名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        team = Team.objects.create(
            name=name,
            description=request.data.get('description', '').strip(),
            creator=request.user,
            invite_code=_gen_invite_code(),
            need_review=request.data.get('need_review', True),
        )
        return Response(_team_data(team, include_code=True), status=status.HTTP_201_CREATED)


# ── 团队详情 / 编辑 ─────────────────────────────────────────────────────────────

class TeamDetailAPIView(APIView):
    """GET/PATCH /api/teams/:id/"""
    permission_classes = [IsAuthenticated]

    def _get_team(self, pk, user):
        try:
            team = Team.objects.select_related('creator').get(pk=pk)
        except Team.DoesNotExist:
            return None, Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        is_member = team.memberships.filter(user=user).exists()
        if not (is_member or _is_creator_or_admin(user, team)):
            return None, Response({'detail': '无权访问该团队'}, status=status.HTTP_403_FORBIDDEN)
        return team, None

    def get(self, request, pk):
        team, err = self._get_team(pk, request.user)
        if err:
            return err
        is_manager = _is_creator_or_admin(request.user, team)
        data = _team_data(team, include_code=is_manager)
        data['can_manage'] = is_manager
        # 返回当前用户在该团队中的角色
        ms = team.memberships.filter(user=request.user).first()
        data['my_role'] = ms.role if ms else None
        return Response(data)

    def patch(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可编辑团队'}, status=status.HTTP_403_FORBIDDEN)

        for field in ('name', 'description', 'need_review', 'is_active'):
            if field in request.data:
                setattr(team, field, request.data[field])
        team.save()
        return Response(_team_data(team, include_code=True))


# ── 重置邀请码 ──────────────────────────────────────────────────────────────────

class TeamResetCodeAPIView(APIView):
    """POST /api/teams/:id/reset-code/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可重置邀请码'}, status=status.HTTP_403_FORBIDDEN)
        team.invite_code = _gen_invite_code()
        team.save(update_fields=['invite_code'])
        return Response({'invite_code': team.invite_code})


# ── 预览团队（按邀请码）─────────────────────────────────────────────────────────

class TeamPreviewAPIView(APIView):
    """GET /api/teams/preview/?code=XXXXXXXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get('code', '').strip().upper()
        if not code:
            return Response({'detail': '请提供邀请码'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            team = Team.objects.select_related('creator').get(invite_code=code, is_active=True)
        except Team.DoesNotExist:
            return Response({'detail': '邀请码无效或团队已关闭'}, status=status.HTTP_404_NOT_FOUND)

        already_member = team.memberships.filter(user=request.user).exists()
        pending_req = team.join_requests.filter(user=request.user, status='pending').exists()
        return Response({
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'creator_username': team.creator.username,
            'need_review': team.need_review,
            'already_member': already_member,
            'pending_request': pending_req,
        })


# ── 申请加入 ───────────────────────────────────────────────────────────────────

class TeamJoinAPIView(APIView):
    """POST /api/teams/join/  学生申请加入"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('invite_code', '').strip().upper()
        remark = request.data.get('remark', '').strip()

        if not code:
            return Response({'detail': '请提供邀请码'}, status=status.HTTP_400_BAD_REQUEST)
        if not remark:
            return Response({'detail': '备注不能为空，请填写如「2023级 张三」'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            team = Team.objects.get(invite_code=code, is_active=True)
        except Team.DoesNotExist:
            return Response({'detail': '邀请码无效或团队已关闭'}, status=status.HTTP_404_NOT_FOUND)

        if team.memberships.filter(user=request.user).exists():
            return Response({'detail': '你已经是该团队成员'}, status=status.HTTP_400_BAD_REQUEST)

        if team.join_requests.filter(user=request.user, status='pending').exists():
            return Response({'detail': '你已有一条待审核的申请，请等待教师处理'}, status=status.HTTP_400_BAD_REQUEST)

        if not team.need_review:
            TeamMembership.objects.create(team=team, user=request.user, remark=remark)
            return Response({'detail': '加入成功', 'need_review': False}, status=status.HTTP_201_CREATED)
        else:
            TeamJoinRequest.objects.create(team=team, user=request.user, remark=remark)
            return Response({'detail': '申请已提交，等待教师审核', 'need_review': True}, status=status.HTTP_201_CREATED)


# ── 退出团队 ───────────────────────────────────────────────────────────────────

class TeamLeaveAPIView(APIView):
    """DELETE /api/teams/:id/leave/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)

        ms = team.memberships.filter(user=request.user).first()
        if not ms:
            return Response({'detail': '你不是该团队成员'}, status=status.HTTP_400_BAD_REQUEST)
        if ms.role == 'captain':
            return Response({'detail': '队长需先由教师转移身份后才能退出'}, status=status.HTTP_400_BAD_REQUEST)

        ms.delete()
        return Response({'detail': '已退出团队'})


# ── 成员列表 / 管理 ─────────────────────────────────────────────────────────────

class TeamMembersAPIView(APIView):
    """GET /api/teams/:id/members/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not (_is_creator_or_admin(request.user, team) or team.memberships.filter(user=request.user).exists()):
            return Response({'detail': '无权访问'}, status=status.HTTP_403_FORBIDDEN)

        memberships = (team.memberships
                       .select_related('user__profile')
                       .order_by('joined_at'))
        return Response({
            'members': [_member_data(ms) for ms in memberships],
            'can_manage': _is_creator_or_admin(request.user, team),
        })


class TeamMemberDetailAPIView(APIView):
    """
    PATCH  /api/teams/:id/members/:user_id/  → 修改备注 / 设队长
    DELETE /api/teams/:id/members/:user_id/  → 移除成员
    """
    permission_classes = [IsAuthenticated]

    def _get_team_and_check(self, pk, request):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return None, Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return None, Response({'detail': '仅创建者可管理成员'}, status=status.HTTP_403_FORBIDDEN)
        return team, None

    def patch(self, request, pk, user_id):
        team, err = self._get_team_and_check(pk, request)
        if err:
            return err

        ms = team.memberships.filter(user_id=user_id).first()
        if not ms:
            return Response({'detail': '该用户不是团队成员'}, status=status.HTTP_404_NOT_FOUND)

        updated = []
        if 'remark' in request.data:
            ms.remark = request.data['remark'].strip()[:50]
            updated.append('remark')

        if 'role' in request.data:
            new_role = request.data['role']
            if new_role not in ('captain', 'member'):
                return Response({'detail': 'role 只能是 captain 或 member'}, status=status.HTTP_400_BAD_REQUEST)
            if new_role == 'captain':
                team.memberships.filter(role='captain').update(role='member')
            ms.role = new_role
            updated.append('role')

        if updated:
            ms.save(update_fields=updated)
        return Response(_member_data(ms))

    def delete(self, request, pk, user_id):
        team, err = self._get_team_and_check(pk, request)
        if err:
            return err

        if user_id == request.user.id:
            return Response({'detail': '不能移除自己（创建者）'}, status=status.HTTP_400_BAD_REQUEST)

        ms = team.memberships.filter(user_id=user_id).first()
        if not ms:
            return Response({'detail': '该用户不是团队成员'}, status=status.HTTP_404_NOT_FOUND)

        ms.delete()
        return Response({'detail': '已移除'})


# ── 申请列表 / 审核 ─────────────────────────────────────────────────────────────

def _req_data(req):
    profile = getattr(req.user, 'profile', None)
    return {
        'id': req.id,
        'user_id': req.user_id,
        'username': req.user.username,
        'real_name': profile.real_name if profile else '',
        'student_id': profile.student_id if profile else '',
        'remark': req.remark,
        'status': req.status,
        'reject_reason': req.reject_reason,
        'created_at': req.created_at,
        'reviewed_at': req.reviewed_at,
    }


class TeamRequestsAPIView(APIView):
    """GET /api/teams/:id/requests/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可查看申请'}, status=status.HTTP_403_FORBIDDEN)

        filter_status = request.query_params.get('status', 'pending')
        reqs = (team.join_requests
                .filter(status=filter_status)
                .select_related('user__profile')
                .order_by('created_at'))
        return Response([_req_data(r) for r in reqs])


class TeamRequestApproveAPIView(APIView):
    """POST /api/teams/:id/requests/:req_id/approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, req_id):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可审核申请'}, status=status.HTTP_403_FORBIDDEN)

        try:
            req = team.join_requests.select_related('user').get(pk=req_id, status='pending')
        except TeamJoinRequest.DoesNotExist:
            return Response({'detail': '申请不存在或已处理'}, status=status.HTTP_404_NOT_FOUND)

        if team.memberships.filter(user=req.user).exists():
            req.status = 'approved'
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            return Response({'detail': '该用户已是成员，申请已关闭'})

        with transaction.atomic():
            TeamMembership.objects.create(
                team=team,
                user=req.user,
                remark=req.remark,
            )
            req.status = 'approved'
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

        return Response({'detail': '已通过'})


class TeamRequestRejectAPIView(APIView):
    """POST /api/teams/:id/requests/:req_id/reject/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, req_id):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可审核申请'}, status=status.HTTP_403_FORBIDDEN)

        try:
            req = team.join_requests.get(pk=req_id, status='pending')
        except TeamJoinRequest.DoesNotExist:
            return Response({'detail': '申请不存在或已处理'}, status=status.HTTP_404_NOT_FOUND)

        req.status = 'rejected'
        req.reject_reason = request.data.get('reason', '').strip()
        req.reviewed_by = request.user
        req.reviewed_at = timezone.now()
        req.save(update_fields=['status', 'reject_reason', 'reviewed_by', 'reviewed_at'])
        return Response({'detail': '已拒绝'})


# ── 批量通过申请 ────────────────────────────────────────────────────────────────

class TeamRequestBatchApproveAPIView(APIView):
    """POST /api/teams/:id/requests/batch-approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可审核申请'}, status=status.HTTP_403_FORBIDDEN)

        req_ids = request.data.get('ids', [])
        if not req_ids:
            return Response({'detail': '请提供申请 ID 列表'}, status=status.HTTP_400_BAD_REQUEST)

        reqs = team.join_requests.filter(pk__in=req_ids, status='pending').select_related('user')
        success, skip = 0, 0
        now = timezone.now()

        for req in reqs:
            if team.memberships.filter(user=req.user).exists():
                req.status = 'approved'
                req.reviewed_by = request.user
                req.reviewed_at = now
                req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
                skip += 1
                continue
            with transaction.atomic():
                TeamMembership.objects.create(team=team, user=req.user, remark=req.remark)
                req.status = 'approved'
                req.reviewed_by = request.user
                req.reviewed_at = now
                req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            success += 1

        return Response({'success': success, 'already_member': skip})


# ── 我的申请状态（学生）────────────────────────────────────────────────────────

class MyRequestsAPIView(APIView):
    """GET /api/my-requests/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reqs = (TeamJoinRequest.objects
                .filter(user=request.user)
                .select_related('team')
                .order_by('-created_at'))
        result = []
        for r in reqs:
            result.append({
                'id': r.id,
                'team_id': r.team_id,
                'team_name': r.team.name,
                'remark': r.remark,
                'status': r.status,
                'reject_reason': r.reject_reason,
                'created_at': r.created_at,
            })
        return Response(result)


# ── 搜索学生 ───────────────────────────────────────────────────────────────────

class TeamSearchStudentAPIView(APIView):
    """GET /api/teams/:id/search-student/?q=xxx  按用户名或学号搜索"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无权访问'}, status=status.HTTP_403_FORBIDDEN)

        q = request.query_params.get('q', '').strip()
        if not q:
            return Response([])

        from django.db.models import Q
        users = (User.objects
                 .select_related('profile')
                 .filter(Q(username__icontains=q) | Q(profile__student_id__icontains=q))
                 .exclude(pk=request.user.pk)
                 [:20])

        existing_ids = set(team.memberships.values_list('user_id', flat=True))
        result = []
        for u in users:
            p = getattr(u, 'profile', None)
            result.append({
                'user_id': u.id,
                'username': u.username,
                'real_name': p.real_name if p else '',
                'student_id': p.student_id if p else '',
                'major': p.major if p else '',
                'grade': p.grade if p else '',
                'already_member': u.id in existing_ids,
            })
        return Response(result)


# ── 单个直接添加 ────────────────────────────────────────────────────────────────

class TeamAddStudentAPIView(APIView):
    """POST /api/teams/:id/add-student/  教师直接添加学生（无需确认）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可添加成员'}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        remark = request.data.get('remark', '').strip()[:50]

        try:
            target = User.objects.select_related('profile').get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        if team.memberships.filter(user=target).exists():
            return Response({'detail': '该学生已是团队成员'}, status=status.HTTP_400_BAD_REQUEST)

        if not remark:
            p = getattr(target, 'profile', None)
            remark = (p.real_name if p and p.real_name else target.username)[:50]

        ms = TeamMembership.objects.create(team=team, user=target, remark=remark)
        return Response(_member_data(ms), status=status.HTTP_201_CREATED)


# ── Excel 模板下载 ─────────────────────────────────────────────────────────────

class TeamImportTemplateAPIView(APIView):
    """GET /api/teams/:id/import-template/  下载导入模板"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无权下载'}, status=status.HTTP_403_FORBIDDEN)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '学生名单'
        ws.append(['学号', '姓名', '专业', '年级'])
        ws.append(['2023001', '张三', '计算机科学', '2023级'])

        for col, width in zip(['A', 'B', 'C', 'D'], [15, 12, 20, 10]):
            ws.column_dimensions[col].width = width

        return _xlsx_response(wb, f'import_template_{team.id}.xlsx')


# ── Excel 批量导入 ─────────────────────────────────────────────────────────────

class TeamImportStudentsAPIView(APIView):
    """POST /api/teams/:id/import-students/  上传 Excel 批量导入"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return Response({'detail': '团队不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可导入'}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传 Excel 文件'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        except Exception:
            return Response({'detail': '文件格式错误，请上传 .xlsx 文件'}, status=status.HTTP_400_BAD_REQUEST)

        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))

        success, already_member, failed = [], [], []
        seen_ids = set()

        def cell_text(v):
            if v is None:
                return ''
            # Excel 中纯数字学号会被读成 float（2023001.0）
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            return str(v).strip()

        for row_idx, row in enumerate(rows, start=2):
            row = (tuple(row) + (None,) * 4)[:4]
            if all(v is None or str(v).strip() == '' for v in row):
                continue   # 跳过空行
            student_id, name, major, grade = (cell_text(v) for v in row)

            if not student_id:
                failed.append({'row': row_idx, 'reason': '学号为空'})
                continue
            if not name:
                failed.append({'row': row_idx, 'student_id': student_id, 'reason': '姓名为空'})
                continue
            if student_id in seen_ids:
                failed.append({'row': row_idx, 'student_id': student_id, 'reason': '学号在文件内重复'})
                continue
            seen_ids.add(student_id)

            try:
                self._process_row(team, student_id, name, major, grade, success, already_member)
            except Exception as e:
                failed.append({'row': row_idx, 'student_id': student_id, 'reason': str(e)})

        return Response({
            'success': len(success),
            'already_member': len(already_member),
            'failed': len(failed),
            'success_list': success,
            'already_list': already_member,
            'fail_list': failed,
        })

    def _process_row(self, team, student_id, name, major, grade, success, already_member):
        from judge.models import UserProfile

        profile_qs = UserProfile.objects.filter(student_id=student_id).select_related('user')
        if profile_qs.exists():
            profile = profile_qs.first()
            user = profile.user
            update_fields = []
            if major and profile.major != major:
                profile.major = major
                update_fields.append('major')
            if grade and profile.grade != grade:
                profile.grade = grade
                update_fields.append('grade')
            if name and profile.real_name != name:
                profile.real_name = name
                update_fields.append('real_name')
            if update_fields:
                profile.save(update_fields=update_fields)

            if team.memberships.filter(user=user).exists():
                already_member.append({'student_id': student_id, 'username': user.username})
            else:
                TeamMembership.objects.create(team=team, user=user, remark=name[:50])
                success.append({'student_id': student_id, 'username': user.username, 'created': False})
        else:
            if User.objects.filter(username=student_id).exists():
                user = User.objects.get(username=student_id)
                p, _ = UserProfile.objects.get_or_create(user=user)
                p.student_id = student_id
                p.real_name = name
                if major:
                    p.major = major
                if grade:
                    p.grade = grade
                p.must_change_password = True
                p.save()
            else:
                with transaction.atomic():
                    user = User.objects.create_user(username=student_id, password=student_id)
                    UserProfile.objects.create(
                        user=user,
                        student_id=student_id,
                        real_name=name,
                        major=major,
                        grade=grade,
                        role='student',
                        must_change_password=True,
                    )

            if team.memberships.filter(user=user).exists():
                already_member.append({'student_id': student_id, 'username': user.username})
            else:
                TeamMembership.objects.create(team=team, user=user, remark=name[:50])
                success.append({'student_id': student_id, 'username': user.username, 'created': True})


# ── 难度 / 时间范围工具 ────────────────────────────────────────────────────────

# 洛谷 8 级难度，「暂无评定」放最后
DIFF_LEVELS = [d for d, _ in Problem.DIFFICULTY_CHOICES if d != '暂无评定'] + ['暂无评定']


def _parse_time_range(params):
    """
    解析 ?range=all|week|month|custom&start=YYYY-MM-DD&end=YYYY-MM-DD
    week / month 为自然周（周一起）/ 自然月；custom 的 end 含当天。
    返回 (range_name, start_dt|None, end_dt_exclusive|None)。
    """
    rng = params.get('range', 'all')
    tz = timezone.get_current_timezone()
    today = timezone.localdate()

    def at_midnight(d):
        return timezone.make_aware(datetime.combine(d, time.min), tz)

    if rng == 'week':
        return rng, at_midnight(today - timedelta(days=today.weekday())), None
    if rng == 'month':
        return rng, at_midnight(today.replace(day=1)), None
    if rng == 'custom':
        s = parse_date(params.get('start', '') or '')
        e = parse_date(params.get('end', '') or '')
        return rng, (at_midnight(s) if s else None), (at_midnight(e + timedelta(days=1)) if e else None)
    return 'all', None, None


def _filter_range(qs, start, end):
    if start:
        qs = qs.filter(submitted_at__gte=start)
    if end:
        qs = qs.filter(submitted_at__lt=end)
    return qs


def _build_ranking_and_stats(team, memberships, start=None, end=None):
    """
    计算成员排行（各难度去重 AC、总提交、AC 率、最近活跃）及团队汇总。
    全部是按 user / difficulty 分组的聚合查询，查询次数与人数无关。
    """
    member_user_ids = [ms.user_id for ms in memberships]
    base = Submission.objects.filter(user_id__in=member_user_ids)
    ranged = _filter_range(base, start, end)

    # 用户 × 难度 的去重 AC 数
    by_diff = {}
    for row in (ranged.filter(status='AC')
                .values('user_id', 'problem__difficulty')
                .annotate(cnt=Count('problem_id', distinct=True))):
        by_diff.setdefault(row['user_id'], {})[row['problem__difficulty']] = row['cnt']

    # 提交数 / AC 提交数（时间范围内）
    sub_stats = {
        row['user_id']: row for row in
        ranged.values('user_id').annotate(total=Count('id'), ac_subs=Count('id', filter=Q(status='AC')))
    }
    # 最近活跃（不受时间范围影响）
    last_active = dict(base.values('user_id').annotate(last=Max('submitted_at')).values_list('user_id', 'last'))

    # 本周新增 AC：首次 AC 落在本周的 (user, problem)
    _, week_start, _ = _parse_time_range({'range': 'week'})
    week_new = {}
    for row in (base.filter(status='AC').values('user_id', 'problem_id')
                .annotate(first=Min('submitted_at')).filter(first__gte=week_start)):
        week_new[row['user_id']] = week_new.get(row['user_id'], 0) + 1

    ranking = []
    for ms in memberships:
        uid = ms.user_id
        diffs = by_diff.get(uid, {})
        s = sub_stats.get(uid, {'total': 0, 'ac_subs': 0})
        profile = getattr(ms.user, 'profile', None)
        last = last_active.get(uid)
        ranking.append({
            'user_id': uid,
            'display_name': ms.display_name,
            'username': ms.user.username,
            'student_id': profile.student_id if profile else '',
            'role': ms.role,
            'total_ac': sum(diffs.values()),
            'by_diff': {d: diffs.get(d, 0) for d in DIFF_LEVELS},
            'total_submit': s['total'],
            'ac_rate': round(s['ac_subs'] / s['total'] * 100, 1) if s['total'] else 0,
            'week_new_ac': week_new.get(uid, 0),
            'last_active': last.isoformat() if last else None,
        })
    ranking = _ranked(ranking, 'total_ac')

    total_ac = sum(r['total_ac'] for r in ranking)
    distinct_problems = ranged.filter(status='AC').values('problem_id').distinct().count()
    stats = {
        'member_count': len(ranking),
        'total_ac': total_ac,
        'distinct_problems': distinct_problems,
        'week_new_ac': sum(week_new.values()),
        'avg_ac': round(total_ac / len(ranking), 1) if ranking else 0,
        'pending_count': team.join_requests.filter(status='pending').count(),
    }
    return ranking, stats


def _daily_series(qs, days=30):
    """近 days 天每日提交数（submit）与去重 AC 数（count，user×problem×date 去重）。"""
    today = timezone.localdate()
    since = today - timedelta(days=days - 1)
    tz = timezone.get_current_timezone()
    qs = qs.filter(submitted_at__gte=timezone.make_aware(datetime.combine(since, time.min), tz))

    submits = {str(r['d']): r['n'] for r in
               qs.annotate(d=TruncDate('submitted_at')).values('d').annotate(n=Count('id'))}
    ac = {}
    for r in (qs.filter(status='AC').annotate(d=TruncDate('submitted_at'))
              .values('user_id', 'problem_id', 'd').distinct()):
        key = str(r['d'])
        ac[key] = ac.get(key, 0) + 1

    out = []
    for i in range(days):
        d = str(since + timedelta(days=i))
        out.append({'date': d, 'submit': submits.get(d, 0), 'count': ac.get(d, 0)})
    return out


# ── 团队 Dashboard ────────────────────────────────────────────────────────────

class TeamDashboardAPIView(APIView):
    """GET /api/teams/:id/dashboard/?range=all|week|month|custom&start=&end="""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        rng, start, end = _parse_time_range(request.query_params)
        memberships = list(team.memberships.select_related('user', 'user__profile'))
        ranking, stats = _build_ranking_and_stats(team, memberships, start, end)
        trend = _daily_series(Submission.objects.filter(user_id__in=[m.user_id for m in memberships]))

        return Response({
            'team': {'id': team.id, 'name': team.name, 'description': team.description},
            'range': {
                'name': rng,
                'start': timezone.localtime(start).date().isoformat() if start else None,
                'end': (timezone.localtime(end).date() - timedelta(days=1)).isoformat() if end else None,
            },
            'stats': stats,
            'ranking': ranking,
            'trend': trend,
            'diff_levels': DIFF_LEVELS,
            'can_manage': _is_creator_or_admin(request.user, team),
        })


class TeamDashboardExportAPIView(APIView):
    """GET /api/teams/:id/dashboard/export/  按当前筛选条件导出排行 Excel"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        rng, start, end = _parse_time_range(request.query_params)
        memberships = list(team.memberships.select_related('user', 'user__profile'))
        ranking, _ = _build_ranking_and_stats(team, memberships, start, end)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '团队排行'
        headers = ['排名', '备注(姓名)', '用户名', '学号', '角色', '总AC'] + DIFF_LEVELS + \
                  ['总提交', 'AC率(%)', '本周新增AC', '最近活跃']
        ws.append(headers)
        for r in ranking:
            last = ''
            if r['last_active']:
                last = timezone.localtime(datetime.fromisoformat(r['last_active'])).strftime('%Y-%m-%d %H:%M')
            ws.append([
                r['rank'], r['display_name'], r['username'], r['student_id'],
                '队长' if r['role'] == 'captain' else '队员', r['total_ac'],
            ] + [r['by_diff'][d] for d in DIFF_LEVELS] + [
                r['total_submit'], r['ac_rate'], r['week_new_ac'], last,
            ])
        widths = [6, 14, 14, 14, 6, 8] + [11] * len(DIFF_LEVELS) + [8, 9, 11, 17]
        for col_idx, width in enumerate(widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        label = {'all': '全部', 'week': '本周', 'month': '本月', 'custom': '自定义'}[rng]
        return _xlsx_response(wb, f'{team.name}_排行_{label}.xlsx')


# ── 团队内排行（成员视角，只含名次与 AC 数）──────────────────────────────────

class TeamRankAPIView(APIView):
    """GET /api/teams/:id/rank/  任意成员可看，不展示他人明细"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_member_or_manager(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        ranking = _team_ac_ranking(team)
        for r in ranking:
            r['is_me'] = r['user_id'] == request.user.id
        return Response(ranking)


# ── 学生详情 ──────────────────────────────────────────────────────────────────

def _knowledge_points(user):
    """
    知识点（Tag）下钻：每个知识点下列出该生提交过的所有题目。
    一题多 Tag 时在每个 Tag 下都出现；无 Tag 的题归入「未分类」。
    NT / Pending / Judging 不算有效尝试（只计入提交次数）。
    排序：未 AC 比例高的知识点在前（教学上最需要关注）。
    """
    per_problem = {}
    for s in (Submission.objects.filter(user=user)
              .order_by('submitted_at').values('problem_id', 'status')):
        p = per_problem.setdefault(s['problem_id'], {
            'submit_count': 0, 'ac': False, 'submits_to_ac': None, 'last_status': None,
        })
        p['submit_count'] += 1
        if s['status'] in _NON_RESULT_STATUSES:
            continue
        p['last_status'] = s['status']
        if s['status'] == 'AC' and not p['ac']:
            p['ac'] = True
            p['submits_to_ac'] = p['submit_count']

    tried_ids = [pid for pid, p in per_problem.items() if p['last_status'] is not None]
    problems = Problem.objects.filter(id__in=tried_ids).prefetch_related('tags')

    tags = {}
    for prob in problems:
        info = per_problem[prob.id]
        item = {
            'problem_id': prob.id,
            'title': prob.title,
            'difficulty': prob.difficulty,
            'submit_count': info['submit_count'],
            'ac': info['ac'],
            'submits_to_ac': info['submits_to_ac'],
            'last_status': info['last_status'],
        }
        for name in ([t.name for t in prob.tags.all()] or ['未分类']):
            tags.setdefault(name, []).append(item)

    result = []
    for name, items in tags.items():
        items.sort(key=lambda x: (x['ac'], x['problem_id']))   # 未 AC 的排前面
        ac = sum(1 for x in items if x['ac'])
        result.append({
            'tag': name,
            'ac_count': ac,
            'tried_count': len(items),
            'unsolved_ratio': round((len(items) - ac) / len(items), 3),
            'problems': items,
        })
    result.sort(key=lambda t: (-t['unsolved_ratio'], -t['tried_count'], t['tag']))
    return result


class TeamStudentDetailAPIView(APIView):
    """GET /api/teams/:teamId/students/:userId/
    返回该学生在这个团队中的完整学习数据。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, user_id):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        try:
            ms = team.memberships.select_related('user', 'user__profile').get(user_id=user_id)
        except TeamMembership.DoesNotExist:
            return Response({'detail': '该学生不在此团队'}, status=status.HTTP_404_NOT_FOUND)

        user = ms.user
        subs = Submission.objects.filter(user=user)

        # 难度分布（去重 AC）
        diff_counts = dict(
            subs.filter(status='AC').values('problem__difficulty')
            .annotate(cnt=Count('problem_id', distinct=True))
            .values_list('problem__difficulty', 'cnt')
        )
        diff_dist = [{'level': d, 'count': diff_counts.get(d, 0)} for d in DIFF_LEVELS]

        # 近 365 天每日提交数（热力图）
        today = timezone.localdate()
        tz = timezone.get_current_timezone()
        year_ago = timezone.make_aware(datetime.combine(today - timedelta(days=364), time.min), tz)
        heatmap = {
            str(r['d']): r['n'] for r in
            subs.filter(submitted_at__gte=year_ago).annotate(d=TruncDate('submitted_at'))
            .values('d').annotate(n=Count('id'))
        }

        # 已 AC 题目（按首次 AC 时间倒序，最近 50 道）
        first_ac = (
            subs.filter(status='AC')
            .values('problem_id', 'problem__title', 'problem__difficulty')
            .annotate(first_ac_at=Min('submitted_at'))
            .order_by('-first_ac_at')[:50]
        )

        profile = getattr(user, 'profile', None)
        total_submit = subs.count()
        ac_subs = subs.filter(status='AC').count()
        knowledge = _knowledge_points(user)

        return Response({
            'member': {
                'user_id': user.id,
                'username': user.username,
                'display_name': ms.display_name,
                'real_name': profile.real_name if profile else '',
                'student_id': profile.student_id if profile else '',
                'major': profile.major if profile else '',
                'grade': profile.grade if profile else '',
                'role': ms.role,
                'joined_at': ms.joined_at.isoformat(),
                'total_ac': sum(diff_counts.values()),
                'total_submit': total_submit,
                'ac_rate': round(ac_subs / total_submit * 100, 1) if total_submit else 0,
                'tried_count': len({p['problem_id'] for k in knowledge for p in k['problems']}),
            },
            'diff_dist': diff_dist,
            'trend': _daily_series(subs),
            'heatmap': heatmap,
            'knowledge': knowledge,
            'ac_problems': [
                {
                    'problem_id': r['problem_id'],
                    'title': r['problem__title'],
                    'difficulty': r['problem__difficulty'],
                    'first_ac_at': r['first_ac_at'].isoformat() if r['first_ac_at'] else None,
                }
                for r in first_ac
            ],
            'can_manage': _is_creator_or_admin(request.user, team),
        })


# ── 公告 ─────────────────────────────────────────────────────────────────────

def _announcement_data(a):
    return {
        'id': a.id,
        'title': a.title,
        'content': a.content,
        'is_pinned': a.is_pinned,
        'created_by': a.created_by.username if a.created_by else '',
        'created_at': a.created_at.isoformat(),
        'updated_at': a.updated_at.isoformat(),
    }


class AnnouncementListCreateAPIView(APIView):
    """GET|POST /api/teams/:id/announcements/  成员可看，仅创建者可发"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_member_or_manager(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        announcements = team.announcements.select_related('created_by').all()
        return Response([_announcement_data(a) for a in announcements])

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可发公告'}, status=status.HTTP_403_FORBIDDEN)
        title = request.data.get('title', '').strip()
        if not title:
            return Response({'detail': '标题不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        a = Announcement.objects.create(
            team=team,
            title=title[:200],
            content=request.data.get('content', ''),
            is_pinned=bool(request.data.get('is_pinned', False)),
            created_by=request.user,
        )
        return Response(_announcement_data(a), status=status.HTTP_201_CREATED)


class AnnouncementDetailAPIView(APIView):
    """GET|PATCH|DELETE /api/teams/:id/announcements/:aid/"""
    permission_classes = [IsAuthenticated]

    def _get_obj(self, pk, aid, user):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_member_or_manager(user, team):
            return None, None, Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        try:
            a = team.announcements.select_related('created_by').get(pk=aid)
        except Announcement.DoesNotExist:
            return None, None, Response({'detail': '公告不存在'}, status=status.HTTP_404_NOT_FOUND)
        return team, a, None

    def get(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        return Response(_announcement_data(a))

    def patch(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无编辑权限'}, status=status.HTTP_403_FORBIDDEN)
        if 'title' in request.data:
            a.title = request.data['title'].strip()[:200] or a.title
        if 'content' in request.data:
            a.content = request.data['content']
        if 'is_pinned' in request.data:
            a.is_pinned = bool(request.data['is_pinned'])
        a.save()
        return Response(_announcement_data(a))

    def delete(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无删除权限'}, status=status.HTTP_403_FORBIDDEN)
        a.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── 作业 ─────────────────────────────────────────────────────────────────────
#
# 完成判定（不建冗余表，实时判定）：
#   ontime —— 在 [start_at, deadline] 时间窗内有 AC 提交（未设置的一端视为不限）
#   late   —— 只有窗口外的 AC（补交完成）
#   tried  —— 有提交但没有 AC
#   none   —— 没有提交

def _problem_states(assignment, user_ids, problem_ids):
    """返回 {(user_id, problem_id): {'state': ..., 'attempts': n}}，两次聚合查询完成。"""
    if not user_ids or not problem_ids:
        return {}
    subs = Submission.objects.filter(user_id__in=user_ids, problem_id__in=problem_ids)
    attempts = {
        (r['user_id'], r['problem_id']): r['n']
        for r in subs.values('user_id', 'problem_id').annotate(n=Count('id'))
    }
    in_window = subs.filter(status='AC')
    if assignment.start_at:
        in_window = in_window.filter(submitted_at__gte=assignment.start_at)
    if assignment.deadline:
        in_window = in_window.filter(submitted_at__lte=assignment.deadline)
    ontime = set(in_window.values_list('user_id', 'problem_id').distinct())
    any_ac = set(subs.filter(status='AC').values_list('user_id', 'problem_id').distinct())

    result = {}
    for key, n in attempts.items():
        if key in ontime:
            state = 'ontime'
        elif key in any_ac:
            state = 'late'
        else:
            state = 'tried'
        result[key] = {'state': state, 'attempts': n}
    return result


def _assignment_data(assignment, user=None):
    """序列化作业；传入 user 时附带该用户每题的完成状态。"""
    problems = list(assignment.problems.select_related('problem').order_by('sort_order', 'id'))
    states = {}
    if user is not None:
        states = _problem_states(assignment, [user.id], [ap.problem_id for ap in problems])

    def prob_item(ap):
        st = states.get((user.id, ap.problem_id)) if user is not None else None
        state = st['state'] if st else 'none'
        return {
            'id': ap.problem_id,
            'title': ap.problem.title,
            'difficulty': ap.problem.difficulty,
            'state': state,
            'attempts': st['attempts'] if st else 0,
            'ac': state in ('ontime', 'late'),
        }

    return {
        'id': assignment.id,
        'title': assignment.title,
        'description': assignment.description,
        'start_at': assignment.start_at.isoformat() if assignment.start_at else None,
        'deadline': assignment.deadline.isoformat() if assignment.deadline else None,
        'is_active': assignment.is_active,
        'created_by': assignment.created_by.username if assignment.created_by else '',
        'created_at': assignment.created_at.isoformat(),
        'problem_count': len(problems),
        'problems': [prob_item(ap) for ap in problems],
    }


def _parse_assignment_times(data, current=None):
    """解析 start_at / deadline，返回 (start_at, deadline, error_msg)。"""
    def parse(key):
        if key not in data:
            return getattr(current, key, None) if current else None
        raw = data.get(key)
        if not raw:
            return None
        dt = parse_datetime(raw)
        if dt is not None and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    start_at, deadline = parse('start_at'), parse('deadline')
    if data.get('start_at') and start_at is None:
        return None, None, '开始时间格式错误'
    if data.get('deadline') and deadline is None:
        return None, None, '截止时间格式错误'
    if start_at and deadline and deadline <= start_at:
        return None, None, '截止时间必须晚于开始时间'
    return start_at, deadline, None


def _set_assignment_problems(assignment, problem_ids):
    assignment.problems.all().delete()
    published = set(Problem.objects.filter(pk__in=problem_ids, is_published=True).values_list('id', flat=True))
    seen = set()
    for order, pid in enumerate(problem_ids):
        if pid in published and pid not in seen:
            seen.add(pid)
            AssignmentProblem.objects.create(assignment=assignment, problem_id=pid, sort_order=order)


class AssignmentListCreateAPIView(APIView):
    """GET|POST /api/teams/:id/assignments/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_member_or_manager(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        assignments = team.assignments.select_related('created_by').prefetch_related('problems__problem')
        # 草稿只有创建者 / 管理员可见；成员（含队长）看到已发布作业及自己的完成状态
        is_manager = _is_creator_or_admin(request.user, team)
        if not is_manager:
            assignments = assignments.filter(is_active=True)
        user_for_state = None if is_manager else request.user
        return Response([_assignment_data(a, user_for_state) for a in assignments])

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可创建作业'}, status=status.HTTP_403_FORBIDDEN)
        title = request.data.get('title', '').strip()
        if not title:
            return Response({'detail': '作业名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        start_at, deadline, err = _parse_assignment_times(request.data)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            assignment = Assignment.objects.create(
                team=team,
                title=title[:200],
                description=request.data.get('description', ''),
                start_at=start_at,
                deadline=deadline,
                is_active=bool(request.data.get('is_active', True)),
                created_by=request.user,
            )
            _set_assignment_problems(assignment, request.data.get('problem_ids', []))
        return Response(_assignment_data(assignment), status=status.HTTP_201_CREATED)


class AssignmentDetailAPIView(APIView):
    """GET|PATCH|DELETE /api/teams/:id/assignments/:aid/"""
    permission_classes = [IsAuthenticated]

    def _get_obj(self, pk, aid, user):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_member_or_manager(user, team):
            return None, None, Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        qs = team.assignments.select_related('created_by').prefetch_related('problems__problem')
        if not _is_creator_or_admin(user, team):
            qs = qs.filter(is_active=True)
        try:
            a = qs.get(pk=aid)
        except Assignment.DoesNotExist:
            return None, None, Response({'detail': '作业不存在'}, status=status.HTTP_404_NOT_FOUND)
        return team, a, None

    def get(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        is_manager = _is_creator_or_admin(request.user, team)
        return Response(_assignment_data(a, None if is_manager else request.user))

    def patch(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无编辑权限'}, status=status.HTTP_403_FORBIDDEN)
        start_at, deadline, time_err = _parse_assignment_times(request.data, current=a)
        if time_err:
            return Response({'detail': time_err}, status=status.HTTP_400_BAD_REQUEST)

        if 'title' in request.data:
            a.title = request.data['title'].strip()[:200] or a.title
        if 'description' in request.data:
            a.description = request.data['description']
        if 'is_active' in request.data:
            a.is_active = bool(request.data['is_active'])
        a.start_at, a.deadline = start_at, deadline
        with transaction.atomic():
            a.save()
            if 'problem_ids' in request.data:
                _set_assignment_problems(a, request.data['problem_ids'])
        return Response(_assignment_data(a))

    def delete(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无删除权限'}, status=status.HTTP_403_FORBIDDEN)
        a.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _assignment_matrix(team, assignment):
    """作业完成矩阵：行 = 学生（按完成数降序），列 = 题目。"""
    problems = list(assignment.problems.select_related('problem').order_by('sort_order', 'id'))
    memberships = list(team.memberships.select_related('user', 'user__profile'))
    pids = [ap.problem_id for ap in problems]
    states = _problem_states(assignment, [m.user_id for m in memberships], pids)

    rows = []
    for ms in memberships:
        cells = []
        ontime = late = 0
        for pid in pids:
            st = states.get((ms.user_id, pid), {'state': 'none', 'attempts': 0})
            ontime += st['state'] == 'ontime'
            late += st['state'] == 'late'
            cells.append(st)
        profile = getattr(ms.user, 'profile', None)
        rows.append({
            'user_id': ms.user_id,
            'display_name': ms.display_name,
            'student_id': profile.student_id if profile else '',
            'role': ms.role,
            'ontime': ontime,
            'late': late,
            'done': ontime + late,
            'cells': cells,
        })
    rows.sort(key=lambda r: (-r['done'], -r['ontime'], r['display_name']))

    columns = []
    for i, ap in enumerate(problems):
        done = sum(1 for r in rows if r['cells'][i]['state'] in ('ontime', 'late'))
        columns.append({
            'id': ap.problem_id,
            'title': ap.problem.title,
            'difficulty': ap.problem.difficulty,
            'done_count': done,
        })
    return columns, rows


class AssignmentMatrixAPIView(APIView):
    """GET /api/teams/:id/assignments/:aid/matrix/  创建者 / 管理员 / 队长（只读）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, aid):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        assignment = get_object_or_404(team.assignments.select_related('created_by'), pk=aid)
        columns, rows = _assignment_matrix(team, assignment)
        return Response({
            'team': {'id': team.id, 'name': team.name},
            'assignment': _assignment_data(assignment),
            'columns': columns,
            'rows': rows,
            'can_manage': _is_creator_or_admin(request.user, team),
        })


class AssignmentMatrixExportAPIView(APIView):
    """GET /api/teams/:id/assignments/:aid/matrix/export/"""
    permission_classes = [IsAuthenticated]

    STATE_TEXT = {'ontime': '✅', 'late': '🕐补交', 'none': '❌'}

    def get(self, request, pk, aid):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        assignment = get_object_or_404(team.assignments, pk=aid)
        columns, rows = _assignment_matrix(team, assignment)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '完成情况'
        ws.append(['备注(姓名)', '学号', '按时完成', '补交', '合计'] +
                  [f'#{c["id"]} {c["title"]}' for c in columns])
        for r in rows:
            cells = []
            for c in r['cells']:
                if c['state'] == 'tried':
                    cells.append(f'❌ 尝试{c["attempts"]}次')
                else:
                    cells.append(self.STATE_TEXT[c['state']])
            ws.append([r['display_name'], r['student_id'], r['ontime'], r['late'], r['done']] + cells)
        ws.append(['完成人数', '', '', '', ''] + [c['done_count'] for c in columns])

        for col_idx, width in enumerate([14, 14, 9, 7, 7] + [16] * len(columns), start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width
        return _xlsx_response(wb, f'{team.name}_{assignment.title}_完成情况.xlsx')
