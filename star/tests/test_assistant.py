"""对话助手：skills 流水线（仿说、词表、代词、意图）、求助护栏、字面化检查、缓存、身份信息不出平台、兜底回复。"""
from django.core.cache import cache

from star.models import LLMCallLog
from star.services import assistant, expressions

from .base import LLM_OFF, LLM_ON, StarTestCase, llm_reply, patch_llm

REPLY = {'intent': 'ask_hint', 'reply': '{name}，我们看第一条提示。', 'options': ['看提示', '再试一次']}
INTENT = {'intent': 'ask_hint', 'answer': '', 'restated': '学生想要提示', 'confidence': 0.8}


class EcholaliaTests(StarTestCase):

    def test_full_repeat(self):
        self.assertTrue(assistant.is_echolalia('你想看提示吗？', '你想看提示吗'))

    def test_partial_tail_repeat(self):
        self.assertTrue(assistant.is_echolalia('看提示吗', '你想看提示吗？'))

    def test_new_content_is_not_echo(self):
        self.assertFalse(assistant.is_echolalia('我不会写循环', '你想看提示吗？'))
        self.assertFalse(assistant.is_echolalia('好', '你想看提示吗？'))

    def test_vocabulary_longest_first(self):
        text, pairs = assistant.apply_vocabulary(
            '大长脖饿了', [{'word': '长脖', 'meaning': '长颈鹿'}, {'word': '大长脖', 'meaning': '腕龙'}])
        self.assertEqual(text, '腕龙饿了')
        self.assertEqual(pairs, [('大长脖', '腕龙')])


class ReplyTests(StarTestCase):

    def setUp(self):
        cache.clear()
        self.lp = self.make_profile(self.kid, nickname='阿杰',
                                    communication={'pronoun_reversal': True, 'echolalia': False, 'notes': ''})
        self.lp.vocabulary = [{'word': '大长脖', 'meaning': '腕龙'}]
        self.lp.save()

    @LLM_ON
    def test_help_words_bypass_model(self):
        with patch_llm() as post:
            out = assistant.reply(self.lp, '我肚子疼')
        post.assert_not_called()
        self.assertEqual(out['intent'], 'help')
        self.assertTrue(out['meta']['guard'])

    @LLM_ON
    def test_pipeline_and_privacy(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY)) as post:
            out = assistant.reply(self.lp, '阿杰想知道大长脖怎么走')
        intent_call, reply_call = (c.args[0] for c in post.call_args_list)
        self.assertIn('意图识别', intent_call['messages'][0]['content'])   # 第 5 步：意图识别
        text = str(reply_call['messages'])
        self.assertIn('腕龙', text)                     # 自创词已替换
        self.assertNotIn('大长脖怎么走', text)
        self.assertIn('用"你"指自己', text)             # 代词提示写进了系统提示词
        self.assertIn('意图识别结果：ask_hint', text)   # 意图交给了回复生成
        for call in (intent_call, reply_call):
            self.assertNotIn('阿杰', str(call['messages']))   # 昵称换成了 {name}
        self.assertEqual(reply_call['temperature'], 0.2)
        self.assertEqual(out['reply'], '阿杰，我们看第一条提示。')
        self.assertEqual(out['meta']['replaced'], [['大长脖', '腕龙']])
        self.assertEqual(out['meta']['intent']['intent'], 'ask_hint')
        purposes = list(LLMCallLog.objects.order_by('id').values_list('purpose', flat=True))
        self.assertEqual(purposes, ['P5', 'P3'])

    @LLM_ON
    def test_pronoun_hint_reaches_both_calls(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY)) as post:
            out = assistant.reply(self.lp, '你要提示')
        self.assertEqual(len(out['meta']['pronoun_hints']), 1)
        self.assertIn('可能指他自己', out['meta']['pronoun_hints'][0])
        for call in post.call_args_list:
            last = call.args[0]['messages'][-1]['content']
            self.assertIn('可能指他自己（{name}）', last)
            self.assertNotIn('阿杰', str(call.args[0]['messages']))

    @LLM_ON
    def test_no_pronoun_hint_without_flag(self):
        self.lp.profile['communication']['pronoun_reversal'] = False
        self.lp.save()
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY)) as post:
            out = assistant.reply(self.lp, '你要提示')
        self.assertEqual(out['meta']['pronoun_hints'], [])
        last = post.call_args_list[0].args[0]['messages'][-1]['content']    # 少样本示例之后的真实输入
        self.assertIn('代词提示：无', last)

    @LLM_ON
    def test_same_question_hits_cache(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY)) as post:
            first = assistant.reply(self.lp, '怎么办')
            second = assistant.reply(self.lp, '怎么办')
        self.assertEqual(post.call_count, 2)            # 第二次连意图识别都不用再调
        self.assertEqual(first['reply'], second['reply'])
        self.assertTrue(second['meta']['cached'])
        self.assertEqual(second['meta']['intent']['intent'], 'ask_hint')

    @LLM_ON
    def test_need_help_intent_goes_to_teacher(self):
        with patch_llm(llm_reply(dict(INTENT, intent='need_help'))) as post:
            out = assistant.reply(self.lp, '我不想学了')
        self.assertEqual(post.call_count, 1)
        self.assertEqual(out['reply'], assistant.HELP_REPLY['reply'])
        self.assertTrue(out['meta']['guard'])

    @LLM_ON
    def test_echolalia_asks_model_to_rephrase(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY), llm_reply(dict(REPLY, intent='echo'))) as post:
            assistant.reply(self.lp, '怎么办')
            out = assistant.reply(self.lp, '我们看第一条提示')
        self.assertTrue(out['meta']['echolalia'])
        self.assertEqual(post.call_count, 3)            # 仿说不做意图识别，直接请模型换问法
        self.assertIn('可能是仿说', post.call_args.args[0]['messages'][-1]['content'])

    @LLM_ON
    def test_tapping_an_option_is_not_echolalia(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY), llm_reply(REPLY)) as post:
            assistant.reply(self.lp, '怎么办')
            out = assistant.reply(self.lp, '看提示', via='option')
        self.assertFalse(out['meta']['echolalia'])
        self.assertEqual(out['meta']['intent']['source'], 'option')   # 点选项由规则判定，不调意图识别
        self.assertEqual(post.call_count, 3)

    @LLM_ON
    def test_reply_failing_plain_check_is_rewritten(self):
        long_reply = dict(REPLY, reply='难道你不知道小火车应该先向前走再转弯吗')
        with patch_llm(llm_reply(INTENT), llm_reply(long_reply), llm_reply(REPLY)) as post:
            out = assistant.reply(self.lp, '怎么办')
        self.assertEqual(post.call_count, 3)
        self.assertIn('反问', post.call_args.args[0]['messages'][-1]['content'])
        self.assertFalse(out['meta']['fallback'])
        self.assertEqual(out['reply'], '阿杰，我们看第一条提示。')

    @LLM_ON
    def test_invalid_model_reply_falls_back(self):
        bad = llm_reply({'intent': 'diagnose', 'reply': '...', 'options': []})
        with patch_llm(llm_reply(INTENT), bad, bad):
            out = assistant.reply(self.lp, '怎么办')
        self.assertTrue(out['meta']['fallback'])
        self.assertEqual(out['options'], assistant.FALLBACK_REPLY['options'])

    @LLM_OFF
    def test_without_llm_still_answers_and_logs(self):
        out = assistant.reply(self.lp, '我不会')
        self.assertTrue(out['meta']['fallback'])
        self.assertEqual(out['meta']['intent'], {'intent': 'dont_know', 'restated': '学生不会',
                                                 'confidence': 0.5, 'source': 'rule'})
        self.lp.refresh_from_db()
        roles = [m['role'] for m in self.lp.dialogue['assistant']]
        self.assertEqual(roles, ['user', 'bot'])


