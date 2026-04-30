"""Judge app URL 配置 — 对应技术方案书 §7.1 页面路由"""
from django.urls import path
from . import views

urlpatterns = [
    # 首页
    path('', views.index, name='index'),

    # 用户认证
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 题库
    path('problems/', views.problem_list, name='problem_list'),
    path('problems/<int:problem_id>/', views.problem_detail, name='problem_detail'),

    # 代码提交（AJAX）
    path('problems/<int:problem_id>/submit/', views.submit_code, name='submit_code'),

    # 提交记录
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/<int:submission_id>/', views.submission_detail, name='submission_detail'),

    # 比赛
    path('contests/', views.contest_list, name='contest_list'),
    path('contests/create/', views.contest_create, name='contest_create'),
    path('contests/<int:contest_id>/', views.contest_detail, name='contest_detail'),
    path('contests/<int:contest_id>/register/', views.contest_register, name='contest_register'),
    path('contests/<int:contest_id>/ranking/', views.contest_ranking, name='contest_ranking'),

    # API
    path('api/problems/', views.api_problems, name='api_problems'),

    # 排行榜
    path('rank/', views.leaderboard, name='leaderboard'),

    # 讨论区
    path('discussions/', views.discussion_list, name='discussion_list'),
    path('discussions/new/', views.create_discussion_general, name='create_discussion_general'),
    path('discussions/<int:discussion_id>/', views.discussion_detail, name='discussion_detail'),
    path('problems/<int:problem_id>/discuss/', views.create_discussion, name='create_discussion'),

    # 个人主页
    path('profile/<int:user_id>/', views.profile_view, name='profile'),
    path('profile/', views.my_profile, name='my_profile'),

    # 算法学习
    path('learn/', views.learn_view, name='learn'),
    path('api/learn/problems/', views.learn_tag_problems, name='learn_tag_problems'),
]
