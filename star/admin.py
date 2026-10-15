from django.contrib import admin

from .models import AdaptedTask, LearnerProfile, LLMCallLog, StepAttempt


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'layer', 'status', 'updated_at')
    list_filter = ('layer', 'status')
    search_fields = ('user__username',)


@admin.register(AdaptedTask)
class AdaptedTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'layer', 'template', 'status', 'gen_count', 'approved_at')
    list_filter = ('layer', 'status')
    search_fields = ('student__username', 'template')


@admin.register(StepAttempt)
class StepAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'step_index', 'hint_level', 'is_correct', 'duration_ms', 'created_at')
    list_filter = ('is_correct', 'hint_level')


@admin.register(LLMCallLog)
class LLMCallLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'purpose', 'attempt', 'passed', 'duration_ms', 'total_tokens', 'tag', 'created_at')
    list_filter = ('purpose', 'passed', 'tag')
    readonly_fields = [f.name for f in LLMCallLog._meta.fields]
