"""评测引擎的纯逻辑：输出比对、测试点折算、比赛计分。"""
import shutil
import tempfile
from unittest import mock

from judge.models import ContestParticipant, Submission
from judge.services import judger
from judge.services.judger import (PROBLEM_FULL_SCORE, _normalize, _score_of,
                                   update_contest_score)

from .base import OJTestCase


def cases(*statuses):
    return [{'idx': i, 'status': s, 'time_ms': 1} for i, s in enumerate(statuses, 1)]


class NormalizeTests(OJTestCase):
    """输出比对的归一化。选手输出多个换行/行尾空格不该判 WA。"""

    def test_trailing_whitespace_ignored(self):
        self.assertEqual(_normalize('3   \n'), _normalize('3\n'))

    def test_trailing_newlines_ignored(self):
        self.assertEqual(_normalize('3\n\n\n'), _normalize('3'))

    def test_crlf_equals_lf(self):
        self.assertEqual(_normalize('1\r\n2\r\n'), _normalize('1\n2\n'))

    def test_lone_cr_equals_lf(self):
        self.assertEqual(_normalize('1\r2'), _normalize('1\n2'))

    def test_inner_blank_line_is_significant(self):
        self.assertNotEqual(_normalize('1\n\n2'), _normalize('1\n2'))

    def test_leading_whitespace_is_significant(self):
        self.assertNotEqual(_normalize('  3'), _normalize('3'))


class ScoreConversionTests(OJTestCase):
    """测试点 → 百分制。"""

    def test_all_passed_is_full_score(self):
        self.assertEqual(_score_of(cases(*['AC'] * 5)), PROBLEM_FULL_SCORE)

    def test_half_passed(self):
        self.assertEqual(_score_of(cases(*(['AC'] * 5 + ['WA'] * 5))), 50)

    def test_rounds_down_when_not_divisible(self):
        self.assertEqual(_score_of(cases('AC', 'WA', 'WA')), 33)
        self.assertEqual(_score_of(cases('AC', 'AC', 'WA')), 66)

    def test_none_passed(self):
        self.assertEqual(_score_of(cases(*['WA'] * 4)), 0)

    def test_non_ac_statuses_count_as_failed(self):
        self.assertEqual(_score_of(cases('AC', 'TLE', 'MLE', 'RE')), 25)

    def test_empty_means_zero(self):
        """编译失败 / 无测试点时 test_results 为空，不能崩也不能给分。"""
        self.assertEqual(_score_of([]), 0)

    def test_full_score_never_lost_to_rounding(self):
        """7/7 若按 int(100*7/7) 也是 100，但 3/3 这类必须确保不出现 99。"""
        for n in range(1, 40):
            self.assertEqual(_score_of(cases(*['AC'] * n)), PROBLEM_FULL_SCORE)


class TempDirCleanupTests(OJTestCase):
    """评测必须回收临时目录——否则一场比赛就能把评测机磁盘写满。"""

    def setUp(self):
        self.problem = self.make_problem(time_limit=1000, memory_limit=256)
        self.add_testcases(self.problem, 2)
        self.user = self.make_user('u1')

    def _run_with(self, compile_ok=True, run_side_effect=None):
        created = []
        real_mkdtemp = tempfile.mkdtemp

        def tracking_mkdtemp(*a, **kw):
            path = real_mkdtemp(*a, **kw)
            created.append(path)
            return path

        sub = self.make_submission(self.user, self.problem, status='Pending', score=0)
        with mock.patch.object(judger.tempfile, 'mkdtemp', tracking_mkdtemp), \
                mock.patch.object(judger, 'compile_code',
                                  return_value=(compile_ok, '' if compile_ok else 'CE')), \
                mock.patch.object(judger, 'run_code',
                                  side_effect=run_side_effect or
                                  (lambda *a, **k: (0, '0\n', '', False, False))), \
                mock.patch.object(judger, '_async_ai_feedback'):
            try:
                judger.judge_submission(sub, self.problem)
            except RuntimeError:
                pass                      # 故意抛的沙箱异常
        return created

    def _assert_all_cleaned(self, created):
        import os
        self.assertTrue(created, '应当创建过临时目录')
        leaked = [p for p in created if os.path.exists(p)]
        for p in leaked:                  # 别把垃圾留给下一次测试
            shutil.rmtree(p, ignore_errors=True)
        self.assertEqual(leaked, [], f'临时目录未回收: {leaked}')

    def test_cleaned_after_normal_run(self):
        self._assert_all_cleaned(self._run_with())

    def test_cleaned_after_compile_error(self):
        """CE 会提前 return，清理必须在 finally 里才跑得到。"""
        self._assert_all_cleaned(self._run_with(compile_ok=False))

    def test_cleaned_after_sandbox_exception(self):
        def boom(*a, **kw):
            raise RuntimeError('沙箱炸了')
        self._assert_all_cleaned(self._run_with(run_side_effect=boom))


