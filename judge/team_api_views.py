"""团队（班级）相关 API"""
import io
import secrets
from datetime import timedelta

import openpyxl
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db import models as django_models
from .models import Team, TeamMembership, TeamJoinRequest, Submission, Announcement, Assignment, AssignmentProblem, Problem
from .permissions import IsTeacherOrAdmin


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

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        resp = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = f'attachment; filename="import_template_{team.id}.xlsx"'
        return resp


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

        for row_idx, row in enumerate(rows, start=2):
            student_id = str(row[0]).strip() if row[0] is not None else ''
            name = str(row[1]).strip() if row[1] is not None else ''
            major = str(row[2]).strip() if row[2] is not None else ''
            grade = str(row[3]).strip() if row[3] is not None else ''

            if not student_id or student_id == 'None':
                failed.append({'row': row_idx, 'reason': '学号为空'})
                continue
            if not name or name == 'None':
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


# ── 难度分组工具 ──────────────────────────────────────────────────────────────

_DIFF_GROUP = {
    '入门': '入门',
    '普及-': '普及',
    '普及/提高-': '普及',
    '普及+/提高': '普及',
    '提高+/省选-': '提高',
    '省选/NOI-': '提高',
    'NOI/NOI+/CTSC': 'NOI',
    '暂无评定': '其他',
}
DIFF_ORDER = ['入门', '普及', '提高', 'NOI', '其他']


def _group_difficulty(raw):
    return _DIFF_GROUP.get(raw, '其他')


def _build_ranking_and_stats(team, member_user_ids, memberships):
    """计算成员排行、各难度 AC 数及团队汇总统计，返回 (ranking, stats_dict)。"""
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # 全量 distinct AC（user, problem, difficulty）
    all_ac = list(
        Submission.objects.filter(
            user_id__in=member_user_ids,
            status='AC',
        ).values('user_id', 'problem_id', 'problem__difficulty').distinct()
    )

    # 近 7 天 AC 的 (user_id, problem_id) 集合
    week_pairs = set(
        Submission.objects.filter(
            user_id__in=member_user_ids,
            status='AC',
            submitted_at__gte=week_ago,
        ).values_list('user_id', 'problem_id').distinct()
    )

    # 近 30 天 AC 的 (user_id, problem_id) 集合
    month_pairs = set(
        Submission.objects.filter(
            user_id__in=member_user_ids,
            status='AC',
            submitted_at__gte=month_ago,
        ).values_list('user_id', 'problem_id').distinct()
    )

    # 初始化每位成员的统计桶
    user_stats = {uid: {'total': 0, 'week': 0, 'month': 0, 'by_group': {}} for uid in member_user_ids}

    for row in all_ac:
        uid = row['user_id']
        group = _group_difficulty(row['problem__difficulty'])
        s = user_stats[uid]
        s['total'] += 1
        s['by_group'][group] = s['by_group'].get(group, 0) + 1

    for uid, pid in week_pairs:
        if uid in user_stats:
            user_stats[uid]['week'] += 1

    for uid, pid in month_pairs:
        if uid in user_stats:
            user_stats[uid]['month'] += 1

    ms_map = {ms.user_id: ms for ms in memberships}
    ranking = []
    for uid in member_user_ids:
        ms = ms_map.get(uid)
        if not ms:
            continue
        s = user_stats[uid]
        try:
            profile = ms.user.profile
        except Exception:
            profile = None
        ranking.append({
            'user_id': uid,
            'display_name': ms.display_name,
            'username': ms.user.username,
            'student_id': profile.student_id if profile else '',
            'role': ms.role,
            'total_ac': s['total'],
            'week_ac': s['week'],
            'month_ac': s['month'],
            'by_group': s['by_group'],
        })

    ranking.sort(key=lambda x: -x['total_ac'])

    total_ac = sum(r['total_ac'] for r in ranking)
    team_week_ac = sum(r['week_ac'] for r in ranking)
    avg_ac = round(total_ac / len(ranking), 1) if ranking else 0
    pending_count = team.join_requests.filter(status='pending').count()

    stats = {
        'member_count': len(member_user_ids),
        'total_ac': total_ac,
        'week_ac': team_week_ac,
        'avg_ac': avg_ac,
        'pending_count': pending_count,
    }
    return ranking, stats


def _build_trend(member_user_ids):
    """计算近 30 天每日 AC 数（去重 user×problem×date）。"""
    now = timezone.now()
    since_date = (now - timedelta(days=30)).date()

    rows = list(
        Submission.objects.filter(
            user_id__in=member_user_ids,
            status='AC',
            submitted_at__date__gte=since_date,
        ).annotate(sub_date=TruncDate('submitted_at'))
        .values('user_id', 'problem_id', 'sub_date').distinct()
    )

    trend_map = {}
    for row in rows:
        d = str(row['sub_date'])
        trend_map[d] = trend_map.get(d, 0) + 1

    trend = []
    for i in range(30):
        d = (now - timedelta(days=29 - i)).date()
        trend.append({'date': str(d), 'count': trend_map.get(str(d), 0)})
    return trend


