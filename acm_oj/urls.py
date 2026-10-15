from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'

# Django 自带后台挂在 /django-admin/ 而不是 /admin/：
# 前端 Vue 的管理端占用了 /admin、/admin/login、/admin/users，
# 两者同名时 Django 会先匹配，管理端页面永远打不开。
urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/star/', include('star.urls')),
    path('api/', include('judge.api_urls')),
]

# 生产环境：frontend/dist 存在时单端口同时服务前后端。
# 顺序要紧：先把 Vite 产物（/assets/*、favicon）交给静态文件服务，
# 剩下的才丢给 SPA catch-all —— 否则 catch-all 会把 js/css 也回成 index.html，
# 浏览器按 MIME 拒绝加载，页面全白。
#
# django.views.static.serve 只适合自用规模；对外部署应由 nginx 直接托管
# frontend/dist，或引入 WhiteNoise。
if _FRONTEND_DIST.exists():
    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': _FRONTEND_DIST / 'assets'}),
        re_path(r'^(?P<path>favicon\.ico)$', serve, {'document_root': _FRONTEND_DIST}),
        re_path(r'^(?!api/|django-admin/|static/|assets/).*$',
                TemplateView.as_view(template_name='index.html')),
    ]
