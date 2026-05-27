from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Discussion, Problem
from ..forms import DiscussionForm, ReplyForm


def discussion_list(request):
    discussions = Discussion.objects.select_related('user', 'user__profile', 'problem')
    paginator = Paginator(discussions, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'judge/discussion_list.html', {'page_obj': page_obj})


def discussion_detail(request, discussion_id):
    discussion = get_object_or_404(
        Discussion.objects.select_related('user', 'user__profile', 'problem'),
        id=discussion_id,
    )
    Discussion.objects.filter(id=discussion_id).update(view_count=F('view_count') + 1)

    replies = discussion.replies.select_related('user', 'user__profile')
    reply_form = ReplyForm()

    if request.method == 'POST' and request.user.is_authenticated:
        reply_form = ReplyForm(request.POST)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.discussion = discussion
            reply.user = request.user
            reply.save()
            messages.success(request, '回复成功')
            return redirect('discussion_detail', discussion_id=discussion.id)

    context = {
        'discussion': discussion,
        'replies': replies,
        'reply_form': reply_form,
    }
    return render(request, 'judge/discussion_detail.html', context)


@login_required
def create_discussion(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            disc = form.save(commit=False)
            disc.user = request.user
            disc.problem = problem
            disc.save()
            messages.success(request, '帖子发布成功')
            return redirect('discussion_detail', discussion_id=disc.id)
    else:
        form = DiscussionForm()
    return render(request, 'judge/create_discussion.html', {'form': form, 'problem': problem})


@login_required
def create_discussion_general(request):
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            disc = form.save(commit=False)
            disc.user = request.user
            disc.save()
            messages.success(request, '帖子发布成功')
            return redirect('discussion_detail', discussion_id=disc.id)
    else:
        form = DiscussionForm()
    return render(request, 'judge/create_discussion.html', {'form': form, 'problem': None})
