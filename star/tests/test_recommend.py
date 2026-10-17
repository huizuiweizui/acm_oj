"""推荐下一项任务：规则分支的知识点顺序、大模型分支的校验与修复、兜底、身份信息不出平台、接口权限。"""
import json

from star.models import LLMCallLog, StepAttempt
from star.services import recommend

from .base import LLM_OFF, LLM_ON, StarTestCase, llm_reply, patch_llm
from .test_api import api


def solve(task, hint=0, wrong=0, steps=None):
    """把任务的前 steps 步（默认全部）按给定提示等级做对，每步做对前先错 wrong 次。"""
    for i in range(steps if steps is not None else len(task.content['steps'])):
        for _ in range(wrong):
            StepAttempt.objects.create(task=task, step_index=i, is_correct=False, hint_level=hint)
        StepAttempt.objects.create(task=task, step_index=i, is_correct=True, hint_level=hint)


class RuleTests(StarTestCase):

    def setUp(self):
        self.lp = self.make_profile(self.kid, nickname='阿杰')

    def keys(self, out):
        return [i['material'] for i in out['items']]

    @LLM_OFF
    def test_no_data_starts_from_sequence(self):
        out = recommend.recommend(self.lp)
        self.assertEqual(out['source'], 'rule')
        self.assertEqual(self.keys(out), ['sum_two', 'double', 'minutes'])
        self.assertIn('从顺序开始', out['summary'])

    @LLM_OFF
    def test_mastered_sequence_moves_to_condition(self):
        solve(self.make_steps_task(self.kid, 'sum_two'), hint=0)
        out = recommend.recommend(self.lp)
        self.assertTrue(all(i['knowledge'] == 'condition' for i in out['items']))
        self.assertIn('顺序已掌握，进入条件', out['summary'])
        self.assertEqual(out['items'][0]['mode'], 'template')

    @LLM_OFF
    def test_weak_knowledge_is_practised_again(self):
        solve(self.make_steps_task(self.kid, 'sum_two'), hint=3)
        out = recommend.recommend(self.lp)
        self.assertNotIn('sum_two', self.keys(out))          # 布置过的不再推荐
        self.assertEqual(self.keys(out), ['double', 'minutes', 'rect_area'])
        self.assertIn('平均提示等级 3', out['items'][0]['reason'])
        self.assertEqual(out['items'][0]['mode'], 'llm')     # 提示用得多，建议个性化改造

    @LLM_OFF
    def test_enlighten_uses_levels(self):
        lp = self.make_profile(self.kid2, layer='enlighten')
        out = recommend.recommend(lp)
        self.assertEqual(self.keys(out), ['L1', 'L2', 'L3'])

    @LLM_OFF
    def test_many_wrong_attempts_count_as_weak(self):
        solve(self.make_steps_task(self.kid, 'sum_two'), hint=0, wrong=3)   # 不看提示，但每步错 3 次
        out = recommend.recommend(self.lp)
        self.assertEqual(out['mastery']['sequence']['status'], 'weak')
        self.assertTrue(all(i['knowledge'] == 'sequence' for i in out['items']))
        self.assertIn('错的次数较多', out['items'][0]['reason'])
        self.assertEqual(out['items'][0]['mode'], 'llm')

    @LLM_OFF
    def test_recent_steps_weigh_more(self):
        # 早期两题看完整示范，后来两题不看提示：平均提示等级 1.5，但最近已经能独立完成
        for slug, hint in (('sum_two', 3), ('double', 3), ('minutes', 0), ('rect_area', 0)):
            solve(self.make_steps_task(self.kid, slug), hint=hint)
        out = recommend.recommend(self.lp)
        self.assertGreater(out['mastery']['sequence']['avg_hint'], recommend.MASTER_HINT)
        self.assertEqual(out['mastery']['sequence']['status'], 'mastered')
        self.assertTrue(all(i['knowledge'] == 'condition' for i in out['items']))

    @LLM_OFF
    def test_learning_keeps_one_preview_and_notes_unfinished(self):
        solve(self.make_steps_task(self.kid, 'sum_two'))
        solve(self.make_steps_task(self.kid, 'max_two'), steps=2)          # 条件只做对 2 步，任务没做完
        out = recommend.recommend(self.lp)
        self.assertEqual(out['mastery']['condition']['status'], 'learning')
        self.assertEqual([i['knowledge'] for i in out['items']], ['condition', 'condition', 'loop'])
        self.assertEqual(out['items'][2]['material'], 'count_up')       # 只用到循环的最简单的一道
        self.assertIn('预习', out['items'][2]['reason'])
        self.assertIn('1 个已布置的任务还没做完', out['summary'])

    @LLM_OFF
    def test_missing_prerequisite_goes_last(self):
        cands = recommend.candidates(self.lp)
        stats = recommend.learner_stats(self.kid)
        m = recommend.mastery(stats, recommend.ORDER['intro'])
        recommend.TOP_N, old = len(cands), recommend.TOP_N
        try:
            items, _ = recommend.rule_recommend(self.lp, stats, cands, m)
        finally:
            recommend.TOP_N = old
        keys = [i['material'] for i in items]
        # 还没学条件和循环："1 加到 n""偶数之和"等跨类素材排在只用一类知识点的素材后面
        self.assertGreater(keys.index('sum_even'), keys.index('stars'))
        self.assertIn('前置还不够', items[keys.index('sum_even')]['reason'])

    @LLM_OFF
    def test_all_mastered_recommends_combined_tasks(self):
        for slug in ('sum_two', 'odd_even', 'count_up'):
            solve(self.make_steps_task(self.kid, slug))
        out = recommend.recommend(self.lp)
        self.assertTrue(all(v['status'] == 'mastered' for v in out['mastery'].values()))
        self.assertIn(out['items'][0]['material'], {'sum_to_n', 'times_table', 'sum_even'})
        self.assertIn('综合题', out['summary'])


