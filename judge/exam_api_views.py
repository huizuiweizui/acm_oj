"""学生端考试 / 作业答题流。

进入(建立会话/限时) → 拉取试卷(客观题不含标准答案) → 提交客观题(自动判分)
→ 交卷(结算总分) → 切屏上报(防作弊审计)。

编程题仍走 /api/problems/<id>/submit/（带 assignment_id 时归属本作业）。
"""
import hashlib
import io
from datetime import timedelta

import openpyxl
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Assignment, AssignmentQuestion,
    ExamParticipation, QuestionAnswer, Submission,
)
from .services.similarity import fingerprint, similarity, jaccard, token_count


# ── 权限与时间状态 ──────────────────────────────────────────────────────────────

def _can_access(user, assignment):
    """是否为该作业所属团队的成员 / 创建者 / 管理员。"""
    team = assignment.team
    if team.creator_id == user.id:
        return True
    profile = getattr(user, 'profile', None)
    if profile and profile.role == 'admin':
        return True
    return team.memberships.filter(user=user).exists()


def _is_manager(user, assignment):
    team = assignment.team
    profile = getattr(user, 'profile', None)
    if team.creator_id == user.id or bool(profile and profile.role == 'admin'):
        return True
    # 助教（TA）可批改 / 看成绩 / 查重
    return team.memberships.filter(user=user, role='assistant').exists()


def _personal_deadline(assignment, participation):
    """考试个人截止 = min(窗口结束, 进入时间 + 个人限时)。非考试返回 None。"""
    if assignment.category != 'exam':
        return None
    end = assignment.end_time
    if participation and assignment.duration_minutes > 0:
        personal_end = participation.started_at + timedelta(minutes=assignment.duration_minutes)
        if end is None or personal_end < end:
            return personal_end
    return end


def _answering_open(assignment, participation):
    """当前是否还能作答 / 提交，返回 (bool, 原因)。"""
    now = timezone.now()
    if not assignment.is_active:
        return False, '该作业未发布'
    cat = assignment.category
    if cat == 'practice':
        return True, ''
    if cat == 'homework':
        if assignment.deadline and now > assignment.deadline:
            return False, '作业已截止'
        return True, ''
    # exam
    if participation is None:
        return False, '请先进入考试'
    if participation.status != 'in_progress':
        return False, '已交卷'
    if assignment.start_time and now < assignment.start_time:
        return False, '考试未开始'
    pd = _personal_deadline(assignment, participation)
    if pd and now > pd:
        return False, '考试已结束'
    return True, ''


def _participation_data(assignment, participation):
    pd = _personal_deadline(assignment, participation)
    return {
        'status': participation.status,
        'started_at': participation.started_at.isoformat(),
        'submitted_at': participation.submitted_at.isoformat() if participation.submitted_at else None,
        'focus_loss_count': participation.focus_loss_count,
        'total_score': participation.total_score,
        'personal_deadline': pd.isoformat() if pd else None,
        'server_now': timezone.now().isoformat(),
    }


def _stable_shuffle(items, seed):
    """按 (seed, id) 哈希稳定打乱：同一学生每次刷新顺序一致，不同学生不同。"""
    return sorted(items, key=lambda it: hashlib.md5(f'{seed}-{it["id"]}'.encode()).hexdigest())


def _ratio(test_results):
    """编程题单次提交的测试点通过率。"""
    if not test_results:
        return 0.0
    total = len(test_results)
    if not total:
        return 0.0
    return sum(1 for c in test_results if c.get('status') == 'AC') / total


