"""测试基类与构造帮手。

模型字段较多且 UserProfile 没有 post_save 信号（必须显式建），
这里把这些琐碎的构造集中掉，测试本身只写关心的部分。
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from judge.models import (Contest, ContestParticipant, ContestProblem, Problem,
                          Submission, TestCase as TestCaseModel, UserProfile)


class OJTestCase(TestCase):

    # ── 用户 ────────────────────────────────────────────────────────────
    @staticmethod
    def make_user(username, role='student', **kwargs):
        user = User.objects.create_user(username=username, **kwargs)
        UserProfile.objects.update_or_create(user=user, defaults={'role': role})
        user.refresh_from_db()
        return user

    # ── 题目 ────────────────────────────────────────────────────────────
    @staticmethod
    def make_problem(title='测试题', published=True, **kwargs):
        defaults = dict(
            description='题面', input_desc='输入', output_desc='输出',
            sample_input='1 2', sample_output='3',
        )
        defaults.update(kwargs)
        return Problem.objects.create(title=title, is_published=published, **defaults)

    @staticmethod
    def add_testcases(problem, count=3):
        return [
            TestCaseModel.objects.create(
                problem=problem, input_data=str(i), expected_output=str(i), sort_order=i,
            )
            for i in range(count)
        ]

    # ── 比赛 ────────────────────────────────────────────────────────────
    @staticmethod
    def make_contest(title='测试赛', rule='ICPC', phase='running',
                     created_by=None, is_public=True, password=''):
        """phase: upcoming / running / ended"""
        now = timezone.now()
        windows = {
            'upcoming': (now + timedelta(hours=1), now + timedelta(hours=4)),
            'running': (now - timedelta(hours=1), now + timedelta(hours=2)),
            'ended': (now - timedelta(hours=5), now - timedelta(hours=1)),
        }
        start, end = windows[phase]
        return Contest.objects.create(
            title=title, start_time=start, end_time=end, rule_type=rule,
            created_by=created_by, is_public=is_public, password=password,
        )

    @staticmethod
    def add_contest_problem(contest, problem, label='A', order=0):
        return ContestProblem.objects.create(
            contest=contest, problem=problem, label=label, sort_order=order,
        )

    @staticmethod
    def register(contest, user):
        return ContestParticipant.objects.create(contest=contest, user=user)

    # ── 提交 ────────────────────────────────────────────────────────────
    @staticmethod
    def make_submission(user, problem, status='AC', score=100, contest=None,
                        minutes=None, code='int main(){}', **kwargs):
        """minutes：距开赛多少分钟。submitted_at 是 auto_now_add，只能建完再改。"""
        sub = Submission.objects.create(
            user=user, problem=problem, contest=contest, language='C++',
            code=code, status=status, score=score, **kwargs
        )
        if minutes is not None and contest is not None:
            Submission.objects.filter(id=sub.id).update(
                submitted_at=contest.start_time + timedelta(minutes=minutes)
            )
            sub.refresh_from_db()
        return sub
