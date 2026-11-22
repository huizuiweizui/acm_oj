from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'


def learn_page(request):
    if settings.DEBUG:
        return HttpResponseRedirect(f'{settings.FRONTEND_DEV_ORIGIN}{request.get_full_path()}')
    if not (_FRONTEND_DIST / 'index.html').is_file():
        raise Http404('Vue 前端尚未构建')
    return render(request, 'index.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('judge.api_urls')),
    re_path(r'^learn(?:/.*)?$', learn_page, name='learn'),
    path('', include('judge.urls')),
]

# 生产环境：frontend/dist 存在时启用 SPA catch-all
# 将所有非 api/admin/static 的路径交给 Vue Router 处理
if _FRONTEND_DIST.exists():
    urlpatterns += [
        re_path(r'^(?!api/|admin/|static/).*$',
                TemplateView.as_view(template_name='index.html')),
    ]
