"""消融实验命令：用打桩的大模型各跑一个样本，确认流程能走通、结果文件能写出来。"""
import copy
import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from star.content.levels import LEVELS, themed
from star.content.problems import PROBLEMS
from star.models import AdaptedTask, LLMCallLog

from .base import LLM_OFF, LLM_ON, StarTestCase, llm_reply


def fake_post(payload):
    system = payload['messages'][0]['content']
    if '【关卡规则】' in system:
        return llm_reply(themed(LEVELS[0], 'train'))
    if '【分步任务规则】' in system:
        return llm_reply(copy.deepcopy(PROBLEMS[0]['default_steps']))
    return llm_reply({'intent': 'echo', 'reply': '请点一个按钮。', 'options': ['看提示', '再试一次']})


class EvalCommandTests(TestCase):

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix='star_eval_test_'))
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)

    def run_exp(self, name):
        call_command('star_eval', name, limit=1, out=str(self.out), stdout=StringIO())
        found = list(self.out.glob(f'{name}-*/summary.json'))
        self.assertEqual(len(found), 1)
        return json.loads(found[0].read_text(encoding='utf-8'))

    @LLM_ON
    @mock.patch('star.services.llm._post', side_effect=fake_post)
    def test_all_experiments_run(self, _post):
        s = self.run_exp('adapt')
        self.assertEqual(s['samples'], 2)                         # 1 题 × 2 个画像
        self.assertEqual(s['生成-校验-修复闭环']['规则通过率%'], 100.0)
        self.assertLess(s['平均句长（字）']['改写后'], s['平均句长（字）']['改写前（原题）'])

        s = self.run_exp('levels')
        self.assertEqual(s['BFS校验并重新生成']['可解率%'], 100.0)

        s = self.run_exp('intent')
        self.assertEqual(s['总体']['开启%'], 100.0)               # 第 1 条是仿说，打桩回复的 intent 恰为 echo
        self.assertFalse(s['labels_reviewed'])

        s = self.run_exp('consistency')
        sims = s['平均两两相似度']
        self.assertEqual(sims['低温度加缓存'], 1.0)

        s = self.run_exp('logs')
        self.assertEqual(s['total_calls'], LLMCallLog.objects.count())
        self.assertTrue(LLMCallLog.objects.filter(tag='eval:adapt:loop').exists())

    @LLM_OFF
    def test_requires_llm(self):
        with self.assertRaises(CommandError):
            call_command('star_eval', 'adapt', limit=1, out=str(self.out), stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command('star_pregen', stdout=StringIO())


class PregenCommandTests(StarTestCase):

    @LLM_ON
    @mock.patch('star.services.llm._post', side_effect=fake_post)
    def test_pregenerates_drafts_and_replaces_untouched_tasks(self, _post):
        self.make_profile(self.kid2, layer='enlighten')
        old = self.make_level_task(self.kid2, 'L1')
        call_command('star_pregen', users=self.kid2.username, replace=True, stdout=StringIO())
        tasks = AdaptedTask.objects.filter(student=self.kid2)
        self.assertFalse(tasks.filter(id=old.id).exists())
        self.assertEqual(tasks.count(), len(LEVELS))
        # 打桩永远返回 L1 的关卡：L1 本身通过；其余模板知识点 / 卡片不一致或卡槽不匹配时会判为未通过
        self.assertEqual(tasks.get(template='L1').status, 'draft')
        self.assertTrue(all(t.status in ('draft', 'failed') for t in tasks))
        self.assertFalse(tasks.filter(status='approved').exists())
