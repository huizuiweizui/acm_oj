"""ACM OJ 管理后台"""
from django import forms
from django.contrib import admin
from django.db import models

from .models import (
    UserProfile, Tag, Problem, TestCase, Submission,
    Contest, ContestProblem, ContestParticipant,
    Discussion, DiscussionReply, Question,
)

_MONO_TEXTAREA = forms.Textarea(attrs={
    'rows': 8,
    'style': 'font-family: monospace; white-space: pre; width: 100%;',
})


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'ac_count', 'submit_count', 'rating']
    list_filter = ['role']
    search_fields = ['user__username']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class TestCaseInline(admin.StackedInline):
    model = TestCase
    extra = 1
    show_change_link = True
    fields = ['sort_order', 'is_sample', 'input_data', 'expected_output']
    formfield_overrides = {models.TextField: {'widget': _MONO_TEXTAREA}}


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'problem_type', 'difficulty', 'ac_count', 'submit_count', 'is_published']
    list_filter = ['difficulty', 'is_published', 'problem_type']
    search_fields = ['title', 'source']
    filter_horizontal = ['tags']
    inlines = [TestCaseInline]


@admin.action(description='删除所选题目的 AI 生成测试点（保留样例）')
def delete_ai_testcases(modeladmin, request, queryset):
    deleted, _ = queryset.filter(is_sample=False).delete()
    modeladmin.message_user(request, f'已删除 {deleted} 个 AI 生成测试点')


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display  = ['id', 'problem', 'sort_order', 'is_sample', 'input_preview', 'output_preview']
    list_filter   = ['is_sample']
    search_fields = ['problem__title', 'problem__source']
    raw_id_fields = ['problem']
    ordering      = ['problem', 'sort_order']
    actions       = [delete_ai_testcases]
    formfield_overrides = {models.TextField: {'widget': _MONO_TEXTAREA}}

    @admin.display(description='输入预览')
    def input_preview(self, obj):
        s = obj.input_data.replace('\n', ' ')
        return s[:80] + '…' if len(s) > 80 else s

    @admin.display(description='输出预览')
    def output_preview(self, obj):
        s = obj.expected_output.replace('\n', ' ')
        return s[:80] + '…' if len(s) > 80 else s


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'problem', 'language', 'status', 'time_used', 'memory_used', 'submitted_at']
    list_filter = ['status', 'language']
    search_fields = ['user__username']
    readonly_fields = ['code']


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ['title', 'rule_type', 'start_time', 'end_time', 'is_public']
    list_filter = ['rule_type', 'is_public']


@admin.register(ContestProblem)
class ContestProblemAdmin(admin.ModelAdmin):
    list_display = ['contest', 'label', 'problem']


@admin.register(ContestParticipant)
class ContestParticipantAdmin(admin.ModelAdmin):
    list_display = ['contest', 'user', 'score', 'penalty']


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'problem', 'view_count', 'created_at']
    search_fields = ['title']


@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ['discussion', 'user', 'created_at']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'qtype', 'title', 'difficulty', 'score', 'is_published', 'created_at']
    list_filter = ['qtype', 'difficulty', 'is_published']
    search_fields = ['title', 'source']
    filter_horizontal = ['tags']
