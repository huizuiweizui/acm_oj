"""客观题题库 API（单选 / 多选 / 判断 / 填空）。

编程题的提交评测见 api_views.py；本模块只负责题库本身的增删改查与试做判分，
面向教师 / 管理员。学生作答将在「考试 / 作业」里程碑中接入（届时会剥离标准答案）。
"""
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Question, Tag
from .permissions import IsTeacherOrAdmin
from .serializers import QuestionListSerializer, QuestionDetailSerializer

VALID_QTYPES = {'single', 'multiple', 'judge', 'fill'}


# ── 校验 ──────────────────────────────────────────────────────────────────────

def _validate_answer(qtype, answer, options):
    """校验标准答案与题型/选项是否自洽，返回错误消息或 None。"""
    if not isinstance(answer, list) or not answer:
        return '标准答案不能为空'

    if qtype in ('single', 'multiple', 'judge'):
        if qtype == 'single' and len(answer) != 1:
            return '单选题答案须为 1 项'
        if qtype == 'judge':
            vals = {str(a).strip().upper() for a in answer}
            if len(vals) != 1 or not vals <= {'T', 'F'}:
                return '判断题答案须为 T 或 F'
            return None
        if options:
            keys = {str(o['key']).strip().upper() for o in options}
            ans = {str(a).strip().upper() for a in answer}
            if not ans <= keys:
                return '答案必须是选项 key 之一'
        return None

    if qtype == 'fill':
        for blank in answer:
            variants = blank if isinstance(blank, list) else [blank]
            if not variants or all(str(v).strip() == '' for v in variants):
                return '每个空至少需要一个可接受答案'
        return None

    return None


def _validate_payload(data):
    """整体校验题目数据，返回 (cleaned_dict, error_msg)。
    创建与更新都走全量校验：更新时由视图先合并旧值再传入。
    """
    qtype = data.get('qtype')
    if qtype not in VALID_QTYPES:
        return None, 'qtype 须为 single / multiple / judge / fill 之一'

    title = (data.get('title') or '').strip()
    if not title:
        return None, '题干不能为空'

    options = data.get('options') or []
    if qtype in ('single', 'multiple'):
        if not isinstance(options, list) or len(options) < 2:
            return None, '选择题至少需要 2 个选项'
        keys = []
        for opt in options:
            if not isinstance(opt, dict) or 'key' not in opt or 'text' not in opt:
                return None, '每个选项需包含 key 与 text'
            keys.append(str(opt['key']).strip().upper())
        if len(set(keys)) != len(keys):
            return None, '选项 key 不能重复'

    answer = data.get('answer') or []
    err = _validate_answer(qtype, answer, options)
    if err:
        return None, err

    try:
        score = max(0, int(data.get('score', 5)))
    except (TypeError, ValueError):
        return None, '分值须为整数'

    return {
        'qtype': qtype,
        'title': title[:300],
        'content': data.get('content', '') or '',
        'options': options if qtype in ('single', 'multiple') else [],
        'answer': answer,
        'blank_ignore_case': bool(data.get('blank_ignore_case', True)),
        'explanation': data.get('explanation', '') or '',
        'difficulty': data.get('difficulty') or '暂无评定',
        'score': score,
        'source': data.get('source', '') or '',
        'is_published': bool(data.get('is_published', False)),
    }, None


# ── 题库列表 / 创建 ─────────────────────────────────────────────────────────────

class QuestionListCreateAPIView(APIView):
    """GET|POST /api/questions/  （教师 / 管理员）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'detail': '需要教师或管理员权限'}, status=status.HTTP_403_FORBIDDEN)

        qs = Question.objects.prefetch_related('tags').all()

        qtype = request.query_params.get('qtype')
        if qtype in VALID_QTYPES:
            qs = qs.filter(qtype=qtype)

        keyword = (request.query_params.get('q') or '').strip()
        if keyword:
            qs = qs.filter(title__icontains=keyword)

        tag = request.query_params.get('tag')
        if tag:
            qs = qs.filter(tags__id=tag).distinct()

        published = request.query_params.get('is_published')
        if published in ('true', 'false'):
            qs = qs.filter(is_published=(published == 'true'))

        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except (TypeError, ValueError):
            page, page_size = 1, 20

        total = qs.count()
        start = (page - 1) * page_size
        items = qs[start:start + page_size]

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': QuestionListSerializer(items, many=True).data,
        })

    def post(self, request):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'detail': '需要教师或管理员权限'}, status=status.HTTP_403_FORBIDDEN)

        cleaned, err = _validate_payload(request.data)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        question = Question.objects.create(created_by=request.user, **cleaned)
        tag_ids = request.data.get('tag_ids', [])
        if tag_ids:
            question.tags.set(Tag.objects.filter(id__in=tag_ids))

        return Response(QuestionDetailSerializer(question).data, status=status.HTTP_201_CREATED)


# ── 题库详情 / 编辑 / 删除 ──────────────────────────────────────────────────────

class QuestionDetailAPIView(APIView):
    """GET|PATCH|DELETE /api/questions/<id>/  （教师 / 管理员）"""
    permission_classes = [IsAuthenticated]

    def _denied(self, request):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'detail': '需要教师或管理员权限'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def get(self, request, pk):
        denied = self._denied(request)
        if denied:
            return denied
        question = get_object_or_404(Question.objects.prefetch_related('tags'), pk=pk)
        return Response(QuestionDetailSerializer(question).data)

    def patch(self, request, pk):
        denied = self._denied(request)
        if denied:
            return denied
        question = get_object_or_404(Question, pk=pk)

        # 合并旧值再整体校验，避免 PATCH 局部更新破坏题型自洽性
        merged = {
            'qtype': question.qtype, 'title': question.title, 'content': question.content,
            'options': question.options, 'answer': question.answer,
            'blank_ignore_case': question.blank_ignore_case, 'explanation': question.explanation,
            'difficulty': question.difficulty, 'score': question.score,
            'source': question.source, 'is_published': question.is_published,
        }
        for key in list(merged.keys()):
            if key in request.data:
                merged[key] = request.data[key]

        cleaned, err = _validate_payload(merged)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        for key, value in cleaned.items():
            setattr(question, key, value)
        question.save()

        if 'tag_ids' in request.data:
            question.tags.set(Tag.objects.filter(id__in=request.data.get('tag_ids', [])))

        return Response(QuestionDetailSerializer(question).data)

    def delete(self, request, pk):
        denied = self._denied(request)
        if denied:
            return denied
        question = get_object_or_404(Question, pk=pk)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── 试做判分（无状态，教师验证题目用）──────────────────────────────────────────

class QuestionCheckAPIView(APIView):
    """POST /api/questions/<id>/check/  传入 answer，返回判分结果。

    仅教师 / 管理员可用（会回传标准答案与解析，不能暴露给学生）。
    学生的考试作答判分将在考试里程碑中单独实现。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'detail': '需要教师或管理员权限'}, status=status.HTTP_403_FORBIDDEN)

        question = get_object_or_404(Question, pk=pk)
        correct = question.check_answer(request.data.get('answer'))
        return Response({
            'correct': correct,
            'standard_answer': question.answer,
            'explanation': question.explanation,
        })