# ── 团队 Dashboard ────────────────────────────────────────────────────────────

class TeamDashboardAPIView(APIView):
    """GET /api/teams/:id/dashboard/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        memberships = list(team.memberships.select_related('user', 'user__profile').all())
        member_user_ids = [ms.user_id for ms in memberships]

        ranking, stats = _build_ranking_and_stats(team, member_user_ids, memberships)
        trend = _build_trend(member_user_ids)

        return Response({
            'team': {'id': team.id, 'name': team.name, 'description': team.description},
            'stats': stats,
            'ranking': ranking,
            'trend': trend,
            'diff_order': DIFF_ORDER,
            'can_manage': _is_creator_or_admin(request.user, team),
        })


class TeamDashboardExportAPIView(APIView):
    """GET /api/teams/:id/dashboard/export/  下载排行 Excel"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        memberships = list(team.memberships.select_related('user', 'user__profile').all())
        member_user_ids = [ms.user_id for ms in memberships]
        ranking, stats = _build_ranking_and_stats(team, member_user_ids, memberships)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '团队排行'

        headers = ['排名', '姓名', '用户名', '学号', '角色',
                   '总AC', '本周AC', '本月AC'] + DIFF_ORDER
        ws.append(headers)

        for i, r in enumerate(ranking, start=1):
            row = [
                i,
                r['display_name'],
                r['username'],
                r['student_id'],
                '队长' if r['role'] == 'captain' else '队员',
                r['total_ac'],
                r['week_ac'],
                r['month_ac'],
            ] + [r['by_group'].get(g, 0) for g in DIFF_ORDER]
            ws.append(row)

        for col_idx, width in zip(range(1, len(headers) + 1),
                                   [6, 12, 12, 12, 6, 8, 8, 8] + [8] * len(DIFF_ORDER)):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        resp = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = f'attachment; filename="{team.name}_ranking.xlsx"'
        return resp


