from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import (
    ContestDetailAPIView, ContestListAPIView, ContestRankingAPIView, ContestRegisterAPIView,
    DiscussionCreateAPIView, DiscussionDetailAPIView,
    DiscussionListAPIView, DiscussionReplyCreateAPIView,
    LeaderboardAPIView,
    LoginAPIView, MeAPIView, PlatformStatsAPIView, ProblemDetailAPIView,
    ProblemListAPIView, RegisterAPIView,
    SubmissionListAPIView, SubmissionDetailAPIView,
    SubmitCodeAPIView, UserProfileAPIView, UserStatsAPIView,
)

urlpatterns = [
    # 认证
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    path('auth/me/', MeAPIView.as_view(), name='api-me'),

    # 题目
    path('problems/', ProblemListAPIView.as_view(), name='api-problem-list'),
    path('problems/<int:pk>/', ProblemDetailAPIView.as_view(), name='api-problem-detail'),
    path('problems/<int:pk>/submit/', SubmitCodeAPIView.as_view(), name='api-submit-code'),

    # 提交记录
    path('submissions/', SubmissionListAPIView.as_view(), name='api-submission-list'),
    path('submissions/<int:pk>/', SubmissionDetailAPIView.as_view(), name='api-submission-detail'),

    # 用户主页
    path('users/<int:pk>/', UserProfileAPIView.as_view(), name='api-user-profile'),
    path('users/<int:pk>/stats/', UserStatsAPIView.as_view(), name='api-user-stats'),

    # 比赛
    path('contests/', ContestListAPIView.as_view(), name='api-contest-list'),
    path('contests/<int:pk>/', ContestDetailAPIView.as_view(), name='api-contest-detail'),
    path('contests/<int:pk>/register/', ContestRegisterAPIView.as_view(), name='api-contest-register'),
    path('contests/<int:pk>/rank/', ContestRankingAPIView.as_view(), name='api-contest-rank'),

    # 排行榜
    path('rank/', LeaderboardAPIView.as_view(), name='api-rank'),

    # 平台统计
    path('stats/', PlatformStatsAPIView.as_view(), name='api-stats'),

    # 讨论区
    path('discussions/', DiscussionListAPIView.as_view(), name='api-discussion-list'),
    path('discussions/create/', DiscussionCreateAPIView.as_view(), name='api-discussion-create'),
    path('discussions/<int:pk>/', DiscussionDetailAPIView.as_view(), name='api-discussion-detail'),
    path('discussions/<int:pk>/replies/', DiscussionReplyCreateAPIView.as_view(), name='api-discussion-reply'),
]
