"""确定性校验器：每条规则都要能拦住对应的错误，且错误信息能直接回填给大模型。"""
import copy

from django.test import SimpleTestCase

from star.content.levels import get_level, themed
from star.content.problems import PROBLEMS, get_problem
from star.services.validators import (avg_sentence_len, char_len, check_level, check_profile,
                                      check_reply, check_steps, reference_lines, sentences)


def steps_of(slug='sum_two'):
    p = get_problem(slug)
    return copy.deepcopy(p['default_steps']), reference_lines(p['code'])


class SentenceTests(SimpleTestCase):

    def test_split_and_count(self):
        self.assertEqual(sentences('先读入。再计算！最后输出？'), ['先读入', '再计算', '最后输出'])
        self.assertEqual(char_len('读 a，读 b。'), 4)          # 不算空白与标点
        self.assertEqual(char_len('填 %。'), 2)                # 百分号算字，句号不算

    def test_inline_code_counts_as_one_word(self):
        self.assertEqual(sentences('用 `for i in range(1, n + 1):` 循环。'), ['用 代码 循环'])

    def test_avg_sentence_len(self):
        self.assertEqual(avg_sentence_len(['一二三。一二三四五。']), 4.0)


class LevelCheckTests(SimpleTestCase):

    def level(self, key='L5'):
        return themed(get_level(key), 'space')

    def test_valid(self):
        self.assertTrue(check_level(self.level()).ok)

    def test_format_error_stops_rule_checks(self):
        c = self.level()
        del c['grid']
        chk = check_level(c)
        self.assertFalse(chk.format_ok)
        self.assertEqual(chk.rule_errors, [])

    def test_unsolvable(self):
        c = self.level('L1')
        c['walls'] = [[1, 0], [1, 1], [1, 2]]
        self.assertIn('关卡无解', ' '.join(check_level(c).errors))

    def test_slots_must_match_shortest(self):
        c = self.level('L1')
        c['slots'] = 2
        self.assertIn('最少需要 3 张卡片', ' '.join(check_level(c).errors))
        c['slots'] = 6
        self.assertIn('卡槽太多', ' '.join(check_level(c).errors))

    def test_loop_level_must_need_repeat(self):
        c = self.level('L4')
        c['slots'] = 4
        c['grid'] = {'w': 4, 'h': 3}
        c['goal'] = {'x': 3, 'y': 1}                    # 只有 3 格直线，不用重复卡也放得下
        self.assertIn('练不到循环', ' '.join(check_level(c).errors))

    def test_knowledge_matches_cards(self):
        c = self.level('L2')
        c['cards'].append('repeat')
        self.assertIn('顺序关卡不提供', ' '.join(check_level(c).errors))
        c = self.level('L4')
        c['cards'] = ['forward']
        self.assertIn('循环关卡必须提供', ' '.join(check_level(c).errors))

    def test_story_sentence_length(self):
        c = self.level()
        c['story'] = ['小火箭今天要飞过一条非常非常长的银河才能回到月亮上面去休息']
        self.assertIn('超过 20 字', ' '.join(check_level(c).errors))

    def test_icons_must_be_emoji(self):
        c = self.level()
        c['theme']['hero'] = '火箭'
        self.assertIn('emoji', ' '.join(check_level(c).errors))

    def test_start_on_wall(self):
        c = self.level('L1')
        c['walls'] = [[0, 1]]
        self.assertIn('起点或终点上不能放障碍', ' '.join(check_level(c).errors))