class IcpcScoringTests(OJTestCase):
    """ICPC：首次 AC 计一题，罚时 = AC 时刻 + 之前错误次数 × 20。"""

    def setUp(self):
        self.contest = self.make_contest(rule='ICPC')
        self.problem = self.make_problem()
        self.add_contest_problem(self.contest, self.problem)
        self.user = self.make_user('alice')
        self.register(self.contest, self.user)

    def part(self):
        return ContestParticipant.objects.get(contest=self.contest, user=self.user)

    def test_first_ac_scores_with_penalty(self):
        self.make_submission(self.user, self.problem, 'WA', 0, self.contest, minutes=10)
        ac = self.make_submission(self.user, self.problem, 'AC', 100, self.contest, minutes=30)
        update_contest_score(ac)
        p = self.part()
        self.assertEqual(p.score, 1)
        self.assertEqual(p.penalty, 30 + 20, '一次错误 → 30 分钟 + 20 罚时')

    def test_second_ac_does_not_double_count(self):
        ac1 = self.make_submission(self.user, self.problem, 'AC', 100, self.contest, minutes=30)
        update_contest_score(ac1)
        ac2 = self.make_submission(self.user, self.problem, 'AC', 100, self.contest, minutes=40)
        update_contest_score(ac2)
        self.assertEqual(self.part().score, 1, '重复 AC 不应再加分')
        self.assertEqual(self.part().penalty, 30,
                         '罚时按首次 AC 计，第二次 AC 不应把罚时推到 40')

    def test_pending_submissions_are_not_penalised(self):
        """还没判完的提交不算错误次数，否则轮询期间罚时会虚高。"""
        self.make_submission(self.user, self.problem, 'Pending', 0, self.contest, minutes=5)
        ac = self.make_submission(self.user, self.problem, 'AC', 100, self.contest, minutes=20)
        update_contest_score(ac)
        self.assertEqual(self.part().penalty, 20)


class IoiScoringTests(OJTestCase):
    """IOI：每题取最高分之和，无罚时。"""

    def setUp(self):
        self.contest = self.make_contest(rule='IOI')
        self.pa = self.make_problem('A')
        self.pb = self.make_problem('B')
        self.add_contest_problem(self.contest, self.pa, 'A', 0)
        self.add_contest_problem(self.contest, self.pb, 'B', 1)
        self.user = self.make_user('alice')
        self.register(self.contest, self.user)

    def total(self):
        return ContestParticipant.objects.get(contest=self.contest, user=self.user).score

    def submit(self, problem, score, minutes, status='WA'):
        sub = self.make_submission(self.user, problem, status, score, self.contest,
                                   minutes=minutes)
        update_contest_score(sub)
        return sub

    def test_sums_best_per_problem(self):
        self.submit(self.pa, 100, 10, 'AC')
        self.submit(self.pb, 60, 20)
        self.assertEqual(self.total(), 160)

    def test_later_worse_submission_does_not_lower_total(self):
        """选手改崩了重交，总分不该掉——这正是 ICPC 式增量累加会算错的地方。"""
        self.submit(self.pa, 100, 10, 'AC')
        self.assertEqual(self.total(), 100)
        self.submit(self.pa, 30, 20)
        self.assertEqual(self.total(), 100)

    def test_improving_submission_raises_total(self):
        self.submit(self.pa, 40, 10)
        self.assertEqual(self.total(), 40)
        self.submit(self.pa, 100, 20, 'AC')
        self.assertEqual(self.total(), 100)

    def test_no_penalty_in_ioi(self):
        self.submit(self.pa, 50, 10)
        p = ContestParticipant.objects.get(contest=self.contest, user=self.user)
        self.assertEqual(p.penalty, 0)

    def test_problem_removed_from_contest_stops_counting(self):
        """题目被移出比赛后，旧提交不应继续贡献分数。"""
        self.submit(self.pa, 100, 10, 'AC')
        self.submit(self.pb, 50, 20)
        self.assertEqual(self.total(), 150)
        self.contest.contest_problems.filter(problem=self.pb).delete()
        self.submit(self.pa, 100, 30, 'AC')
        self.assertEqual(self.total(), 100)


class JudgeSubmissionScoreTests(OJTestCase):
    """评测结束时 score 必须落库，IOI 计分依赖它。"""

    def setUp(self):
        self.problem = self.make_problem()
        self.user = self.make_user('u2')

    def _judge(self, outputs):
        """outputs: 每个测试点返回的 stdout 列表"""
        self.add_testcases(self.problem, len(outputs))
        sub = self.make_submission(self.user, self.problem, status='Pending', score=0)
        it = iter(outputs)
        with mock.patch.object(judger, 'compile_code', return_value=(True, '')), \
                mock.patch.object(judger, 'run_code',
                                  side_effect=lambda *a, **k: (0, next(it), '', False, False)), \
                mock.patch.object(judger, '_async_ai_feedback'):
            judger.judge_submission(sub, self.problem)
        return Submission.objects.get(id=sub.id)

    def test_all_correct_scores_full(self):
        sub = self._judge(['0\n', '1\n', '2\n'])
        self.assertEqual(sub.status, 'AC')
        self.assertEqual(sub.score, 100)

    def test_partial_correct_scores_proportionally(self):
        sub = self._judge(['0\n', '999\n', '2\n'])
        self.assertEqual(sub.status, 'WA')
        self.assertEqual(sub.score, 66)

    def test_compile_error_scores_zero(self):
        self.add_testcases(self.problem, 2)
        sub = self.make_submission(self.user, self.problem, status='Pending', score=0)
        with mock.patch.object(judger, 'compile_code', return_value=(False, 'error')), \
                mock.patch.object(judger, '_async_ai_feedback'):
            judger.judge_submission(sub, self.problem)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'CE')
        self.assertEqual(sub.score, 0)
