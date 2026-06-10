from rest_framework.permissions import BasePermission


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
