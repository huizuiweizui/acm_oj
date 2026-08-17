"""比赛榜单：ICPC 与 IOI 两套排序，以及各题格的内容。"""
from rest_framework.test import APIClient

from .base import OJTestCase


class IoiRankingTests(OJTestCase):

    def setUp(self):
        self.client = APIClient()
        self.contest = self.make_contest(rule='IOI', phase='ended')
        self.pa = self.make_problem('A')
        self.pb = self.make_problem('B')
        self.pc = self.make_problem('C')
        for i, p in enumerate((self.pa, self.pb, self.pc)):
            self.add_contest_problem(self.contest, p, 'ABC'[i], i)

        self.alice = self.make_user('alice')
        self.bob = self.make_user('bob')
        self.carol = self.make_user('carol')
        for u in (self.alice, self.bob, self.carol):
            self.register(self.contest, u)

    def submit(self, user, problem, score, minutes, status='WA'):
        from judge.services.judger import update_contest_score
        sub = self.make_submission(user, problem, status, score, self.contest,
                                   minutes=minutes)
        update_contest_score(sub)
        return sub

    def rank(self):
        return self.client.get(f'/api/contests/{self.contest.id}/rank/').data

    def test_ranking_sorts_by_score_then_time(self):
        # alice 与 bob 同为 160 分，但 bob 更早达成
        self.submit(self.alice, self.pa, 100, 20, 'AC')
        self.submit(self.alice, self.pb, 60, 40)
        self.submit(self.bob, self.pa, 100, 15, 'AC')
        self.submit(self.bob, self.pb, 60, 25)
        self.submit(self.carol, self.pc, 100, 5, 'AC')

        rows = self.rank()['ranked_users']
        self.assertEqual([r['username'] for r in rows], ['bob', 'alice', 'carol'])
        self.assertEqual([r['rank'] for r in rows], [1, 2, 3])
        self.assertEqual([r['score'] for r in rows], [160, 160, 100])
        self.assertEqual(rows[0]['time_min'], 25)
        self.assertEqual(rows[1]['time_min'], 40)

    def test_cell_keeps_best_score_and_first_time_reaching_it(self):
        self.submit(self.alice, self.pa, 40, 10)
        self.submit(self.alice, self.pa, 100, 20, 'AC')
        self.submit(self.alice, self.pa, 30, 30)      # 改崩了

        cell = next(r for r in self.rank()['ranked_users']
                    if r['username'] == 'alice')['problems']['A']
        self.assertEqual(cell['score'], 100)
        self.assertEqual(cell['attempts'], 3)
        self.assertEqual(cell['time_min'], 20,
                         '应记首次达到最高分的时刻，而非最后一次提交')

    def test_untouched_problem_cell_is_zero(self):
        self.submit(self.alice, self.pa, 100, 10, 'AC')
        cell = next(r for r in self.rank()['ranked_users']
                    if r['username'] == 'alice')['problems']['C']
        self.assertEqual(cell['score'], 0)
        self.assertEqual(cell['attempts'], 0)
        self.assertIsNone(cell['time_min'])

    def test_pending_submission_not_counted_as_attempt(self):
        self.make_submission(self.alice, self.pa, 'Pending', 0, self.contest, minutes=5)
        cell = next(r for r in self.rank()['ranked_users']
                    if r['username'] == 'alice')['problems']['A']
        self.assertEqual(cell['attempts'], 0)

    def test_solved_counts_full_score_problems(self):
        self.submit(self.alice, self.pa, 100, 10, 'AC')
        self.submit(self.alice, self.pb, 99, 20)
        row = next(r for r in self.rank()['ranked_users'] if r['username'] == 'alice')
        self.assertEqual(row['solved'], 1, '99 分不算"通过"')

    def test_response_exposes_full_score(self):
        self.assertEqual(self.rank()['full_score'], 100)

    def test_tie_shares_rank(self):
        self.submit(self.alice, self.pa, 100, 10, 'AC')
        self.submit(self.bob, self.pa, 100, 10, 'AC')
        rows = self.rank()['ranked_users']
        self.assertEqual(rows[0]['rank'], 1)
        self.assertEqual(rows[1]['rank'], 1, '同分同时刻应并列')


class IcpcRankingTests(OJTestCase):
    """ICPC 榜不应被 IOI 分支影响。"""

    def setUp(self):
        self.client = APIClient()
        self.contest = self.make_contest(rule='ICPC', phase='ended')
        self.pa = self.make_problem('A')
        self.add_contest_problem(self.contest, self.pa, 'A', 0)
        self.alice = self.make_user('alice')
        self.register(self.contest, self.alice)

    def test_icpc_shape_unchanged(self):
        self.make_submission(self.alice, self.pa, 'WA', 0, self.contest, minutes=10)
        self.make_submission(self.alice, self.pa, 'AC', 100, self.contest, minutes=30)

        data = self.client.get(f'/api/contests/{self.contest.id}/rank/').data
        row = data['ranked_users'][0]
        self.assertEqual(row['solved'], 1)
        self.assertEqual(row['penalty'], 30 + 20)
        self.assertTrue(row['problems']['A']['ac'])
        self.assertEqual(row['problems']['A']['wrong_count'], 1)
        self.assertNotIn('full_score', data, 'ICPC 响应不应带 IOI 的满分字段')
