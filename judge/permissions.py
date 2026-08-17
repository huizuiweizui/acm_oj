from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import Contest, ContestParticipant


def _role(user):
    try:
        return user.profile.role
    except Exception:
        return 'student'


def can_view_submission_code(user, submission):
    """
    能否看到这条提交的源代码（连带编译错误、AI 反馈——两者都会泄漏代码内容）。

    只有本人、教师、管理员可见。其他人（含未登录）只能看到评测结果本身。
    不加这道闸的话，/api/submissions/?all=1 就是一个全站源码导出接口，
    比赛期间等于开挂通道，平时是抄袭源头。
    """
    if not user or not user.is_authenticated:
        return False
    if submission.user_id == user.id:
        return True
    return user.is_superuser or _role(user) in ('teacher', 'admin')


def _is_staff(user):
    """教师 / 管理员 / 超级用户——平台上的可信角色。"""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or _role(user) in ('teacher', 'admin')


def can_manage_contest(user, contest):
    """出题人 / 教师 / 管理员：不受赛程和报名限制，随时能看赛题。"""
    if not user or not user.is_authenticated:
        return False
    return _is_staff(user) or contest.created_by_id == user.id


def contest_problems_visible(user, contest):
    """
    比赛的题目清单（编号 / 标题 / 链接）对该用户是否可见。

        未开始 —— 仅管理者可见，避免赛前泄题
        进行中 —— 已报名者可见
        已结束 —— 所有人可见（能否打开题面另由 can_access_problem 决定）
    """
    if contest.status == 'ended' or can_manage_contest(user, contest):
        return True
    if contest.status == 'running' and user and user.is_authenticated:
        return ContestParticipant.objects.filter(contest=contest, user=user).exists()
    return False


def can_access_problem(user, problem):
    """
    能否打开这道题的题面。

    已公开的题目谁都能看。未公开的题目只有一种放行情形：它属于某场正在进行、
    且该用户已报名的比赛。

    这条规则是为了解开原先的死结——赛题设为公开则赛前就能被翻出来刷，设为不公开
    则选手赛中也打不开。现在赛题可以一直保持不公开：赛前搜不到，赛中参赛者能打开，
    赛后由出题人决定何时公开。

    出题人和教师另外始终放行：他们在比赛页看得到题目清单，点进去却 404 是说不通的，
    出题前也需要预览自己的题。
    """
    if problem.is_published:
        return True
    if not user or not user.is_authenticated:
        return False
    if _is_staff(user):
        return True
    # 出题人预览自己比赛里的题
    if Contest.objects.filter(
        contest_problems__problem_id=problem.id, created_by=user
    ).exists():
        return True
    return Contest.objects.filter(
        contest_problems__problem_id=problem.id,
        participants__user=user,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now(),
    ).exists()


class IsTeacherOrAdmin(BasePermission):
    """教师或管理员（admin ⊇ teacher ⊇ student）"""
    message = '该操作需要教师或管理员权限'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role in ('teacher', 'admin')
        except Exception:
            return False


class IsAdminOnly(BasePermission):
    """仅管理员"""
    message = '该操作需要管理员权限'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == 'admin'
        except Exception:
            return False
