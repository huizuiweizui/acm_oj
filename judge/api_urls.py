from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .team_api_views import (
    TeamListCreateAPIView, TeamDetailAPIView, TeamResetCodeAPIView,
    TeamPreviewAPIView, TeamJoinAPIView, TeamLeaveAPIView,
    TeamMembersAPIView, TeamMemberDetailAPIView,
    TeamRequestsAPIView, TeamRequestApproveAPIView, TeamRequestRejectAPIView,
    TeamRequestBatchApproveAPIView, MyRequestsAPIView,
    TeamSearchStudentAPIView, TeamAddStudentAPIView,
    TeamImportTemplateAPIView, TeamImportStudentsAPIView,
    TeamDashboardAPIView, TeamDashboardExportAPIView,
    TeamStudentDetailAPIView,
    AnnouncementListCreateAPIView, AnnouncementDetailAPIView,
    AssignmentListCreateAPIView, AssignmentDetailAPIView,
    TeamContestListCreateAPIView,
    DepartmentListCreateAPIView,
)
from .api_views import (
    AlgorithmListAPIView, AlgorithmDetailAPIView, AlgorithmChunksAPIView, AlgorithmGraphAPIView,
    AskAIAPIView,
    ChangePasswordAPIView,
    ContestCreateAPIView, ContestDetailAPIView, ContestListAPIView,
    ContestProblemPoolAPIView, ContestRankingAPIView, ContestRegisterAPIView,
    ContestFinalizeRatingAPIView, UserRatingHistoryAPIView,
    UserContestPermAPIView,
    DiscussionCreateAPIView, DiscussionDetailAPIView,
    DiscussionListAPIView, DiscussionReplyCreateAPIView, DiscussionReplyDeleteAPIView,
    LeaderboardAPIView,
    AdminStatsAPIView, AdminUserListAPIView, AdminUserUpdateAPIView, AdminTransferSuperAdminAPIView,
    LoginAPIView, LogoutAPIView, MeAPIView, PlatformStatsAPIView, ProblemDetailAPIView,
    ProblemListAPIView, RegisterAPIView,
    SubmissionListAPIView, SubmissionDetailAPIView,
    SubmitCodeAPIView, CustomRunAPIView, CustomRunStatusAPIView, HealthAPIView,
    UserProfileAPIView, UserStatsAPIView,
    UserDashboardAPIView,
    CheckInAPIView,
)
from .question_api_views import (
    QuestionListCreateAPIView, QuestionDetailAPIView, QuestionCheckAPIView,
)
from .exam_api_views import (
    ExamEnterAPIView, ExamPaperAPIView, ExamAnswerAPIView,
    ExamSubmitAPIView, ExamFocusLossAPIView,
    GradebookAPIView, GradebookExportAPIView, StudentResultAPIView,
    PlagiarismAPIView, PlagiarismPairAPIView,
)
from .list_api_views import (
    ProblemListListCreateAPIView, ProblemListDetailAPIView, ProblemListAddProblemAPIView,
)
from .community_api_views import (
    SolutionListCreateAPIView, SolutionDeleteAPIView,
    ProblemDistributionAPIView, DailyProblemAPIView,
)
from .learning_api_views import LearningPathAPIView
from .contest_extra_api_views import (
    ContestMyProgressAPIView, ContestVirtualStartAPIView, ContestVirtualStatusAPIView,
)