def _grade(assignment, user):
    """结算某学生在该作业的得分：客观题自动分 + 编程题（取最佳提交的测试点通过率 × 分值）。"""
    problems = list(assignment.problems.select_related('problem').order_by('sort_order', 'id'))
    questions = list(assignment.question_items.select_related('question').order_by('sort_order', 'id'))

    qa_map = {qa.question_id: qa for qa in QuestionAnswer.objects.filter(assignment=assignment, user=user)}
    objective_score = sum(qa.score for qa in qa_map.values())

    pids = [ap.problem_id for ap in problems]
    ratios = {pid: 0.0 for pid in pids}
    if pids:
        for s in Submission.objects.filter(
            assignment=assignment, user=user, problem_id__in=pids,
        ).values('problem_id', 'status', 'test_results'):
            r = 1.0 if s['status'] == 'AC' else _ratio(s['test_results'])
            ratios[s['problem_id']] = max(ratios[s['problem_id']], r)

    prob_got = {ap.problem_id: round(ap.score * ratios.get(ap.problem_id, 0.0)) for ap in problems}
    programming_score = sum(prob_got.values())
    max_score = sum(ap.score for ap in problems) + sum(aq.score for aq in questions)

    return {
        'total_score': objective_score + programming_score,
        'objective_score': objective_score,
        'programming_score': programming_score,
        'max_score': max_score,
        'questions': [{
            'id': aq.question_id,
            'title': aq.question.title,
            'score': aq.score,
            'got_score': qa_map[aq.question_id].score if aq.question_id in qa_map else 0,
            'correct': qa_map[aq.question_id].is_correct if aq.question_id in qa_map else False,
            'my_answer': qa_map[aq.question_id].answer if aq.question_id in qa_map else None,
            'explanation': aq.question.explanation,
        } for aq in questions],
        'problems': [{
            'id': ap.problem_id,
            'title': ap.problem.title,
            'score': ap.score,
            'got_score': prob_got[ap.problem_id],
            'ratio': round(ratios.get(ap.problem_id, 0.0), 3),
            'ac': ratios.get(ap.problem_id, 0.0) >= 1.0,
        } for ap in problems],
    }


# ── 进入 ───────────────────────────────────────────────────────────────────────

class ExamEnterAPIView(APIView):
    """POST /api/assignments/<aid>/enter/  进入作业/考试，建立会话并开始计时。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _can_access(request.user, assignment):
            return Response({'detail': '无权访问该作业'}, status=status.HTTP_403_FORBIDDEN)
        if not assignment.is_active and not _is_manager(request.user, assignment):
            return Response({'detail': '该作业未发布'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        if assignment.category == 'exam' and not _is_manager(request.user, assignment):
            if assignment.start_time and now < assignment.start_time:
                return Response({'detail': '考试未开始'}, status=status.HTTP_403_FORBIDDEN)
            if assignment.end_time and now > assignment.end_time:
                return Response({'detail': '考试已结束'}, status=status.HTTP_403_FORBIDDEN)

        participation, _created = ExamParticipation.objects.get_or_create(
            assignment=assignment, user=request.user,
        )
        return Response(_participation_data(assignment, participation))


# ── 试卷 ───────────────────────────────────────────────────────────────────────

class ExamPaperAPIView(APIView):
    """GET /api/assignments/<aid>/paper/  拉取试卷（客观题不含标准答案）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, aid):
        assignment = get_object_or_404(
            Assignment.objects.prefetch_related('problems__problem', 'question_items__question'),
            pk=aid,
        )
        if not _can_access(request.user, assignment):
            return Response({'detail': '无权访问该作业'}, status=status.HTTP_403_FORBIDDEN)

        is_manager = _is_manager(request.user, assignment)
        participation = ExamParticipation.objects.filter(
            assignment=assignment, user=request.user
        ).first()

        # 考试：学生必须先进入且已开考（管理员可直接预览）
        if assignment.category == 'exam' and not is_manager:
            if participation is None:
                return Response({'detail': '请先进入考试'}, status=status.HTTP_403_FORBIDDEN)
            now = timezone.now()
            if assignment.start_time and now < assignment.start_time:
                return Response({'detail': '考试未开始'}, status=status.HTTP_403_FORBIDDEN)

        # 考试进行中不揭晓对错；练习/作业、或已交卷则揭晓
        reveal = assignment.category != 'exam' or (participation and participation.status != 'in_progress')
        my_answers = {
            qa.question_id: qa
            for qa in QuestionAnswer.objects.filter(assignment=assignment, user=request.user)
        }

        problems = list(assignment.problems.select_related('problem').order_by('sort_order', 'id'))
        questions = list(assignment.question_items.select_related('question').order_by('sort_order', 'id'))

        ac_pids = set()
        pids = [ap.problem_id for ap in problems]
        if pids:
            ac_pids = set(Submission.objects.filter(
                assignment=assignment, user=request.user, status='AC', problem_id__in=pids,
            ).values_list('problem_id', flat=True))

        problem_items = [{
            'id': ap.problem_id,
            'title': ap.problem.title,
            'difficulty': ap.problem.difficulty,
            'time_limit': ap.problem.time_limit,
            'memory_limit': ap.problem.memory_limit,
            'score': ap.score,
            'ac': ap.problem_id in ac_pids,
        } for ap in problems]

        question_items = []
        for aq in questions:
            qa = my_answers.get(aq.question_id)
            item = {
                'id': aq.question_id,
                'title': aq.question.title,
                'content': aq.question.content,
                'qtype': aq.question.qtype,
                'qtype_display': aq.question.get_qtype_display(),
                'options': aq.question.options,
                'score': aq.score,
                'my_answer': qa.answer if qa else None,
                # 填空题告知空数（不泄露答案内容），供前端渲染输入框
                'blank_count': len(aq.question.answer) if aq.question.qtype == 'fill' else 0,
            }
            if reveal and qa:
                item['correct'] = qa.is_correct
                item['got_score'] = qa.score
                item['explanation'] = aq.question.explanation
            question_items.append(item)

        if assignment.shuffle and not is_manager:
            problem_items = _stable_shuffle(problem_items, request.user.id)
            question_items = _stable_shuffle(question_items, request.user.id)

        return Response({
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'category': assignment.category,
            'hide_rank': assignment.hide_rank,
            'track_focus': assignment.track_focus,
            'deadline': assignment.deadline.isoformat() if assignment.deadline else None,
            'start_time': assignment.start_time.isoformat() if assignment.start_time else None,
            'end_time': assignment.end_time.isoformat() if assignment.end_time else None,
            'duration_minutes': assignment.duration_minutes,
            'total_score': sum(ap.score for ap in problems) + sum(aq.score for aq in questions),
            'participation': _participation_data(assignment, participation) if participation else None,
            'problems': problem_items,
            'questions': question_items,
        })


