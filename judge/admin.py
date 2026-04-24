"""ACM OJ 管理后台"""
from django.contrib import admin
from .models import (
    UserProfile, Tag, Problem, TestCase, Submission,
    Contest, ContestProblem, ContestParticipant,
    Discussion, DiscussionReply,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'ac_count', 'submit_count', 'rating']
    list_filter = ['role']
    search_fields = ['user__username']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'difficulty', 'ac_count', 'submit_count', 'is_published']
    list_filter = ['difficulty', 'is_published']
    search_fields = ['title', 'source']
    filter_horizontal = ['tags']
    inlines = [TestCaseInline]


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
