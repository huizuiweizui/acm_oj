"""权限判定：提交源码可见性、赛题访问、比赛管理。"""
from django.contrib.auth.models import AnonymousUser

from judge.permissions import (can_access_problem, can_manage_contest,
                               can_view_submission_code, contest_problems_visible)

from .base import OJTestCase


class SubmissionCodeVisibilityTests(OJTestCase):
    """源码只对本人 / 教师 / 管理员可见。"""

    def setUp(self):
        self.owner = self.make_user('owner')
        self.other = self.make_user('other')
        self.teacher = self.make_user('teacher', role='teacher')
        self.admin = self.make_user('admin', role='admin')
        self.superuser = self.make_user('root', is_superuser=True)
        self.problem = self.make_problem()
        self.sub = self.make_submission(self.owner, self.problem)

    def test_anonymous_cannot_view(self):
        self.assertFalse(can_view_submission_code(AnonymousUser(), self.sub))

    def test_none_user_cannot_view(self):
        self.assertFalse(can_view_submission_code(None, self.sub))

    def test_other_student_cannot_view(self):
        self.assertFalse(can_view_submission_code(self.other, self.sub))

    def test_owner_can_view(self):
        self.assertTrue(can_view_submission_code(self.owner, self.sub))

    def test_teacher_can_view(self):
        self.assertTrue(can_view_submission_code(self.teacher, self.sub))

    def test_admin_can_view(self):
        self.assertTrue(can_view_submission_code(self.admin, self.sub))

    def test_superuser_can_view(self):
        self.assertTrue(can_view_submission_code(self.superuser, self.sub))

    def test_user_without_profile_is_treated_as_student(self):
        """历史数据里可能有没建 profile 的用户，不能因此报错或放行。"""
        from django.contrib.auth.models import User
        bare = User.objects.create_user(username='bare')
        self.assertFalse(can_view_submission_code(bare, self.sub))


class ProblemAccessTests(OJTestCase):
    """未公开赛题：赛中放行给已报名者，赛前赛后锁住；管理者始终可预览。"""

    def setUp(self):
        self.author = self.make_user('author')
        self.player = self.make_user('player')
        self.stranger = self.make_user('stranger')
        self.teacher = self.make_user('teacher', role='teacher')

    def _setup(self, phase):
        contest = self.make_contest(phase=phase, created_by=self.author)
        secret = self.make_problem('赛题', published=False)
        self.add_contest_problem(contest, secret)
        self.register(contest, self.player)
        return contest, secret

    def test_published_problem_is_public(self):
        prob = self.make_problem(published=True)
        for user in (AnonymousUser(), self.stranger, self.player):
            self.assertTrue(can_access_problem(user, prob))

    def test_unpublished_locked_before_contest(self):
        _, secret = self._setup('upcoming')
        self.assertFalse(can_access_problem(AnonymousUser(), secret))
        self.assertFalse(can_access_problem(self.stranger, secret))
        self.assertFalse(can_access_problem(self.player, secret),
                         '赛前连已报名者也不该看到题面')

    def test_unpublished_open_to_participant_during_contest(self):
        _, secret = self._setup('running')
        self.assertTrue(can_access_problem(self.player, secret))
        self.assertFalse(can_access_problem(self.stranger, secret))
        self.assertFalse(can_access_problem(AnonymousUser(), secret))

    def test_unpublished_locked_again_after_contest(self):
        _, secret = self._setup('ended')
        self.assertFalse(can_access_problem(self.player, secret),
                         '赛后题目仍未公开时，选手不该还能打开')

    def test_author_and_teacher_can_always_preview(self):
        for phase in ('upcoming', 'running', 'ended'):
            _, secret = self._setup(phase)
            self.assertTrue(can_access_problem(self.author, secret), phase)
            self.assertTrue(can_access_problem(self.teacher, secret), phase)

    def test_publishing_after_contest_restores_public_access(self):
        _, secret = self._setup('ended')
        secret.is_published = True
        secret.save(update_fields=['is_published'])
        self.assertTrue(can_access_problem(self.stranger, secret))


class ContestProblemListVisibilityTests(OJTestCase):
    """题目清单：赛前仅管理者，赛中限已报名，赛后放开。"""

    def setUp(self):
        self.author = self.make_user('author')
        self.player = self.make_user('player')
        self.stranger = self.make_user('stranger')
        self.teacher = self.make_user('teacher', role='teacher')

    def _contest(self, phase):
        contest = self.make_contest(phase=phase, created_by=self.author)
        self.register(contest, self.player)
        return contest

    def test_upcoming_hidden_from_everyone_but_managers(self):
        c = self._contest('upcoming')
        self.assertFalse(contest_problems_visible(AnonymousUser(), c))
        self.assertFalse(contest_problems_visible(self.stranger, c))
        self.assertFalse(contest_problems_visible(self.player, c))
        self.assertTrue(contest_problems_visible(self.author, c))
        self.assertTrue(contest_problems_visible(self.teacher, c))

    def test_running_visible_to_registered_only(self):
        c = self._contest('running')
        self.assertTrue(contest_problems_visible(self.player, c))
        self.assertFalse(contest_problems_visible(self.stranger, c))
        self.assertFalse(contest_problems_visible(AnonymousUser(), c))

    def test_ended_visible_to_all(self):
        c = self._contest('ended')
        self.assertTrue(contest_problems_visible(AnonymousUser(), c))
        self.assertTrue(contest_problems_visible(self.stranger, c))


class ContestManageTests(OJTestCase):

    def setUp(self):
        self.author = self.make_user('author')
        self.contest = self.make_contest(created_by=self.author)

    def test_creator_can_manage(self):
        self.assertTrue(can_manage_contest(self.author, self.contest))

    def test_teacher_and_admin_can_manage(self):
        self.assertTrue(can_manage_contest(self.make_user('t', role='teacher'), self.contest))
        self.assertTrue(can_manage_contest(self.make_user('a', role='admin'), self.contest))

    def test_student_and_anonymous_cannot(self):
        self.assertFalse(can_manage_contest(self.make_user('s'), self.contest))
        self.assertFalse(can_manage_contest(AnonymousUser(), self.contest))