# ── 客观题作答（自动判分）──────────────────────────────────────────────────────

class ExamAnswerAPIView(APIView):
    """POST /api/assignments/<aid>/answer/  body: {question_id, answer}。自动判分并保存。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _can_access(request.user, assignment):
            return Response({'detail': '无权访问该作业'}, status=status.HTTP_403_FORBIDDEN)

        participation = ExamParticipation.objects.filter(
            assignment=assignment, user=request.user
        ).first()
        ok, msg = _answering_open(assignment, participation)
        if not ok:
            return Response({'detail': msg}, status=status.HTTP_403_FORBIDDEN)

        aq = AssignmentQuestion.objects.select_related('question').filter(
            assignment=assignment, question_id=request.data.get('question_id')
        ).first()
        if aq is None:
            return Response({'detail': '该题不属于此作业'}, status=status.HTTP_404_NOT_FOUND)

        submitted = request.data.get('answer')
        correct = aq.question.check_answer(submitted)
        got = aq.score if correct else 0

        QuestionAnswer.objects.update_or_create(
            assignment=assignment, user=request.user, question=aq.question,
            defaults={
                'answer': submitted if isinstance(submitted, list) else [submitted],
                'is_correct': correct,
                'score': got,
            },
        )

        resp = {'saved': True}
        if assignment.category != 'exam':  # 练习/作业即时反馈，考试交卷后再揭晓
            resp.update({'correct': correct, 'got_score': got, 'explanation': aq.question.explanation})
        return Response(resp)


# ── 交卷 ───────────────────────────────────────────────────────────────────────

class ExamSubmitAPIView(APIView):
    """POST /api/assignments/<aid>/submit/  交卷并结算总分。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, aid):
        assignment = get_object_or_404(
            Assignment.objects.prefetch_related('problems__problem', 'question_items__question'),
            pk=aid,
        )
        if not _can_access(request.user, assignment):
            return Response({'detail': '无权访问该作业'}, status=status.HTTP_403_FORBIDDEN)

        participation = ExamParticipation.objects.filter(
            assignment=assignment, user=request.user
        ).first()
        if assignment.category == 'exam':
            if participation is None:
                return Response({'detail': '未进入考试'}, status=status.HTTP_400_BAD_REQUEST)
            if participation.status != 'in_progress':
                return Response({'detail': '已交卷'}, status=status.HTTP_400_BAD_REQUEST)
        elif participation is None:
            participation, _ = ExamParticipation.objects.get_or_create(
                assignment=assignment, user=request.user
            )

        result = _grade(assignment, request.user)

        with transaction.atomic():
            participation.status = 'submitted'
            participation.submitted_at = timezone.now()
            participation.total_score = result['total_score']
            participation.save(update_fields=['status', 'submitted_at', 'total_score'])

        return Response(result)


# ── 切屏上报 ────────────────────────────────────────────────────────────────────