class StepsCheckTests(SimpleTestCase):

    def test_all_default_steps_valid(self):
        for p in PROBLEMS:
            with self.subTest(p['slug']):
                self.assertIn('default_steps', p)          # 15 道都要能不经大模型直接布置
                chk = check_steps(p['default_steps'], reference_lines(p['code']))
                self.assertTrue(chk.ok, chk.errors)
                self.assertEqual([st['type'] for st in p['default_steps']['steps']][-2:], ['order', 'code'])

    def test_code_step_must_be_last_after_order(self):
        c, ref = steps_of()
        c['steps'].pop()                                   # 去掉写代码
        self.assertIn('写代码步骤', ' '.join(check_steps(c, ref).errors))
        c, ref = steps_of()
        c['steps'][-2], c['steps'][-1] = c['steps'][-1], c['steps'][-2]
        errs = ' '.join(check_steps(c, ref).errors)
        self.assertIn('放在最后一步', errs)
        self.assertIn('倒数第二步', errs)

    def test_starter_only_comments_and_reference_lines(self):
        c, ref = steps_of()
        c['steps'][-1]['starter'] = '# 读入 a 和 b\na = int(input())\n'
        self.assertTrue(check_steps(c, ref).ok)
        c['steps'][-1]['starter'] = 'x = 1\n'
        self.assertIn('"x = 1"不是', ' '.join(check_steps(c, ref).errors))
        c['steps'][-1]['starter'] = '# 先把题目里给出的两个整数分别从标准输入中读进来然后保存\n'
        self.assertIn('超过 20 字', ' '.join(check_steps(c, ref).errors))

    def test_starter_cannot_be_the_whole_answer(self):
        c, ref = steps_of()
        c['steps'][-1]['starter'] = '\n'.join(ref)
        self.assertIn('全部代码行', ' '.join(check_steps(c, ref).errors))

    def test_order_lines_must_come_from_reference(self):
        c, ref = steps_of()
        c['steps'][-2]['lines'][2] = 's = a - b'
        errs = ' '.join(check_steps(c, ref).errors)
        self.assertIn('逐字复制参考解', errs)
        self.assertIn('s = a - b', errs)

    def test_order_must_be_last_and_unique(self):
        c, ref = steps_of()
        c['steps'].insert(0, c['steps'].pop())
        self.assertIn('放在最后一步', ' '.join(check_steps(c, ref).errors))

    def test_choice_answer_unique(self):
        c, ref = steps_of()
        c['steps'][0]['options'] = ['读入两个数', '读入 两个数']
        self.assertIn('重复的选项', ' '.join(check_steps(c, ref).errors))

    def test_choice_answer_in_range(self):
        c, ref = steps_of()
        c['steps'][0]['answer'] = 5
        self.assertIn('超出选项范围', ' '.join(check_steps(c, ref).errors))

    def test_fill_must_rebuild_a_reference_line(self):
        c, ref = steps_of()
        c['steps'][1]['answer'] = '*'
        self.assertIn('完全一致', ' '.join(check_steps(c, ref).errors))
        c['steps'][1]['answer'] = '+'
        c['steps'][1]['code'] = 's = a ___ b'          # 三个下划线也认
        self.assertTrue(check_steps(c, ref).ok)

    def test_hints_exactly_three(self):
        c, ref = steps_of()
        c['steps'][0]['hints'] = c['steps'][0]['hints'][:2]
        chk = check_steps(c, ref)
        self.assertFalse(chk.format_ok)
        self.assertIn('恰好是 3 条', ' '.join(chk.errors))

    def test_step_count(self):
        c, ref = steps_of()
        c['steps'] = c['steps'][-1:]
        self.assertIn('应为 3 到 6 步', ' '.join(check_steps(c, ref).errors))

    def test_long_prompt(self):
        c, ref = steps_of()
        c['steps'][0]['prompt'] = '请你仔细想一想这个程序在一开始的时候最先需要完成的是哪一件事情'
        self.assertIn('超过 20 字', ' '.join(check_steps(c, ref).errors))

    def test_not_a_dict(self):
        self.assertFalse(check_steps(['x'], []).format_ok)


class ProfileAndReplyCheckTests(SimpleTestCase):

    def test_profile(self):
        good = {'layer': 'intro', 'interests': ['恐龙'], 'presentation': {'prefer': 'text'},
                'communication': {'pronoun_reversal': False, 'echolalia': True},
                'vocabulary': [{'word': '大长脖', 'meaning': '腕龙'}]}
        self.assertTrue(check_profile(good).ok)
        bad = dict(good, layer='expert')
        self.assertFalse(check_profile(bad).format_ok)
        bad = dict(good, interests=[])
        self.assertIn('1 到 3 项', ' '.join(check_profile(bad).errors))

    def test_reply(self):
        good = {'intent': 'ask_hint', 'reply': '我们看第一条提示。', 'options': ['看提示', '再试一次']}
        self.assertTrue(check_reply(good).ok)
        self.assertFalse(check_reply(dict(good, intent='diagnose')).format_ok)
        self.assertIn('只能是一句话', ' '.join(check_reply(dict(
            good, reply='这是第一句话。这是第二句话。这是第三句话。')).errors))
        self.assertIn('2 到 4 个', ' '.join(check_reply(dict(good, options=['好'])).errors))