urlpatterns = [
    # 算法学习
    path('algorithms/', AlgorithmListAPIView.as_view(), name='api-algorithm-list'),
    path('algorithms/graph/', AlgorithmGraphAPIView.as_view(), name='api-algorithm-graph'),
    path('algorithms/<str:algo_id>/chunks/', AlgorithmChunksAPIView.as_view(), name='api-algorithm-chunks'),
    path('algorithms/<str:algo_id>/learning-path/', LearningPathAPIView.as_view(), name='api-learning-path'),
    path('algorithms/<str:algo_id>/', AlgorithmDetailAPIView.as_view(), name='api-algorithm-detail'),

    # 认证
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    path('auth/me/', MeAPIView.as_view(), name='api-me'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('auth/password/', ChangePasswordAPIView.as_view(), name='api-change-password'),

    # 题目
    path('problems/', ProblemListAPIView.as_view(), name='api-problem-list'),
    path('problems/<int:pk>/', ProblemDetailAPIView.as_view(), name='api-problem-detail'),
    path('problems/<int:pk>/submit/', SubmitCodeAPIView.as_view(), name='api-submit-code'),
    path('problems/<int:pk>/run/', CustomRunAPIView.as_view(), name='api-problem-run'),
    path('run-status/<str:task_id>/', CustomRunStatusAPIView.as_view(), name='api-run-status'),
    path('health/', HealthAPIView.as_view(), name='api-health'),

    # 客观题题库（考试 / 作业用）
    path('questions/', QuestionListCreateAPIView.as_view(), name='api-question-list'),
    path('questions/<int:pk>/', QuestionDetailAPIView.as_view(), name='api-question-detail'),
    path('questions/<int:pk>/check/', QuestionCheckAPIView.as_view(), name='api-question-check'),

    # 作业/考试答题（学生端）
    path('assignments/<int:aid>/enter/', ExamEnterAPIView.as_view(), name='api-exam-enter'),
    path('assignments/<int:aid>/paper/', ExamPaperAPIView.as_view(), name='api-exam-paper'),
    path('assignments/<int:aid>/answer/', ExamAnswerAPIView.as_view(), name='api-exam-answer'),
    path('assignments/<int:aid>/submit/', ExamSubmitAPIView.as_view(), name='api-exam-submit'),
    path('assignments/<int:aid>/focus-loss/', ExamFocusLossAPIView.as_view(), name='api-exam-focus-loss'),
    path('assignments/<int:aid>/gradebook/', GradebookAPIView.as_view(), name='api-gradebook'),
    path('assignments/<int:aid>/gradebook/export/', GradebookExportAPIView.as_view(), name='api-gradebook-export'),
    path('assignments/<int:aid>/students/<int:uid>/result/', StudentResultAPIView.as_view(), name='api-student-result'),
    path('assignments/<int:aid>/plagiarism/', PlagiarismAPIView.as_view(), name='api-plagiarism'),
    path('assignments/<int:aid>/plagiarism/pair/', PlagiarismPairAPIView.as_view(), name='api-plagiarism-pair'),

    # 题单 / 训练计划
    path('problem-lists/', ProblemListListCreateAPIView.as_view(), name='api-problem-lists'),
    path('problem-lists/<int:pk>/', ProblemListDetailAPIView.as_view(), name='api-problem-list-detail'),
    path('problem-lists/<int:pk>/add/', ProblemListAddProblemAPIView.as_view(), name='api-problem-list-add'),

    # 题解 / 提交分布 / 每日一题
    path('problems/<int:pk>/solutions/', SolutionListCreateAPIView.as_view(), name='api-solutions'),
    path('problems/<int:pk>/distribution/', ProblemDistributionAPIView.as_view(), name='api-distribution'),
    path('solutions/<int:pk>/', SolutionDeleteAPIView.as_view(), name='api-solution-delete'),
    path('daily-problem/', DailyProblemAPIView.as_view(), name='api-daily-problem'),

    # 提交记录
    path('submissions/', SubmissionListAPIView.as_view(), name='api-submission-list'),
    path('submissions/<int:pk>/', SubmissionDetailAPIView.as_view(), name='api-submission-detail'),

    # 用户主页
    path('users/<int:pk>/', UserProfileAPIView.as_view(), name='api-user-profile'),
    path('users/<int:pk>/stats/', UserStatsAPIView.as_view(), name='api-user-stats'),
    path('users/<int:pk>/contest-perm/', UserContestPermAPIView.as_view(), name='api-user-contest-perm'),
    path('users/<int:pk>/rating-history/', UserRatingHistoryAPIView.as_view(), name='api-user-rating-history'),

    # 比赛
    path('contests/', ContestListAPIView.as_view(), name='api-contest-list'),
    path('contests/create/', ContestCreateAPIView.as_view(), name='api-contest-create'),
    path('contests/problem-pool/', ContestProblemPoolAPIView.as_view(), name='api-contest-problem-pool'),
    path('contests/<int:pk>/', ContestDetailAPIView.as_view(), name='api-contest-detail'),
    path('contests/<int:pk>/register/', ContestRegisterAPIView.as_view(), name='api-contest-register'),
    path('contests/<int:pk>/rank/', ContestRankingAPIView.as_view(), name='api-contest-rank'),
    path('contests/<int:pk>/finalize-rating/', ContestFinalizeRatingAPIView.as_view(), name='api-contest-finalize-rating'),
    path('contests/<int:pk>/my-progress/', ContestMyProgressAPIView.as_view(), name='api-contest-my-progress'),
    path('contests/<int:pk>/virtual-start/', ContestVirtualStartAPIView.as_view(), name='api-contest-virtual-start'),
    path('contests/<int:pk>/virtual-status/', ContestVirtualStatusAPIView.as_view(), name='api-contest-virtual-status'),

    # 排行榜
    path('rank/', LeaderboardAPIView.as_view(), name='api-rank'),

    # 平台统计
    path('stats/', PlatformStatsAPIView.as_view(), name='api-stats'),

    # 用户仪表盘
    path('dashboard/', UserDashboardAPIView.as_view(), name='api-dashboard'),

    # 每日打卡
    path('checkin/', CheckInAPIView.as_view(), name='api-checkin'),

    # 管理员
    path('admin/stats/', AdminStatsAPIView.as_view(), name='api-admin-stats'),
    path('admin/users/', AdminUserListAPIView.as_view(), name='api-admin-users'),
    path('admin/users/<int:pk>/', AdminUserUpdateAPIView.as_view(), name='api-admin-user-update'),
    path('admin/transfer-super-admin/', AdminTransferSuperAdminAPIView.as_view(), name='api-transfer-super-admin'),

    # AI 问答（RAG）
    path('ai/ask/', AskAIAPIView.as_view(), name='api-ai-ask'),

    # 团队（班级）
    path('teams/', TeamListCreateAPIView.as_view(), name='api-team-list'),
    path('departments/', DepartmentListCreateAPIView.as_view(), name='api-departments'),
    path('teams/preview/', TeamPreviewAPIView.as_view(), name='api-team-preview'),
    path('teams/join/', TeamJoinAPIView.as_view(), name='api-team-join'),
    path('teams/<int:pk>/', TeamDetailAPIView.as_view(), name='api-team-detail'),
    path('teams/<int:pk>/reset-code/', TeamResetCodeAPIView.as_view(), name='api-team-reset-code'),
    path('teams/<int:pk>/leave/', TeamLeaveAPIView.as_view(), name='api-team-leave'),
    path('teams/<int:pk>/members/', TeamMembersAPIView.as_view(), name='api-team-members'),
    path('teams/<int:pk>/members/<int:user_id>/', TeamMemberDetailAPIView.as_view(), name='api-team-member-detail'),
    path('teams/<int:pk>/requests/', TeamRequestsAPIView.as_view(), name='api-team-requests'),
    path('teams/<int:pk>/requests/batch-approve/', TeamRequestBatchApproveAPIView.as_view(), name='api-team-batch-approve'),
    path('teams/<int:pk>/requests/<int:req_id>/approve/', TeamRequestApproveAPIView.as_view(), name='api-team-request-approve'),
    path('teams/<int:pk>/requests/<int:req_id>/reject/', TeamRequestRejectAPIView.as_view(), name='api-team-request-reject'),
    path('my-requests/', MyRequestsAPIView.as_view(), name='api-my-requests'),
    path('teams/<int:pk>/search-student/', TeamSearchStudentAPIView.as_view(), name='api-team-search-student'),
    path('teams/<int:pk>/add-student/', TeamAddStudentAPIView.as_view(), name='api-team-add-student'),
    path('teams/<int:pk>/import-template/', TeamImportTemplateAPIView.as_view(), name='api-team-import-template'),
    path('teams/<int:pk>/import-students/', TeamImportStudentsAPIView.as_view(), name='api-team-import-students'),
    path('teams/<int:pk>/dashboard/', TeamDashboardAPIView.as_view(), name='api-team-dashboard'),
    path('teams/<int:pk>/dashboard/export/', TeamDashboardExportAPIView.as_view(), name='api-team-dashboard-export'),
    path('teams/<int:pk>/students/<int:user_id>/', TeamStudentDetailAPIView.as_view(), name='api-team-student-detail'),
    path('teams/<int:pk>/announcements/', AnnouncementListCreateAPIView.as_view(), name='api-team-announcements'),
    path('teams/<int:pk>/announcements/<int:aid>/', AnnouncementDetailAPIView.as_view(), name='api-team-announcement-detail'),
    path('teams/<int:pk>/assignments/', AssignmentListCreateAPIView.as_view(), name='api-team-assignments'),
    path('teams/<int:pk>/assignments/<int:aid>/', AssignmentDetailAPIView.as_view(), name='api-team-assignment-detail'),
    path('teams/<int:pk>/contests/', TeamContestListCreateAPIView.as_view(), name='api-team-contests'),

    # 讨论区
    path('discussions/', DiscussionListAPIView.as_view(), name='api-discussion-list'),
    path('discussions/create/', DiscussionCreateAPIView.as_view(), name='api-discussion-create'),
    path('discussions/<int:pk>/', DiscussionDetailAPIView.as_view(), name='api-discussion-detail'),
    path('discussions/<int:pk>/replies/', DiscussionReplyCreateAPIView.as_view(), name='api-discussion-reply'),
    path('discussions/<int:pk>/replies/<int:reply_id>/', DiscussionReplyDeleteAPIView.as_view(), name='api-discussion-reply-delete'),
]
