from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    Contest, Discussion, DiscussionReply,
    Problem, Submission, Tag, UserProfile,
)


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
    role = serializers.CharField(source='profile.role', default='user')

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_url', 'avatar_color',
                  'rating', 'ac_count', 'submit_count', 'bio', 'role']


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


class SubmissionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    problem_id = serializers.IntegerField(source='problem.id', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'username', 'problem_id', 'problem_title',
            'language', 'status', 'time_used', 'memory_used',
            'error_info', 'ai_feedback', 'test_results', 'code', 'submitted_at',
        ]
        read_only_fields = [
            'status', 'time_used', 'memory_used',
            'error_info', 'ai_feedback', 'test_results', 'submitted_at',
        ]


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