# ── 学生详情 ──────────────────────────────────────────────────────────────────

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
        now = timezone.now()

        # 所有 AC 的 (problem_id, difficulty)，去重
        all_ac = list(
            Submission.objects.filter(user=user, status='AC')
            .values('problem_id', 'problem__difficulty', 'problem__title').distinct()
        )

        # 难度分组统计
        group_counts = {}
        for row in all_ac:
            g = _group_difficulty(row['problem__difficulty'])
            group_counts[g] = group_counts.get(g, 0) + 1

        diff_dist = [{'group': g, 'count': group_counts.get(g, 0)} for g in DIFF_ORDER]

        # 近 30 天每日 AC（去重 problem × date）
        since_date = (now - timedelta(days=30)).date()
        trend_rows = list(
            Submission.objects.filter(
                user=user,
                status='AC',
                submitted_at__date__gte=since_date,
            ).annotate(sub_date=TruncDate('submitted_at'))
            .values('problem_id', 'sub_date').distinct()
        )
        trend_map = {}
        for row in trend_rows:
            d = str(row['sub_date'])
            trend_map[d] = trend_map.get(d, 0) + 1

        trend = []
        for i in range(30):
            d = (now - timedelta(days=29 - i)).date()
            trend.append({'date': str(d), 'count': trend_map.get(str(d), 0)})

        # 近 365 天热力图（每日 AC 去重）
        year_ago = (now - timedelta(days=364)).date()
        heatmap_rows = list(
            Submission.objects.filter(
                user=user,
                status='AC',
                submitted_at__date__gte=year_ago,
            ).annotate(sub_date=TruncDate('submitted_at'))
            .values('problem_id', 'sub_date').distinct()
        )
        heatmap_map = {}
        for row in heatmap_rows:
            d = str(row['sub_date'])
            heatmap_map[d] = heatmap_map.get(d, 0) + 1

        # 已 AC 题目列表（最近 50 道，按首次 AC 时间倒序）
        # 找每道题最早的 AC 时间
        first_ac = (
            Submission.objects.filter(user=user, status='AC')
            .values('problem_id', 'problem__title', 'problem__difficulty')
            .annotate(first_ac_at=django_models.Min('submitted_at'))
            .order_by('-first_ac_at')[:50]
        )

        try:
            profile = user.profile
        except Exception:
            profile = None

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
                'total_ac': len(all_ac),
                'total_submit': Submission.objects.filter(user=user).count(),
            },
            'diff_dist': diff_dist,
            'trend': trend,
            'heatmap': heatmap_map,
            'ac_problems': [
                {
                    'problem_id': r['problem_id'],
                    'title': r['problem__title'],
                    'difficulty': r['problem__difficulty'],
                    'first_ac_at': r['first_ac_at'].isoformat() if r['first_ac_at'] else None,
                }
                for r in first_ac
            ],
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
    """GET|POST /api/teams/:id/announcements/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
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
            title=title,
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
        if not _is_team_viewer(user, team):
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
            a.title = request.data['title'].strip() or a.title
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

def _assignment_data(assignment, user=None):
    """序列化作业，可选附带当前用户的 AC 状态。"""
    problems = list(
        assignment.problems.select_related('problem').order_by('sort_order', 'id')
    )
    # 若提供 user，计算 AC 集合
    ac_set = set()
    if user:
        pids = [ap.problem_id for ap in problems]
        if pids:
            ac_set = set(
                Submission.objects.filter(
                    user=user, status='AC', problem_id__in=pids
                ).values_list('problem_id', flat=True).distinct()
            )

    return {
        'id': assignment.id,
        'title': assignment.title,
        'description': assignment.description,
        'deadline': assignment.deadline.isoformat() if assignment.deadline else None,
        'is_active': assignment.is_active,
        'created_by': assignment.created_by.username if assignment.created_by else '',
        'created_at': assignment.created_at.isoformat(),
        'problem_count': len(problems),
        'problems': [
            {
                'id': ap.problem_id,
                'title': ap.problem.title,
                'difficulty': ap.problem.difficulty,
                'ac': ap.problem_id in ac_set,
            }
            for ap in problems
        ],
    }


class AssignmentListCreateAPIView(APIView):
    """GET|POST /api/teams/:id/assignments/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(request.user, team):
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        assignments = team.assignments.filter(is_active=True).select_related('created_by').prefetch_related('problems__problem')
        # 教师看到全部，学生也看 is_active=True
        is_teacher = _is_creator_or_admin(request.user, team)
        if is_teacher:
            assignments = team.assignments.select_related('created_by').prefetch_related('problems__problem')
        user_for_ac = None if is_teacher else request.user
        return Response([_assignment_data(a, user_for_ac) for a in assignments])

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '仅创建者可创建作业'}, status=status.HTTP_403_FORBIDDEN)
        title = request.data.get('title', '').strip()
        if not title:
            return Response({'detail': '作业名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        deadline_raw = request.data.get('deadline')
        deadline = None
        if deadline_raw:
            from django.utils.dateparse import parse_datetime
            deadline = parse_datetime(deadline_raw)

        assignment = Assignment.objects.create(
            team=team,
            title=title,
            description=request.data.get('description', ''),
            deadline=deadline,
            is_active=bool(request.data.get('is_active', True)),
            created_by=request.user,
        )
        problem_ids = request.data.get('problem_ids', [])
        for order, pid in enumerate(problem_ids):
            if Problem.objects.filter(pk=pid, is_published=True).exists():
                AssignmentProblem.objects.get_or_create(
                    assignment=assignment, problem_id=pid,
                    defaults={'sort_order': order},
                )
        return Response(_assignment_data(assignment), status=status.HTTP_201_CREATED)


class AssignmentDetailAPIView(APIView):
    """GET|PATCH|DELETE /api/teams/:id/assignments/:aid/"""
    permission_classes = [IsAuthenticated]

    def _get_obj(self, pk, aid, user):
        team = get_object_or_404(Team, pk=pk)
        if not _is_team_viewer(user, team):
            return None, None, Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        try:
            a = team.assignments.select_related('created_by').prefetch_related('problems__problem').get(pk=aid)
        except Assignment.DoesNotExist:
            return None, None, Response({'detail': '作业不存在'}, status=status.HTTP_404_NOT_FOUND)
        return team, a, None

    def get(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        is_teacher = _is_creator_or_admin(request.user, team)
        return Response(_assignment_data(a, None if is_teacher else request.user))

    def patch(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无编辑权限'}, status=status.HTTP_403_FORBIDDEN)
        if 'title' in request.data:
            a.title = request.data['title'].strip() or a.title
        if 'description' in request.data:
            a.description = request.data['description']
        if 'is_active' in request.data:
            a.is_active = bool(request.data['is_active'])
        if 'deadline' in request.data:
            from django.utils.dateparse import parse_datetime
            a.deadline = parse_datetime(request.data['deadline']) if request.data['deadline'] else None
        a.save()
        # 更新题目列表
        if 'problem_ids' in request.data:
            pids = request.data['problem_ids']
            a.problems.all().delete()
            for order, pid in enumerate(pids):
                if Problem.objects.filter(pk=pid, is_published=True).exists():
                    AssignmentProblem.objects.create(assignment=a, problem_id=pid, sort_order=order)
        return Response(_assignment_data(a))

    def delete(self, request, pk, aid):
        team, a, err = self._get_obj(pk, aid, request.user)
        if err:
            return err
        if not _is_creator_or_admin(request.user, team):
            return Response({'detail': '无删除权限'}, status=status.HTTP_403_FORBIDDEN)
        a.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