class ExamFocusLossAPIView(APIView):
    """POST /api/assignments/<aid>/focus-loss/  上报一次切屏（考试防作弊审计）。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _can_access(request.user, assignment):
            return Response({'detail': '无权访问'}, status=status.HTTP_403_FORBIDDEN)

        participation = ExamParticipation.objects.filter(
            assignment=assignment, user=request.user, status='in_progress'
        ).first()
        if participation is None:
            return Response({'focus_loss_count': 0})

        ExamParticipation.objects.filter(pk=participation.pk).update(
            focus_loss_count=F('focus_loss_count') + 1
        )
        return Response({'focus_loss_count': participation.focus_loss_count + 1})


# ── 成绩单（教师）──────────────────────────────────────────────────────────────

def _build_gradebook(assignment):
    """批量计算全班成绩，返回 (rows, max_score)。固定 3 次查询，与班级规模无关。"""
    members = list(assignment.team.memberships.select_related('user__profile').order_by('joined_at'))
    member_ids = [m.user_id for m in members]
    problems = list(assignment.problems.order_by('sort_order', 'id'))
    questions = list(assignment.question_items.order_by('sort_order', 'id'))
    pids = [ap.problem_id for ap in problems]
    prog_full = {ap.problem_id: ap.score for ap in problems}
    max_score = sum(ap.score for ap in problems) + sum(aq.score for aq in questions)

    obj_scores = {}
    for qa in QuestionAnswer.objects.filter(
        assignment=assignment, user_id__in=member_ids
    ).values('user_id', 'score'):
        obj_scores[qa['user_id']] = obj_scores.get(qa['user_id'], 0) + qa['score']

    best_ratio = {uid: {} for uid in member_ids}
    if pids:
        for s in Submission.objects.filter(
            assignment=assignment, user_id__in=member_ids, problem_id__in=pids,
        ).values('user_id', 'problem_id', 'status', 'test_results'):
            r = 1.0 if s['status'] == 'AC' else _ratio(s['test_results'])
            d = best_ratio[s['user_id']]
            d[s['problem_id']] = max(d.get(s['problem_id'], 0.0), r)

    parts = {p.user_id: p for p in assignment.participations.filter(user_id__in=member_ids)}

    rows = []
    for m in members:
        uid = m.user_id
        prog = sum(round(prog_full[pid] * best_ratio[uid].get(pid, 0.0)) for pid in pids)
        obj = obj_scores.get(uid, 0)
        part = parts.get(uid)
        profile = getattr(m.user, 'profile', None)
        rows.append({
            'user_id': uid,
            'username': m.user.username,
            'display_name': m.display_name,
            'student_id': profile.student_id if profile else '',
            'objective_score': obj,
            'programming_score': prog,
            'total_score': obj + prog,
            'status': part.status if part else 'not_started',
            'focus_loss_count': part.focus_loss_count if part else 0,
            'submitted_at': part.submitted_at.isoformat() if part and part.submitted_at else None,
        })
    rows.sort(key=lambda r: -r['total_score'])
    return rows, max_score


class GradebookAPIView(APIView):
    """GET /api/assignments/<aid>/gradebook/  教师查看全班成绩。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _is_manager(request.user, assignment):
            return Response({'detail': '需要教师/管理员权限'}, status=status.HTTP_403_FORBIDDEN)
        rows, max_score = _build_gradebook(assignment)
        submitted = sum(1 for r in rows if r['status'] in ('submitted', 'graded'))
        return Response({
            'assignment': {'id': assignment.id, 'title': assignment.title, 'category': assignment.category},
            'max_score': max_score,
            'member_count': len(rows),
            'submitted_count': submitted,
            'rows': rows,
        })


