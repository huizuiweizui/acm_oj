"""卡片闯关规则：模拟器、最短解、关卡模板、三级提示，以及与前端 maze.js 的一致性。"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from star.content.levels import LEVELS, THEMES, themed
from star.services import maze
from star.services.validators import check_level

CASES = json.loads((Path(__file__).parent / 'maze_cases.json').read_text(encoding='utf-8'))

F, L, R = {'type': 'forward'}, {'type': 'left'}, {'type': 'right'}


def rep(n):
    return {'type': 'repeat', 'times': n}


LINE = {'grid': {'w': 5, 'h': 3}, 'start': {'x': 0, 'y': 1, 'dir': 'E'}, 'goal': {'x': 3, 'y': 1},
        'walls': [], 'cards': ['forward', 'left', 'right', 'repeat']}


class SharedCaseTests(SimpleTestCase):
    """与前端 maze.js 共用的用例：两边对同一程序必须给出同样的结果和轨迹。"""

    def test_all_shared_cases(self):
        for c in CASES:
            with self.subTest(c['name']):
                r = maze.simulate(c['level'], c['program'])
                last = r['frames'][-1]
                self.assertEqual(r['result'], c['result'])
                self.assertEqual({'x': last['x'], 'y': last['y'], 'dir': last['dir']}, c['final'])
                self.assertEqual([f['card'] for f in r['frames']], c['cards'])


@unittest.skipUnless(shutil.which('node'), '没有 node，跳过前端规则一致性检查')
class JsParityTests(SimpleTestCase):
    """前端播放动画用 maze.js，后端判定用 maze.py：同一批用例两边结果必须一致。"""

    def test_js_port_matches(self):
        script = Path(settings.BASE_DIR) / 'frontend' / 'scripts' / 'check-maze.mjs'
        proc = subprocess.run(['node', str(script)], capture_output=True, text=True,
                              encoding='utf-8', timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class SimulateTests(SimpleTestCase):

    def test_stops_on_goal_and_ignores_extra_cards(self):
        r = maze.simulate(LINE, [F, F, F, L, F])
        self.assertEqual(r['result'], 'arrived')
        self.assertEqual(len(r['frames']), 4)          # 起点 + 三步
        self.assertEqual(r['cards_used'], 5)

    def test_wall_keeps_position(self):
        level = dict(LINE, walls=[[1, 1]])
        r = maze.simulate(level, [F])
        self.assertEqual(r['result'], 'wall')
        self.assertEqual((r['frames'][-1]['x'], r['frames'][-1]['y']), (0, 1))

    def test_repeat_applies_to_next_card_only(self):
        r = maze.simulate(dict(LINE, goal={'x': 4, 'y': 1}), [rep(2), F, F])
        self.assertEqual((r['frames'][-1]['x'], r['result']), (3, 'not_reached'))
        self.assertEqual([f['rep'] for f in r['frames'][1:]], [1, 2, 0])

    def test_dangling_repeat_is_noop(self):
        self.assertEqual(maze.simulate(LINE, [F, rep(3)])['frames'][-1]['x'], 1)

    def test_action_cap(self):
        prog = [rep(5), L] * 50                          # 原地打转 250 次，超过上限
        r = maze.simulate(LINE, prog)
        self.assertEqual(r['result'], 'not_reached')
        self.assertEqual(len(r['frames']), maze.MAX_ACTIONS + 1)


class ShortestSolutionTests(SimpleTestCase):

    def test_templates_slots_equal_shortest(self):
        for lv in LEVELS:
            with self.subTest(lv['key']):
                sol = maze.shortest_solution(lv)
                self.assertIsNotNone(sol)
                self.assertEqual(len(sol), lv['slots'])
                self.assertEqual(maze.simulate(lv, sol)['result'], 'arrived')
                if lv['knowledge'] == 'loop':
                    self.assertTrue(maze.uses_repeat(sol))

    def test_repeat_shortens_solution(self):
        level = dict(LINE, grid={'w': 6, 'h': 3}, goal={'x': 5, 'y': 1})
        self.assertEqual(len(maze.shortest_solution(level)), 2)
        self.assertEqual(len(maze.shortest_solution(dict(level, cards=['forward']))), 5)

    def test_unsolvable(self):
        level = dict(LINE, walls=[[1, 0], [1, 1], [1, 2]])
        self.assertIsNone(maze.shortest_solution(level))

    def test_deterministic(self):
        lv = LEVELS[2]
        self.assertEqual(maze.shortest_solution(lv), maze.shortest_solution(lv))

    def test_all_themes_valid_for_all_templates(self):
        for lv in LEVELS:
            for key in THEMES:
                with self.subTest(level=lv['key'], theme=key):
                    self.assertTrue(check_level(themed(lv, key)).ok)


class HintTests(SimpleTestCase):

    def test_place_count_does_not_split_repeat_pair(self):
        sol = [rep(4), F, L, rep(4), F]
        self.assertEqual(maze.hint_payload({}, sol, 2)['place_count'], 3)
        sol = [R, rep(3), F, L, rep(5), F]
        # 一半是 3，第 3 张是"前进"，不用调整
        self.assertEqual(maze.hint_payload({}, sol, 2)['place_count'], 3)
        sol = [F, rep(3), F]
        # 一半是 2，第 2 张是重复卡，要把它管的那张一起放上
        self.assertEqual(maze.hint_payload({}, sol, 2)['place_count'], 3)

    def test_actions_by_level(self):
        sol = [F, F]
        self.assertEqual([maze.hint_payload({}, sol, k)['action'] for k in (1, 2, 3)],
                         ['highlight', 'place', 'demo'])
