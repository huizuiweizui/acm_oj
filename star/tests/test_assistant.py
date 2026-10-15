"""对话助手：仿说检测、自创词替换、求助护栏、缓存、身份信息不出平台、兜底回复。"""
from django.core.cache import cache

from star.services import assistant

from .base import LLM_OFF, LLM_ON, StarTestCase, llm_reply, patch_llm

REPLY = {'intent': 'ask_hint', 'reply': '{name}，我们看第一条提示。', 'options': ['看提示', '再试一次']}


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
        with patch_llm(llm_reply(REPLY)) as post:
            out = assistant.reply(self.lp, '阿杰想知道大长脖怎么走')
        sent = post.call_args.args[0]
        text = str(sent['messages'])
        self.assertIn('腕龙', text)                     # 自创词已替换
        self.assertNotIn('大长脖怎么走', text)
        self.assertIn('用"你"指自己', text)             # 代词提示写进了系统提示词
        self.assertNotIn('阿杰', text)                   # 昵称换成了 {name}
        self.assertEqual(sent['temperature'], 0.2)
        self.assertEqual(out['reply'], '阿杰，我们看第一条提示。')
        self.assertEqual(out['meta']['replaced'], [['大长脖', '腕龙']])

    @LLM_ON
    def test_same_question_hits_cache(self):
        with patch_llm(llm_reply(REPLY)) as post:
            first = assistant.reply(self.lp, '怎么办')
            second = assistant.reply(self.lp, '怎么办')
        self.assertEqual(post.call_count, 1)
        self.assertEqual(first['reply'], second['reply'])
        self.assertTrue(second['meta']['cached'])

    @LLM_ON
    def test_echolalia_asks_model_to_rephrase(self):
        with patch_llm(llm_reply(REPLY), llm_reply(dict(REPLY, intent='echo'))) as post:
            assistant.reply(self.lp, '怎么办')
            out = assistant.reply(self.lp, '我们看第一条提示')
        self.assertTrue(out['meta']['echolalia'])
        self.assertIn('可能是仿说', post.call_args.args[0]['messages'][-1]['content'])

    @LLM_ON
    def test_tapping_an_option_is_not_echolalia(self):
        with patch_llm(llm_reply(REPLY), llm_reply(REPLY)):
            assistant.reply(self.lp, '怎么办')
            out = assistant.reply(self.lp, '看提示', via='option')
        self.assertFalse(out['meta']['echolalia'])

    @LLM_ON
    def test_invalid_model_reply_falls_back(self):
        with patch_llm(llm_reply({'intent': 'diagnose', 'reply': '...', 'options': []})):
            out = assistant.reply(self.lp, '怎么办')
        self.assertTrue(out['meta']['fallback'])
        self.assertEqual(out['options'], assistant.FALLBACK_REPLY['options'])

    @LLM_OFF
    def test_without_llm_still_answers_and_logs(self):
        out = assistant.reply(self.lp, '怎么办')
        self.assertTrue(out['meta']['fallback'])
        self.lp.refresh_from_db()
        roles = [m['role'] for m in self.lp.dialogue['assistant']]
        self.assertEqual(roles, ['user', 'bot'])