class GradebookExportAPIView(APIView):
    """GET /api/assignments/<aid>/gradebook/export/  导出成绩单 Excel。"""
    permission_classes = [IsAuthenticated]

    _STATUS_CN = {'not_started': '未开始', 'in_progress': '进行中', 'submitted': '已交卷', 'graded': '已批改'}

    def get(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _is_manager(request.user, assignment):
            return Response({'detail': '需要教师/管理员权限'}, status=status.HTTP_403_FORBIDDEN)
        rows, max_score = _build_gradebook(assignment)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '成绩单'
        ws.append(['排名', '姓名', '用户名', '学号', '客观分', '编程分', '总分',
                   f'满分({max_score})', '状态', '切屏', '交卷时间'])
        for i, r in enumerate(rows, 1):
            ws.append([
                i, r['display_name'], r['username'], r['student_id'],
                r['objective_score'], r['programming_score'], r['total_score'], max_score,
                self._STATUS_CN.get(r['status'], r['status']), r['focus_loss_count'],
                r['submitted_at'] or '',
            ])
        for col, width in zip('ABCDEFGHIJK', [6, 12, 14, 14, 8, 8, 8, 10, 8, 6, 22]):
            ws.column_dimensions[col].width = width

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = f'attachment; filename="gradebook_{assignment.id}.xlsx"'
        return resp


class StudentResultAPIView(APIView):
    """GET /api/assignments/<aid>/students/<uid>/result/  教师查看单个学生作答详情与得分。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, aid, uid):
        from django.contrib.auth.models import User
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _is_manager(request.user, assignment):
            return Response({'detail': '需要教师/管理员权限'}, status=status.HTTP_403_FORBIDDEN)
        student = get_object_or_404(User, pk=uid)
        result = _grade(assignment, student)
        part = assignment.participations.filter(user=student).first()
        result['participation'] = _participation_data(assignment, part) if part else None
        result['student'] = {'user_id': student.id, 'username': student.username}
        return Response(result)


# ── 代码查重（教师，Winnowing 指纹）────────────────────────────────────────────

_PLAGIARISM_MIN_TOKENS = 25   # token 过少的提交（如空壳）不参与，避免样板代码误报


class PlagiarismAPIView(APIView):
    """GET /api/assignments/<aid>/plagiarism/?threshold=0.5
    对作业/考试内每道编程题，两两比对学生最新提交的代码相似度，给出超阈值的可疑对。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _is_manager(request.user, assignment):
            return Response({'detail': '需要教师/管理员权限'}, status=status.HTTP_403_FORBIDDEN)

        try:
            threshold = min(1.0, max(0.1, float(request.query_params.get('threshold', 0.5))))
        except (TypeError, ValueError):
            threshold = 0.5

        names = {
            ms.user_id: ms.display_name
            for ms in assignment.team.memberships.select_related('user', 'user__profile')
        }
        problems = list(assignment.problems.select_related('problem').order_by('sort_order', 'id'))

        report = []
        for ap in problems:
            # 每位学生取最新一次提交作为代表
            latest = {}
            for s in (Submission.objects
                      .filter(assignment=assignment, problem_id=ap.problem_id)
                      .order_by('user_id', '-submitted_at')
                      .only('id', 'user_id', 'code', 'raw_code', 'language', 'submitted_at')):
                if s.user_id not in latest:
                    latest[s.user_id] = s

            fps = {}
            for uid, s in latest.items():
                src = s.raw_code or s.code   # 函数题用学生函数，避免公共驱动样板误报
                if token_count(src, s.language) >= _PLAGIARISM_MIN_TOKENS:
                    fps[uid] = (fingerprint(src, s.language), s.id)

            uids = list(fps.keys())
            pairs = []
            for i in range(len(uids)):
                for j in range(i + 1, len(uids)):
                    a, b = uids[i], uids[j]
                    sim = similarity(fps[a][0], fps[b][0])
                    if sim >= threshold:
                        pairs.append({
                            'user_a': a, 'name_a': names.get(a, ''), 'sub_a': fps[a][1],
                            'user_b': b, 'name_b': names.get(b, ''), 'sub_b': fps[b][1],
                            'similarity': round(sim, 3),
                            'jaccard': round(jaccard(fps[a][0], fps[b][0]), 3),
                        })
            pairs.sort(key=lambda p: -p['similarity'])
            if pairs:
                report.append({
                    'problem_id': ap.problem_id,
                    'problem_title': ap.problem.title,
                    'checked': len(fps),
                    'pairs': pairs,
                })

        return Response({
            'assignment': {'id': assignment.id, 'title': assignment.title},
            'threshold': threshold,
            'report': report,
        })


class PlagiarismPairAPIView(APIView):
    """GET /api/assignments/<aid>/plagiarism/pair/?a=<subId>&b=<subId>
    并排取两份提交的源代码与相似度，供教师人工研判。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, aid):
        assignment = get_object_or_404(Assignment, pk=aid)
        if not _is_manager(request.user, assignment):
            return Response({'detail': '需要教师/管理员权限'}, status=status.HTTP_403_FORBIDDEN)
        try:
            sa = Submission.objects.get(pk=request.query_params.get('a'), assignment=assignment)
            sb = Submission.objects.get(pk=request.query_params.get('b'), assignment=assignment)
        except (Submission.DoesNotExist, ValueError, TypeError):
            return Response({'detail': '提交不存在'}, status=status.HTTP_404_NOT_FOUND)

        code_a = sa.raw_code or sa.code
        code_b = sb.raw_code or sb.code
        fa = fingerprint(code_a, sa.language)
        fb = fingerprint(code_b, sb.language)
        return Response({
            'a': {'submission_id': sa.id, 'user_id': sa.user_id, 'language': sa.language, 'code': code_a},
            'b': {'submission_id': sb.id, 'user_id': sb.user_id, 'language': sb.language, 'code': code_b},
            'similarity': round(similarity(fa, fb), 3),
            'jaccard': round(jaccard(fa, fb), 3),
        })
