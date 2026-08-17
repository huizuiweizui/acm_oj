"""路由：旧模板站已移除，Django 后台让位给 Vue 管理端，SPA 兜底不吞静态资源。"""
import unittest
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

_DIST = Path(settings.BASE_DIR) / 'frontend' / 'dist'
_HAS_DIST = _DIST.exists()
_needs_dist = unittest.skipUnless(
    _HAS_DIST, 'SPA 兜底路由只在 frontend/dist 存在时启用（先 npm run build）'
)


class LegacyRoutesRemovedTests(SimpleTestCase):
    """回归：旧 Django 模板站曾挂在 '' 且排在 SPA 兜底之前，把首页和 /admin 都抢走了。"""

    def test_legacy_view_module_is_gone(self):
        with self.assertRaises(ModuleNotFoundError):
            __import__('judge.views')

    def test_legacy_urlconf_is_gone(self):
        with self.assertRaises(ModuleNotFoundError):
            __import__('judge.urls')

    @_needs_dist
    def test_root_is_served_by_spa_not_legacy_template(self):
        """/ 曾解析到 judge.views.auth.index（老模板首页），现在应交给 SPA 兜底。"""
        match = resolve('/')
        self.assertNotIn('judge.views', match.func.__module__)
        self.assertEqual(match.func.__module__, 'django.views.generic.base')


class AdminRouteTests(SimpleTestCase):

    def test_django_admin_moved(self):
        self.assertEqual(resolve('/django-admin/').func.__module__,
                         'django.contrib.admin.sites')

    def test_old_admin_path_no_longer_django_admin(self):
        """/admin 已让给 Vue 管理端（/admin、/admin/login、/admin/users）。"""
        if not _HAS_DIST:
            with self.assertRaises(Resolver404):
                resolve('/admin/users')
            return
        self.assertNotIn('django.contrib.admin', resolve('/admin/users').func.__module__)


class ApiRouteTests(SimpleTestCase):

    def test_api_still_resolves(self):
        for path in ('/api/problems/', '/api/submissions/1/', '/api/contests/1/rank/'):
            self.assertEqual(resolve(path).func.__module__, 'judge.api_views', path)


@_needs_dist
class SpaFallbackTests(SimpleTestCase):
    """兜底正则曾把 /assets/* 也吞掉，js/css 被回成 html，页面全白。"""

    def test_assets_not_swallowed_by_spa_fallback(self):
        match = resolve('/assets/index-abc123.js')
        self.assertEqual(match.func.__module__, 'django.views.static')

    def test_favicon_not_swallowed(self):
        self.assertEqual(resolve('/favicon.ico').func.__module__, 'django.views.static')

    def test_spa_routes_fall_through(self):
        for path in ('/problems', '/contests/1', '/learn/graph', '/teacher', '/my-teams'):
            match = resolve(path)
            self.assertEqual(match.func.__module__, 'django.views.generic.base', path)

    def test_api_prefix_excluded_from_fallback(self):
        self.assertEqual(resolve('/api/problems/').func.__module__, 'judge.api_views')
