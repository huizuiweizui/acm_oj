from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from ..models import Submission


def submission_list(request):
    """提交记录列表：登录时默认显示自己的，?all=1 显示全站"""
    submissions = Submission.objects.select_related('user', 'problem', 'user__profile')
    show_all = request.GET.get('all', '')
    if request.user.is_authenticated and not show_all:
        submissions = submissions.filter(user=request.user)

    paginator = Paginator(submissions, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'judge/submission_list.html', {'page_obj': page_obj, 'show_all': show_all})


def submission_detail(request, submission_id):
    submission = get_object_or_404(
        Submission.objects.select_related('problem', 'user', 'user__profile'),
        id=submission_id,
    )
    can_view_details = (
        request.user.is_authenticated
        and request.user.pk == submission.user_id
    )
    return render(request, 'judge/submission_detail.html', {
        'submission': submission,
        'can_view_details': can_view_details,
    })