class ExpressionMemoryTests(StarTestCase):
    """个人表达记忆：大模型两次一致后生效，生效后同一说法不再调意图识别；教师改意图后旧缓存作废。"""

    def setUp(self):
        cache.clear()
        self.lp = self.make_profile(self.kid, nickname='阿杰')
        self.lp.vocabulary = [{'word': '嘀嘀', 'meaning': '提示'}]
        self.lp.save()

    @LLM_ON
    def test_learn_twice_then_hit(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY), llm_reply(INTENT), llm_reply(REPLY)):
            first = assistant.reply(self.lp, '我要嘀嘀', step=0)
            second = assistant.reply(self.lp, '我要嘀嘀啦', step=1)     # 换了一步，不走回复缓存
        self.assertEqual(first['meta']['memory']['event'], 'new')
        self.assertEqual(second['meta']['memory']['event'], 'active')
        with patch_llm(llm_reply(REPLY)) as post:                        # 只剩生成回复这一次调用
            third = assistant.reply(self.lp, '我要嘀嘀！', step=2)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(third['meta']['intent']['source'], 'memory')
        self.assertEqual(third['meta']['memory']['event'], 'hit')
        self.lp.refresh_from_db()
        self.assertEqual(len(self.lp.expressions), 1)
        e = self.lp.expressions[0]
        self.assertEqual((e['text'], e['intent'], e['votes'], e['hits']), ('我要提示', 'ask_hint', 2, 1))

    @LLM_ON
    def test_low_confidence_and_answer_not_learned(self):
        with patch_llm(llm_reply(dict(INTENT, confidence=0.6)), llm_reply(REPLY),
                       llm_reply(dict(INTENT, intent='answer', answer='3')), llm_reply(REPLY)):
            assistant.reply(self.lp, '帮帮我')
            assistant.reply(self.lp, '是三')
        self.lp.refresh_from_db()
        self.assertEqual(self.lp.expressions, [])

    @LLM_ON
    def test_teacher_change_beats_reply_cache(self):
        with patch_llm(llm_reply(INTENT), llm_reply(REPLY)):
            assistant.reply(self.lp, '怎么办', step=0)
        self.lp.refresh_from_db()
        expressions.teacher_update(self.lp, [{'text': '怎么办', 'intent': 'dont_know', 'status': 'confirmed'}])
        self.lp.save()
        with patch_llm(llm_reply(REPLY)) as post:
            out = assistant.reply(self.lp, '怎么办', step=0)
        self.assertEqual(post.call_count, 1)
        self.assertFalse(out['meta']['cached'])
        self.assertEqual(out['meta']['intent']['intent'], 'dont_know')
        self.assertIn('意图识别结果：dont_know', str(post.call_args.args[0]['messages']))
