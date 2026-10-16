from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    Algorithm, AlgorithmEdge,
    Contest, Discussion, DiscussionReply,
    Problem, Submission, Tag, UserProfile,
)


class AlgorithmListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = ['algo_id', 'name', 'name_en', 'category', 'difficulty', 'desc', 'sort_order']


class AlgorithmDetailSerializer(serializers.ModelSerializer):
    prerequisites = serializers.SerializerMethodField()
    extends_to    = serializers.SerializerMethodField()
    related       = serializers.SerializerMethodField()

    class Meta:
        model = Algorithm
        fields = ['algo_id', 'name', 'name_en', 'category', 'difficulty', 'desc',
                  'description', 'steps', 'complexity', 'stable', 'codes',
                  'prerequisites', 'extends_to', 'related']

    @staticmethod
    def _mini(algo):
        return {
            'algo_id':    algo.algo_id,
            'name':       algo.name,
            'name_en':    algo.name_en,
            'category':   algo.category,
            'difficulty': algo.difficulty,
        }

    def get_prerequisites(self, obj):
        """先学这些：obj 的前置依赖节点（source=obj, type=prerequisite 的 target）"""
        edges = (AlgorithmEdge.objects
                 .filter(source=obj, edge_type='prerequisite')
                 .select_related('target'))
        return [self._mini(e.target) for e in edges]

    def get_extends_to(self, obj):
        """学完可继续：以 obj 为前置或被 obj 扩展的算法"""
        seen, result = set(), []
        qs = (AlgorithmEdge.objects
              .filter(target=obj, edge_type__in=['prerequisite', 'extends'])
              .select_related('source'))
        for e in qs:
            if e.source.algo_id not in seen:
                seen.add(e.source.algo_id)
                result.append(self._mini(e.source))
        return result

    def get_related(self, obj):
        """相关算法：related 类型双向邻居，排除已出现在前置/延伸中的节点"""
        exclude = {a['algo_id'] for a in self.get_prerequisites(obj) + self.get_extends_to(obj)}
        exclude.add(obj.algo_id)
        seen, result = set(), []
        for e in AlgorithmEdge.objects.filter(source=obj, edge_type='related').select_related('target'):
            if e.target.algo_id not in seen and e.target.algo_id not in exclude:
                seen.add(e.target.algo_id)
                result.append(self._mini(e.target))
        for e in AlgorithmEdge.objects.filter(target=obj, edge_type='related').select_related('source'):
            if e.source.algo_id not in seen and e.source.algo_id not in exclude:
                seen.add(e.source.algo_id)
                result.append(self._mini(e.source))
        return result


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.CharField(source='profile.avatar_url', default='')
    avatar_color = serializers.CharField(source='profile.avatar_color', default='#4F46E5')
    rating = serializers.IntegerField(source='profile.rating', default=1500)
    ac_count = serializers.IntegerField(source='profile.ac_count', default=0)
    submit_count = serializers.IntegerField(source='profile.submit_count', default=0)
    bio = serializers.CharField(source='profile.bio', default='')
    role = serializers.CharField(source='profile.role', default='student')
    student_id = serializers.CharField(source='profile.student_id', default='')
    real_name = serializers.CharField(source='profile.real_name', default='')
    major = serializers.CharField(source='profile.major', default='')
    grade = serializers.CharField(source='profile.grade', default='')
    must_change_password = serializers.BooleanField(source='profile.must_change_password', default=False)
    can_create_contest = serializers.BooleanField(source='profile.can_create_contest', default=False)
    is_super_admin = serializers.BooleanField(source='profile.is_super_admin', default=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_url', 'avatar_color',
                  'rating', 'ac_count', 'submit_count', 'bio', 'role',
                  'student_id', 'real_name', 'major', 'grade',
                  'must_change_password', 'can_create_contest', 'is_super_admin']


class ProblemListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    ac_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Problem
        fields = ['id', 'title', 'difficulty', 'ac_rate',
                  'ac_count', 'submit_count', 'tags', 'source']


class ProblemDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    ac_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Problem
        fields = [
            'id', 'title', 'difficulty', 'ac_rate',
            'ac_count', 'submit_count', 'tags', 'source',
            'description', 'input_desc', 'output_desc',
            'sample_input', 'sample_output', 'hint',
            'time_limit', 'memory_limit', 'is_published',
        ]


class SubmissionListSerializer(serializers.ModelSerializer):
    """
    提交列表用。不含源代码、编译错误、AI 反馈——列表可以匿名翻（全站评测流、
    个人主页的近期提交），这些字段跟着一起发出去就等于公开导出所有人的代码。
    """
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    problem_id = serializers.IntegerField(source='problem.id', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'username', 'user_id', 'problem_id', 'problem_title',
            'language', 'status', 'time_used', 'memory_used', 'score', 'submitted_at',
        ]


class SubmissionSerializer(serializers.ModelSerializer):
    """
    提交详情。源代码等私密字段是否返回，由视图通过 context['can_view_code'] 决定
    （见 permissions.can_view_submission_code）。context 缺省时按"不可见"处理，
    这样将来漏传 context 的调用点是少给数据，而不是多给。
    """
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    problem_id = serializers.IntegerField(source='problem.id', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)

    # 都会泄漏代码内容：CE 信息里带源码片段，AI 反馈会复述实现思路
    PRIVATE_FIELDS = ('code', 'error_info', 'ai_feedback')

    class Meta:
        model = Submission
        fields = [
            'id', 'username', 'user_id', 'problem_id', 'problem_title',
            'language', 'status', 'time_used', 'memory_used', 'score',
            'error_info', 'ai_feedback', 'test_results', 'code', 'submitted_at',
        ]
        read_only_fields = [
            'status', 'time_used', 'memory_used', 'score',
            'error_info', 'ai_feedback', 'test_results', 'submitted_at',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['can_view_code'] = bool(self.context.get('can_view_code'))   # 前端据此显示"代码不可见"
        if not data['can_view_code']:
            for name in self.PRIVATE_FIELDS:
                data[name] = ''
        return data


class ContestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    problem_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'start_time', 'end_time',
            'rule_type', 'is_public', 'status', 'created_by_username', 'problem_count',
        ]


class DiscussionReplySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = DiscussionReply
        fields = ['id', 'username', 'content', 'created_at']
        read_only_fields = ['created_at']


class DiscussionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    problem_id = serializers.IntegerField(source='problem.id', read_only=True, allow_null=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True, allow_null=True)
    reply_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Discussion
        fields = [
            'id', 'username', 'problem_id', 'problem_title',
            'title', 'content', 'view_count', 'reply_count', 'created_at',
        ]
        read_only_fields = ['view_count', 'created_at']
