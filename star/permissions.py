"""
星语的权限：复用平台的角色与团队体系。

    学生端  任何登录用户都可以填问卷、做自己的任务（教师也能借此体验学生流程）
    教师端  教师 / 管理员；教师只能看到自己创建的团队里的学生，管理员看全部
"""
from judge.models import TeamMembership
from judge.permissions import IsTeacherOrAdmin, _role  # noqa: F401  （IsTeacherOrAdmin 供视图引用）

from .models import LearnerProfile


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or _role(user) == 'admin'))


def visible_learner_ids(user):
    qs = LearnerProfile.objects.all()
    if not is_admin(user):
        member_ids = TeamMembership.objects.filter(team__creator=user).values_list('user_id', flat=True)
        qs = qs.filter(user_id__in=member_ids)
    return qs.values_list('user_id', flat=True)


def can_view_learner(user, learner_id):
    return learner_id in set(visible_learner_ids(user))