GOOD = {'summary': '{name}还没开始，先从顺序类入门。',
        'items': [{'material': 'double', 'reason': '{name}喜欢恐龙，两倍题最短，先建立信心', 'mode': 'llm'},
                  {'material': 'sum_two', 'reason': '演示题，读入和输出最基础', 'mode': 'template'}]}


class LLMTests(StarTestCase):

    def setUp(self):
        self.lp = self.make_profile(self.kid, nickname='阿杰')

    @LLM_ON
    def test_llm_is_primary_and_rule_kept_for_comparison(self):
        with patch_llm(llm_reply(GOOD)) as post:
            out = recommend.recommend(self.lp)
        self.assertEqual(out['source'], 'llm')
        self.assertEqual([i['material'] for i in out['items']], ['double', 'sum_two'])
        self.assertEqual(out['summary'], '阿杰还没开始，先从顺序类入门。')
        self.assertTrue(out['items'][0]['reason'].startswith('阿杰喜欢恐龙'))
        self.assertEqual(out['rule']['items'][0]['material'], 'sum_two')
        prompt = json.dumps(post.call_args.args[0]['messages'], ensure_ascii=False)
        self.assertIn('规则算法的建议', prompt)
        self.assertIn('mastery', prompt)                    # 掌握度也给大模型看
        self.assertNotIn('阿杰', prompt)
        self.assertNotIn(self.kid.username, prompt)
        log = LLMCallLog.objects.get(purpose='P6')
        self.assertTrue(log.passed)

    @LLM_ON
    def test_invalid_output_is_repaired_once(self):
        bad = {'summary': '好', 'items': [{'material': 'not_exist', 'reason': '随便', 'mode': 'llm'}]}
        with patch_llm(llm_reply(bad), llm_reply(GOOD)) as post:
            out = recommend.recommend(self.lp)
        self.assertEqual(out['source'], 'llm')
        repair = post.call_args_list[1].args[0]['messages'][-1]['content']
        self.assertIn('不在候选素材里', repair)
        self.assertEqual(list(LLMCallLog.objects.filter(purpose='P6').order_by('attempt')
                              .values_list('passed', flat=True)), [False, True])

    @LLM_ON
    def test_falls_back_to_rule_after_two_failures(self):
        with patch_llm(llm_reply('不是 JSON'), llm_reply({'items': []})):
            out = recommend.recommend(self.lp)
        self.assertEqual(out['source'], 'rule')
        self.assertEqual(out['items'], out['rule']['items'])
        self.assertIn('未通过校验', out['note'])

    @LLM_ON
    def test_already_assigned_material_is_rejected(self):
        self.make_steps_task(self.kid, 'double')
        items, _, errors = recommend.check(GOOD, recommend.candidates(self.lp))
        self.assertEqual([i['material'] for i in items], ['sum_two'])
        self.assertTrue(any('double' in e for e in errors))

    @LLM_OFF
    def test_api_permissions(self):
        url = f'/api/star/teacher/learners/{self.kid.id}/recommend/'
        r = api(self.teacher).post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['source'], 'rule')
        self.assertEqual(r.json()['mastery']['sequence']['status'], 'new')
        self.assertEqual(api(self.other_teacher).post(url).status_code, 404)
        self.assertEqual(api(self.kid).post(url).status_code, 403)
