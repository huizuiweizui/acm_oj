from django.urls import path

from . import views

urlpatterns = [
    # 学生端
    path('me/', views.MeView.as_view(), name='star-me'),
    path('survey/', views.SurveyView.as_view(), name='star-survey'),
    path('dialogue/', views.DialogueView.as_view(), name='star-dialogue'),
    path('tasks/', views.MyTasksView.as_view(), name='star-tasks'),
    path('tasks/<int:pk>/', views.MyTaskDetailView.as_view(), name='star-task'),
    path('tasks/<int:pk>/hint/', views.HintView.as_view(), name='star-task-hint'),
    path('tasks/<int:pk>/attempt/', views.AttemptView.as_view(), name='star-task-attempt'),
    path('chat/', views.ChatView.as_view(), name='star-chat'),

    # 教师端
    path('teacher/learners/', views.LearnerListView.as_view(), name='star-t-learners'),
    path('teacher/learners/<int:uid>/', views.LearnerDetailView.as_view(), name='star-t-learner'),
    path('teacher/learners/<int:uid>/profile/', views.ProfileRegenerateView.as_view(), name='star-t-profile'),
    path('teacher/learners/<int:uid>/tasks/', views.TaskCreateView.as_view(), name='star-t-task-create'),
    path('teacher/learners/<int:uid>/report/', views.ReportView.as_view(), name='star-t-report'),
    path('teacher/materials/', views.MaterialsView.as_view(), name='star-t-materials'),
    path('teacher/tasks/<int:pk>/', views.TaskDetailView.as_view(), name='star-t-task'),
    path('teacher/tasks/<int:pk>/approve/', views.TaskApproveView.as_view(), name='star-t-task-approve'),
    path('teacher/tasks/<int:pk>/regenerate/', views.TaskRegenerateView.as_view(), name='star-t-task-regen'),
]
