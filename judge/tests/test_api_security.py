"""接口层的安全边界：源码不外泄、赛题不早泄、私有赛要密码。

用 DRF 的 APIClient 走真实路由，确保拦截真的发生在接口上而不只是 helper 里。
"""
from rest_framework.test import APIClient

from judge.models import Submission

from .base import OJTestCase


class SubmissionCodeLeakTests(OJTestCase):
    """回归：GET /api/submissions/?all=1 曾能翻出全站每个人的源码。"""

    SECRET = '#include <bits/stdc++.h>\n// 我的解法'

    def setUp(self):
        self.client = APIClient()
        self.owner = self.make_user('owner')
        self.other = self.make_user('other')
        self.teacher = self.make_user('teacher', role='teacher')
        self.problem = self.make_problem()
        self.sub = self.make_submission(
            self.owner, self.problem, code=self.SECRET,
            error_info='main.cpp:3 error: 这里会带出源码片段',
            ai_feedback='你用了双指针……',
        )

    def test_list_never_includes_code(self):
        for who in (None, self.owner, self.teacher):
            if who:
                self.client.force_authenticate(user=who)
            else:
                self.client.force_authenticate(user=None)
            resp = self.client.get('/api/submissions/', {'all': 1})
            self.assertEqual(resp.status_code, 200)
            rows = resp.data['results']
            self.assertTrue(rows)
            for field in ('code', 'error_info', 'ai_feedback'):
                self.assertNotIn(field, rows[0], f'列表泄漏了 {field}（登录者={who}）')

    def test_list_body_does_not_contain_secret(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/submissions/', {'all': 1})
        self.assertNotIn('bits/stdc++', str(resp.data))

    def test_detail_hides_private_fields_from_anonymous(self):
        self.client.force_authenticate(user=None)
        data = self.client.get(f'/api/submissions/{self.sub.id}/').data
        self.assertEqual(data['code'], '')
        self.assertEqual(data['error_info'], '')
        self.assertEqual(data['ai_feedback'], '')
        self.assertEqual(data['status'], 'AC', '评测结果本身仍应公开')

    def test_detail_hides_code_from_other_student(self):
        self.client.force_authenticate(user=self.other)
        data = self.client.get(f'/api/submissions/{self.sub.id}/').data
        self.assertEqual(data['code'], '')

    def test_owner_sees_own_code(self):
        self.client.force_authenticate(user=self.owner)
        data = self.client.get(f'/api/submissions/{self.sub.id}/').data
        self.assertEqual(data['code'], self.SECRET)

    def test_teacher_sees_student_code(self):
        self.client.force_authenticate(user=self.teacher)
        data = self.client.get(f'/api/submissions/{self.sub.id}/').data
        self.assertEqual(data['code'], self.SECRET)

    def test_user_profile_recent_submissions_have_no_code(self):
        """个人主页曾是第三个泄漏点。"""
        self.client.force_authenticate(user=None)
        data = self.client.get(f'/api/users/{self.owner.id}/').data
        self.assertTrue(data['recent_submissions'])
        self.assertNotIn('code', data['recent_submissions'][0])


class ProblemAccessApiTests(OJTestCase):
    """未公开赛题在接口层的放行规则。"""

    def setUp(self):
        self.client = APIClient()
        self.author = self.make_user('author')
        self.player = self.make_user('player')
        self.stranger = self.make_user('stranger')

    def _setup(self, phase):
        contest = self.make_contest(phase=phase, created_by=self.author)
        secret = self.make_problem('赛题', published=False)
        self.add_contest_problem(contest, secret)
        self.register(contest, self.player)
        return contest, secret

    def test_participant_can_open_during_contest(self):
        _, secret = self._setup('running')
        self.client.force_authenticate(user=self.player)
        resp = self.client.get(f'/api/problems/{secret.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['description'], '题面')

    def test_stranger_gets_404_during_contest(self):
        _, secret = self._setup('running')
        self.client.force_authenticate(user=self.stranger)
        self.assertEqual(self.client.get(f'/api/problems/{secret.id}/').status_code, 404)

    def test_participant_gets_404_before_contest(self):
        _, secret = self._setup('upcoming')
        self.client.force_authenticate(user=self.player)
        self.assertEqual(self.client.get(f'/api/problems/{secret.id}/').status_code, 404)

    def test_unpublished_problem_absent_from_problem_list(self):
        """赛题不该混进普通题库被搜到，即使自己已报名。"""
        _, secret = self._setup('running')
        self.client.force_authenticate(user=self.player)
        ids = [p['id'] for p in self.client.get('/api/problems/').data['results']]
        self.assertNotIn(secret.id, ids)

    def test_submit_blocked_for_stranger(self):
        _, secret = self._setup('running')
        self.client.force_authenticate(user=self.stranger)
        resp = self.client.post(f'/api/problems/{secret.id}/submit/',
                                {'language': 'C++', 'code': 'int main(){}'}, format='json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Submission.objects.count(), 0)

    def test_submit_blocked_before_contest(self):
        _, secret = self._setup('upcoming')
        self.client.force_authenticate(user=self.player)
        resp = self.client.post(f'/api/problems/{secret.id}/submit/',
                                {'language': 'C++', 'code': 'int main(){}'}, format='json')
        self.assertEqual(resp.status_code, 404)


class ContestDetailVisibilityApiTests(OJTestCase):

    def setUp(self):
        self.client = APIClient()
        self.author = self.make_user('author')
        self.stranger = self.make_user('stranger')

    def _contest(self, phase):
        contest = self.make_contest(phase=phase, created_by=self.author)
        self.add_contest_problem(contest, self.make_problem('机密题名', published=False))
        return contest

    def test_upcoming_hides_titles_but_reports_count(self):
        contest = self._contest('upcoming')
        self.client.force_authenticate(user=self.stranger)
        data = self.client.get(f'/api/contests/{contest.id}/').data
        self.assertFalse(data['problems_visible'])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['problem_count'], 1, '数量仍应告知，供前端占位')
        self.assertNotIn('机密题名', str(data))

    def test_ended_contest_lists_problems(self):
        contest = self._contest('ended')
        self.client.force_authenticate(user=self.stranger)
        data = self.client.get(f'/api/contests/{contest.id}/').data
        self.assertTrue(data['problems_visible'])
        self.assertEqual(len(data['problems']), 1)


class ContestRegisterPasswordTests(OJTestCase):
    """私有赛密码。可见性挂在报名上，这道闸放开等于私有赛形同虚设。"""

    def setUp(self):
        self.client = APIClient()
        self.author = self.make_user('author')
        self.outsider = self.make_user('outsider')

    def _register(self, contest, user, password=None):
        self.client.force_authenticate(user=user)
        body = {} if password is None else {'password': password}
        return self.client.post(f'/api/contests/{contest.id}/register/', body, format='json')

    def test_public_contest_needs_no_password(self):
        c = self.make_contest(is_public=True, created_by=self.author)
        self.assertIn(self._register(c, self.outsider).status_code, (200, 201))

    def test_private_contest_rejects_missing_password(self):
        c = self.make_contest(is_public=False, password='letmein', created_by=self.author)
        self.assertEqual(self._register(c, self.outsider).status_code, 403)

    def test_private_contest_rejects_wrong_password(self):
        c = self.make_contest(is_public=False, password='letmein', created_by=self.author)
        self.assertEqual(self._register(c, self.outsider, 'nope').status_code, 403)

    def test_private_contest_accepts_correct_password(self):
        c = self.make_contest(is_public=False, password='letmein', created_by=self.author)
        self.assertIn(self._register(c, self.outsider, 'letmein').status_code, (200, 201))

    def test_private_without_password_only_manager_can_join(self):
        c = self.make_contest(is_public=False, password='', created_by=self.author)
        self.assertEqual(self._register(c, self.outsider).status_code, 403)
        self.assertIn(self._register(c, self.author).status_code, (200, 201))

    def test_rejected_registration_grants_no_problem_access(self):
        c = self.make_contest(is_public=False, password='letmein',
                              phase='running', created_by=self.author)
        secret = self.make_problem('赛题', published=False)
        self.add_contest_problem(c, secret)
        self._register(c, self.outsider, 'wrong')
        self.client.force_authenticate(user=self.outsider)
        self.assertEqual(self.client.get(f'/api/problems/{secret.id}/').status_code, 404)
