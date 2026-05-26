from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('judge.api_urls')),
    path('', include('judge.urls')),
]

# 生产环境：frontend/dist 存在时启用 SPA catch-all
# 将所有非 api/admin/static 的路径交给 Vue Router 处理
if _FRONTEND_DIST.exists():
    urlpatterns += [
        re_path(r'^(?!api/|admin/|static/).*$',
                TemplateView.as_view(template_name='index.html')),
    ]
