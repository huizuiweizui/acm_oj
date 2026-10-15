"""题目改造链：生成 → 校验 → 修复闭环，以及大模型调用日志。"""
import copy
from unittest import mock

import requests

from star.content.levels import get_level, themed
from star.content.problems import get_problem
from star.models import AdaptedTask, LLMCallLog
from star.services import adapt, llm

from .base import LLM_OFF, LLM_ON, StarTestCase, llm_reply, patch_llm


def good_steps():
    out = copy.deepcopy(get_problem('sum_two')['default_steps'])
    out['analysis'] = '先理解读入，再写加法，最后排序。'
    out['title'] = '恐龙蛋相加'
    return out


def long_sentence_steps():
    out = good_steps()
    out['steps'][0]['prompt'] = '请你仔细想一想这个程序在一开始的时候最先需要完成的是哪一件事情'
    return out


@mock.patch('star.services.adapt.reference_passes', return_value=True)
class StepsLoopTests(StarTestCase):

    def setUp(self):
        self.make_profile(self.kid)
        self.task = AdaptedTask.objects.create(
            student=self.kid, layer='intro', template='sum_two', problem=self.make_problem_row(),
        )

    @LLM_ON
    def test_refine_after_rule_failure(self, _ref):
        with patch_llm(llm_reply(long_sentence_steps()), llm_reply(good_steps())) as post:
            adapt.generate(self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'draft')
        self.assertEqual(self.task.gen_count, 2)
        self.assertEqual(self.task.content['title'], '恐龙蛋相加')
        self.assertEqual([e['ok'] for e in self.task.validation_log], [False, True])
        # 第二次请求带上了上一次的输出和错误清单
        second = post.call_args_list[1].args[0]['messages']
        self.assertEqual(second[-2]['role'], 'assistant')
        self.assertIn('超过 20 字', second[-1]['content'])
        logs = list(LLMCallLog.objects.filter(task=self.task).order_by('attempt'))
        self.assertEqual([(g.attempt, g.passed) for g in logs], [(1, False), (2, True)])
        self.assertTrue(logs[0].checks['format_ok'])
        self.assertFalse(logs[0].checks['rules_ok'])
        self.assertEqual(logs[1].total_tokens, 150)

    @LLM_ON
    def test_three_failures_mark_failed_and_keep_last_output(self, _ref):
        bad = long_sentence_steps()
        with patch_llm(llm_reply('not json'), llm_reply(bad), llm_reply(bad)):
            adapt.generate(self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'failed')
        self.assertEqual(self.task.gen_count, 3)
        self.assertEqual(self.task.content['steps'][0]['prompt'], bad['steps'][0]['prompt'])
        first = self.task.validation_log[0]
        self.assertFalse(first['format_ok'])
        self.assertIn('不是合法的 JSON', first['errors'][0])

    @LLM_ON
    def test_json_in_code_fence_is_accepted(self, _ref):
        fenced = '```json\n' + llm_reply(good_steps())['choices'][0]['message']['content'] + '\n```'
        with patch_llm(llm_reply(fenced)):
            adapt.generate(self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'draft')

    @LLM_ON
    def test_network_error_is_retried_then_logged(self, _ref):
        with mock.patch('star.services.llm.time.sleep'), \
                patch_llm(requests.Timeout('slow'), requests.Timeout('slow'), requests.Timeout('slow'),
                          llm_reply(good_steps())):
            adapt.generate(self.task)
        self.task.refresh_from_db()
        # 第一轮网络重试 3 次都失败 → 记一条失败日志；第二轮成功
        self.assertEqual(self.task.status, 'draft')
        self.assertEqual(self.task.gen_count, 2)
        failed = LLMCallLog.objects.get(task=self.task, attempt=1)
        self.assertIn('Timeout', failed.error)
        self.assertFalse(failed.passed)

    @LLM_ON
    def test_reference_failure_is_material_error(self, ref):
        ref.return_value = False
        with patch_llm():
            with self.assertRaises(adapt.MaterialError):
                adapt.generate(self.task)

    @LLM_OFF
    def test_llm_mode_requires_configuration(self, _ref):
        with self.assertRaises(llm.LLMNotConfigured):
            adapt.generate(self.task)

    @LLM_OFF
    def test_template_mode_without_llm(self, _ref):
        adapt.generate(self.task, mode='template')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'draft')
        self.assertEqual(self.task.validation_log[-1]['mode'], 'template')
        self.assertEqual(LLMCallLog.objects.count(), 0)

    @LLM_ON
    def test_prompt_has_profile_and_reference_but_no_identity(self, _ref):
        with patch_llm(llm_reply(good_steps())) as post:
            adapt.generate(self.task)
        text = str(post.call_args.args[0]['messages'])
        self.assertIn('恐龙', text)                        # 画像里的兴趣
        self.assertIn('s = a + b', text)                   # 参考解
        self.assertNotIn(self.kid.username, text)          # 学生账号不出平台
        self.assertNotIn(f'{self.kid.username}昵称', text)


class LevelLoopTests(StarTestCase):

    def setUp(self):
        self.make_profile(self.kid2, layer='enlighten', theme_key='train')
        self.task = AdaptedTask.objects.create(student=self.kid2, layer='enlighten', template='L4')

    @LLM_ON
    def test_unsolvable_level_is_refined(self):
        good = dict(themed(get_level('L4'), 'train'), analysis='直线 5 格')
        bad = copy.deepcopy(good)
        bad['walls'] = [[3, 0], [3, 1], [3, 2]]           # 一堵墙把路堵死
        with patch_llm(llm_reply(bad), llm_reply(good)) as post:
            adapt.generate(self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'draft')
        self.assertIn('关卡无解', post.call_args_list[1].args[0]['messages'][-1]['content'])
        self.assertEqual(self.task.content['analysis'], '直线 5 格')
