"""首页今日推荐：作业优先、没通过的题重做、按水平与薄弱标签挑练习题、同一天结果稳定、接口权限。"""
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from judge.models import Assignment, AssignmentProblem, Submission, Tag, Team, TeamMembership
from judge.services.recommend import recommend_problems, user_level

from .base import OJTestCase


class RecommendTests(OJTestCase):

    def setUp(self):
        self.stu = self.make_user('stu')
        self.teacher = self.make_user('t', role='teacher')
        self.loop = Tag.objects.create(name='循环结构')
        self.branch = Tag.objects.create(name='分支结构')

    def prob(self, title, difficulty='入门', tags=(), **kw):
        p = self.make_problem(title, difficulty=difficulty, **kw)
        p.tags.set(tags)
        return p

    def submit(self, p, status='AC', days_ago=0):
        s = Submission.objects.create(user=self.stu, problem=p, code='x', status=status)
        if days_ago:
            Submission.objects.filter(pk=s.pk).update(submitted_at=timezone.now() - timedelta(days=days_ago))
        return s

    def ids(self, items):
        return [i['id'] for i in items]

    def test_new_user_gets_entry_problems(self):
        easy = [self.prob(f'入门{i}') for i in range(3)]
        self.prob('难题', difficulty='提高+/省选-')
        out = recommend_problems(self.stu)
        self.assertEqual(set(self.ids(out)), {p.id for p in easy})
        self.assertTrue(all(i['kind'] == 'practice' for i in out))
        self.assertIn('从入门题开始', out[0]['reason'])

    def test_solved_and_unpublished_are_excluded(self):
        a, b = self.prob('a'), self.prob('b')
        hidden = self.prob('hidden', published=False)
        self.submit(a)
        self.assertEqual(self.ids(recommend_problems(self.stu)), [b.id])
        self.assertNotIn(hidden.id, self.ids(recommend_problems(self.stu, n=5)))

    def test_assignment_comes_first(self):
        self.prob('练习题')
        hw, done = self.prob('作业题'), self.prob('作业里做过的')
        self.submit(done)
        team = Team.objects.create(name='一班', creator=self.teacher, invite_code='ABCD1234')
        TeamMembership.objects.create(team=team, user=self.stu)
        a = Assignment.objects.create(team=team, title='第一周', created_by=self.teacher,
                                      deadline=timezone.now() + timedelta(days=3, hours=1))
        AssignmentProblem.objects.create(assignment=a, problem=done, sort_order=0)
        AssignmentProblem.objects.create(assignment=a, problem=hw, sort_order=1)
        draft = Assignment.objects.create(team=team, title='草稿', created_by=self.teacher, is_active=False)
        AssignmentProblem.objects.create(assignment=draft, problem=self.prob('草稿题'))
        out = recommend_problems(self.stu)
        self.assertEqual(out[0]['id'], hw.id)
        self.assertEqual(out[0]['kind'], 'assignment')
        self.assertIn('《第一周》', out[0]['reason'])
        self.assertIn('还有 3 天截止', out[0]['reason'])
        self.assertNotIn(done.id, self.ids(out))

    def test_recent_failure_is_retried_once(self):
        wa1, wa2 = self.prob('wa1'), self.prob('wa2')
        old = self.prob('old')
        self.submit(wa1, 'WA', days_ago=2)
        self.submit(wa2, 'TLE', days_ago=1)
        self.submit(old, 'WA', days_ago=30)
        out = recommend_problems(self.stu)
        self.assertEqual(out[0]['id'], wa2.id)               # 最近的那道
        self.assertEqual(out[0]['kind'], 'retry')
        self.assertIn('TLE', out[0]['reason'])
        self.assertEqual(sum(1 for i in out if i['kind'] == 'retry'), 1)

    def test_weak_tag_is_preferred(self):
        failed = self.prob('循环没过', tags=[self.loop])
        self.submit(failed, 'WA', days_ago=30)               # 超出重做窗口，只算薄弱标签
        self.prob('分支题', tags=[self.branch])
        same = self.prob('循环题', tags=[self.loop])
        out = recommend_problems(self.stu, n=1)
        self.assertEqual(out[0]['id'], same.id)
        self.assertIn('「循环结构」类还有 1 道没通过', out[0]['reason'])

    def test_level_moves_up_after_enough_ac(self):
        for i in range(8):
            self.submit(self.prob(f'入门{i}'))
        self.prob('还剩的入门')
        harder = self.prob('普及-题', difficulty='普及-')
        self.assertEqual(user_level([s.problem for s in self.stu.submissions.all()])[0], 1)
        out = recommend_problems(self.stu, n=1)
        self.assertEqual(out[0]['id'], harder.id)

    def test_same_day_is_stable(self):
        for i in range(10):
            self.prob(f'题{i}')
        d = date(2026, 10, 17)
        self.assertEqual(self.ids(recommend_problems(self.stu, today=d)),
                         self.ids(recommend_problems(self.stu, today=d)))

    def test_api(self):
        p = self.prob('a')
        self.assertEqual(APIClient().get('/api/recommend/').status_code, 401)
        c = APIClient()
        c.force_authenticate(self.stu)
        r = c.get('/api/recommend/?n=2')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['items'][0]['id'], p.id)
        self.assertEqual(c.get('/api/recommend/?n=abc').status_code, 200)
