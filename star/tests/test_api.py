"""星语接口：学生流程、作答判定、教师审核、权限边界。"""
from unittest import mock

from rest_framework.test import APIClient

from star.models import AdaptedTask, LearnerProfile, StepAttempt
from star.services import learning, profile as profile_svc

from .base import LLM_OFF, StarTestCase

ALL_SURVEY = profile_svc.example_answers()


def api(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user)
    return c


@LLM_OFF
class OnboardingTests(StarTestCase):

    def test_survey_then_dialogue_builds_profile(self):
        c = api(self.kid)
        self.assertEqual(c.get('/api/star/me/').json()['status'], 'new')
        r = c.post('/api/star/survey/', {'answers': ALL_SURVEY}, format='json')
        self.assertEqual(r.status_code, 200)
        q = r.json()['dialogue']
        self.assertEqual((q['index'], q['total']), (0, 5))

        answers = ['高铁', '呜呜', '停停', '再说一遍', '小航']
        for i, a in enumerate(answers):
            r = c.post('/api/star/dialogue/', {'answer': a, 'via': 'text'}, format='json')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['done'], i == len(answers) - 1)

        lp = LearnerProfile.objects.get(user=self.kid)
        self.assertEqual(lp.status, 'pending')
        self.assertEqual(lp.profile['source'], 'rule')
        self.assertEqual(lp.profile['nickname'], '小航')
        words = {v['word']: v['meaning'] for v in lp.vocabulary}
        self.assertEqual(words, {'呜呜': '高铁', '停停': '想休息'})
        # 问卷第一项都选了 train / image / word ... → 认字少、不会打字之外的组合由规则决定层级
        self.assertEqual(lp.layer, profile_svc.suggest_layer(ALL_SURVEY))

    def test_survey_returns_custom_ui(self):
        answers = profile_svc.example_answers(
            bg_color='dark',
            color_like={r['key']: 3 for r in profile_svc._SURVEY_BY_KEY['color_like']['rows']} | {'purple': 5},
            ui_needs={r['key']: 'no' for r in profile_svc._SURVEY_BY_KEY['ui_needs']['rows']} | {'font_size': 'must'},
        )
        r = api(self.kid).post('/api/star/survey/', {'answers': answers}, format='json')
        self.assertEqual(r.status_code, 200)
        ui = r.json()['ui']
        self.assertEqual((ui['bg'], ui['accent'], ui['font_adjust'], ui['color_choice']),
                         ('dark', 'purple', True, False))
        self.assertEqual(api(self.kid).get('/api/star/me/').json()['ui'], ui)

    def test_incomplete_survey_rejected(self):
        partial = dict(ALL_SURVEY)
        partial.pop('typing')
        r = api(self.kid).post('/api/star/survey/', {'answers': partial}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_survey_cannot_be_redone_after_submit(self):
        self.make_profile(self.kid, status='pending')
        r = api(self.kid).post('/api/star/survey/', {'answers': ALL_SURVEY}, format='json')
        self.assertEqual(r.status_code, 409)


@LLM_OFF
class StudentTaskTests(StarTestCase):

    def setUp(self):
        self.make_profile(self.kid)
        self.task = self.make_steps_task(self.kid)

    def test_only_approved_own_tasks_visible(self):
        draft = self.make_steps_task(self.kid, slug='odd_even', status='draft')
        mine = api(self.kid).get('/api/star/tasks/').json()
        self.assertEqual([t['id'] for t in mine], [self.task.id])
        self.assertEqual(api(self.kid).get(f'/api/star/tasks/{draft.id}/').status_code, 404)
        self.assertEqual(api(self.kid2).get(f'/api/star/tasks/{self.task.id}/').status_code, 404)

    def test_student_content_hides_answers(self):
        c = api(self.kid).get(f'/api/star/tasks/{self.task.id}/').json()['content']
        text = str(c)
        self.assertNotIn("'answer'", text)
        self.assertNotIn('hints', text)
        order = c['steps'][-2]['lines']
        self.assertNotEqual(order, self.task.content['steps'][-2]['lines'])   # 打乱了
        again = api(self.kid).get(f'/api/star/tasks/{self.task.id}/').json()['content']
        self.assertEqual(again['steps'][-2]['lines'], order)                   # 每次一样

    def test_choice_and_fill_judging_and_progress(self):
        c = api(self.kid)
        r = c.post(f'/api/star/tasks/{self.task.id}/attempt/',
                   {'step': 0, 'answer': {'choice': 1}, 'hint_level': 0}, format='json').json()
        self.assertFalse(r['correct'])
        self.assertEqual(r['feedback'], learning.FEEDBACK['wrong'])
        r = c.post(f'/api/star/tasks/{self.task.id}/attempt/',
                   {'step': 0, 'answer': {'choice': 0}, 'hint_level': 2, 'duration_ms': 4200}, format='json').json()
        self.assertTrue(r['correct'])
        r = c.post(f'/api/star/tasks/{self.task.id}/attempt/',
                   {'step': 1, 'answer': {'text': ' + '}}, format='json').json()
        self.assertTrue(r['correct'])
        self.assertEqual(r['done_steps'], [0, 1])
        self.assertFalse(r['task_done'])
        last = StepAttempt.objects.filter(task=self.task, step_index=0, is_correct=True).get()
        self.assertEqual((last.hint_level, last.duration_ms), (2, 4200))

    def test_order_step_is_judged_by_running_the_program(self):
        shown = api(self.kid).get(f'/api/star/tasks/{self.task.id}/').json()['content']['steps'][-2]['lines']
        order = [shown.index(x) for x in ['b = int(input())', 'a = int(input())', 's = a + b', 'print(s)']]
        fake = {'status': 'AC', 'passed': 5, 'total': 5, 'error': ''}
        with mock.patch('star.services.learning.run_against_tests', return_value=fake) as run:
            r = api(self.kid).post(f'/api/star/tasks/{self.task.id}/attempt/',
                                   {'step': 2, 'answer': {'order': order}}, format='json').json()
        self.assertTrue(r['correct'])
        program = run.call_args.args[1]
        self.assertEqual(program.splitlines(), ['b = int(input())', 'a = int(input())', 's = a + b', 'print(s)'])

    def test_incomplete_order_not_run(self):
        with mock.patch('star.services.learning.run_against_tests') as run:
            r = api(self.kid).post(f'/api/star/tasks/{self.task.id}/attempt/',
                                   {'step': 2, 'answer': {'order': [0, 1]}}, format='json').json()
        run.assert_not_called()
        self.assertEqual(r['feedback'], learning.FEEDBACK['incomplete'])

    def test_hint_levels(self):
        r = api(self.kid).post(f'/api/star/tasks/{self.task.id}/hint/', {'step': 1, 'level': 3}, format='json')
        self.assertEqual(r.json()['text'], self.task.content['steps'][1]['hints'][2])
        r = api(self.kid).post(f'/api/star/tasks/{self.task.id}/hint/', {'step': 9, 'level': 1}, format='json')
        self.assertEqual(r.status_code, 400)


@LLM_OFF
class CodeStepTests(StarTestCase):
    """最后一步：学生自己写整段程序，跑测试数据判定。"""

    CODE = 3       # sum_two 的写代码步骤

    def setUp(self):
        self.make_profile(self.kid)
        self.task = self.make_steps_task(self.kid)

    def post(self, code):
        return api(self.kid).post(f'/api/star/tasks/{self.task.id}/attempt/',
                                  {'step': self.CODE, 'answer': {'code': code}}, format='json').json()

    def test_starter_shown_and_no_reference(self):
        st = api(self.kid).get(f'/api/star/tasks/{self.task.id}/').json()['content']['steps'][self.CODE]
        self.assertEqual(st['type'], 'code')
        self.assertTrue(st['starter'].startswith('# '))
        self.assertNotIn('s = a + b', st['starter'])

    def test_empty_or_comment_only_not_run(self):
        with mock.patch('star.services.learning.run_against_tests') as run:
            r = self.post('# 读入 a 和 b\n\n')
        run.assert_not_called()
        self.assertEqual(r['feedback'], learning.FEEDBACK['empty_code'])

    def test_syntax_error_reported_with_line_without_running(self):
        with mock.patch('star.services.learning.run_against_tests') as run:
            r = self.post('a = int(input())\nb = int(input()\nprint(a + b)\n')
        run.assert_not_called()
        self.assertFalse(r['correct'])
        self.assertEqual(r['feedback'], learning.FEEDBACK['code_error'])
        self.assertTrue(r['error_text'].startswith('第 '))

    def test_runtime_error_explained(self):
        fake = {'status': 'RE', 'passed': 0, 'total': 5,
                'error': 'Traceback (most recent call last):\n  File "/sandbox/main.py", line 3, in <module>\n'
                         "    print(c)\nNameError: name 'c' is not defined\n", 'first_fail': None}
        with mock.patch('star.services.learning.run_against_tests', return_value=fake):
            r = self.post('a = int(input())\nb = int(input())\nprint(c)\n')
        self.assertEqual(r['error_line'], 3)
        self.assertEqual(r['error_text'], '第 3 行：' + learning.ERROR_TEXT['NameError'])
        self.assertEqual(r['error_raw'], "NameError: name 'c' is not defined")
        self.assertNotIn('sandbox', str(r))

    def test_wrong_answer_shows_first_failing_case(self):
        fake = {'status': 'WA', 'passed': 0, 'total': 5, 'error': '',
                'first_fail': {'input': '3\n5\n', 'expected': '8', 'output': '-2\n'}}
        with mock.patch('star.services.learning.run_against_tests', return_value=fake) as run:
            r = self.post('a = int(input())\nb = int(input())\nprint(a - b)\n')
        self.assertTrue(run.call_args.kwargs['detail'])
        self.assertEqual(r['feedback'], learning.FEEDBACK['code_wrong'])
        self.assertEqual(r['first_fail']['expected'], '8')

    def test_correct_code_finishes_task(self):
        for i in range(self.CODE):
            StepAttempt.objects.create(task=self.task, step_index=i, is_correct=True)
        fake = {'status': 'AC', 'passed': 5, 'total': 5, 'error': '', 'first_fail': None}
        code = 'a = int(input())\r\nb = int(input())\r\nprint(a + b)\r\n'
        with mock.patch('star.services.learning.run_against_tests', return_value=fake) as run:
            r = self.post(code)
        self.assertTrue(r['correct'])
        self.assertTrue(r['task_done'])
        self.assertNotIn('\r', run.call_args.args[1])
        stored = StepAttempt.objects.filter(task=self.task, step_index=self.CODE).get()
        self.assertEqual(stored.answer['status'], 'AC')

    def test_code_must_be_text(self):
        r = api(self.kid).post(f'/api/star/tasks/{self.task.id}/attempt/',
                               {'step': self.CODE, 'answer': {'code': ['x']}}, format='json')
        self.assertEqual(r.status_code, 400)


@LLM_OFF
@mock.patch('star.services.adapt.reference_passes', return_value=True)
class AssignTests(StarTestCase):
    """教师批量布置：一组素材 × 一组学生，用默认版本。"""

    def setUp(self):
        self.make_profile(self.kid, layer='intro')
        self.make_profile(self.kid2, layer='enlighten')
        self.make_problem_row('sum_two')
        self.make_problem_row('double')

    def assign(self, user=None, **data):
        body = dict({'learners': [self.kid.id, self.kid2.id], 'materials': ['L1', 'sum_two', 'double']}, **data)
        return api(user or self.teacher).post('/api/star/teacher/assign/', body, format='json')

    def test_teams_listing_is_scoped(self, _ref):
        teams = api(self.teacher).get('/api/star/teacher/assign/').json()['teams']
        self.assertEqual([t['name'] for t in teams], ['星语测试班'])
        self.assertEqual({x['user_id'] for x in teams[0]['learners']}, {self.kid.id, self.kid2.id})
        self.assertEqual(api(self.other_teacher).get('/api/star/teacher/assign/').json()['teams'], [])
        self.assertEqual(api(self.kid).get('/api/star/teacher/assign/').status_code, 403)

    def test_assign_by_layer_and_approve(self, _ref):
        r = self.assign()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['created_total'], 3)
        by_user = {x['user_id']: x for x in r.json()['results']}
        self.assertEqual([c['template'] for c in by_user[self.kid.id]['created']], ['sum_two', 'double'])
        self.assertEqual([c['template'] for c in by_user[self.kid2.id]['created']], ['L1'])
        self.assertEqual({s['reason'] for s in by_user[self.kid.id]['skipped']}, {'层级不对'})

        mine = api(self.kid).get('/api/star/tasks/').json()               # 学生立刻能看到，按布置顺序
        self.assertEqual([t['template'] for t in mine], ['sum_two', 'double'])
        lv = AdaptedTask.objects.get(student=self.kid2)
        self.assertEqual(lv.content['theme']['name'], '恐龙')               # 关卡套学生的兴趣主题
        self.assertEqual(lv.approved_by, self.teacher)

    def test_no_duplicates(self, _ref):
        self.assign()
        r = self.assign()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['created_total'], 0)
        self.assertEqual(AdaptedTask.objects.count(), 3)

    def test_draft_mode(self, _ref):
        self.assign(approve=False, learners=[self.kid.id], materials=['sum_two'])
        self.assertEqual(AdaptedTask.objects.get().status, 'draft')
        self.assertEqual(api(self.kid).get('/api/star/tasks/').json(), [])

    def test_missing_problem_row_skipped(self, _ref):
        r = self.assign(learners=[self.kid.id], materials=['stars']).json()
        self.assertIn('seed_star', r['results'][0]['skipped'][0]['reason'])

    def test_other_teacher_and_bad_input(self, _ref):
        self.assertEqual(self.assign(self.other_teacher).status_code, 403)
        self.assertEqual(self.assign(materials=['nope']).status_code, 400)
        self.assertEqual(self.assign(learners=[]).status_code, 400)
        self.assertFalse(AdaptedTask.objects.exists())


@LLM_OFF
class LevelTaskTests(StarTestCase):

    def setUp(self):
        self.make_profile(self.kid2, layer='enlighten')
        self.task = self.make_level_task(self.kid2, 'L5')

    def post(self, program, **extra):
        return api(self.kid2).post(f'/api/star/tasks/{self.task.id}/attempt/',
                                   dict({'step': 0, 'answer': {'program': program}}, **extra), format='json').json()

    def test_solution_from_hint_arrives(self):
        sol = api(self.kid2).post(f'/api/star/tasks/{self.task.id}/hint/',
                                  {'step': 0, 'level': 3}, format='json').json()['solution']
        r = self.post(sol, hint_level=3)
        self.assertTrue(r['correct'])
        self.assertEqual((r['result'], r['cards_used'], r['shortest']), ('arrived', 5, 5))

    def test_results(self):
        self.assertEqual(self.post([{'type': 'left'}, {'type': 'forward'}])['result'], 'not_reached')
        self.assertEqual(self.post([{'type': 'right'}, {'type': 'forward'}])['result'], 'out')
        self.assertEqual(self.post([{'type': 'forward'}] * 6)['result'], 'too_many')

    def test_card_not_in_level_rejected(self):
        task = self.make_level_task(self.kid2, 'L1')     # 只有"前进"
        r = api(self.kid2).post(f'/api/star/tasks/{task.id}/attempt/',
                                {'step': 0, 'answer': {'program': [{'type': 'left'}]}}, format='json')
        self.assertEqual(r.status_code, 400)


@LLM_OFF
class TeacherTests(StarTestCase):

    def setUp(self):
        self.lp = self.make_profile(self.kid, status='pending')
        self.make_problem_row('sum_two')

    def test_scoping(self):
        self.make_profile(self.outsider)
        ids = [r['user_id'] for r in api(self.teacher).get('/api/star/teacher/learners/').json()['learners']]
        self.assertEqual(ids, [self.kid.id])
        self.assertEqual(api(self.other_teacher).get(f'/api/star/teacher/learners/{self.kid.id}/').status_code, 404)
        self.assertEqual(api(self.admin).get(f'/api/star/teacher/learners/{self.outsider.id}/').status_code, 200)
        self.assertEqual(api(self.kid).get('/api/star/teacher/learners/').status_code, 403)
        self.assertEqual(api().get('/api/star/teacher/learners/').status_code, 401)

    def test_confirm_profile_and_edit_vocabulary(self):
        r = api(self.teacher).patch(f'/api/star/teacher/learners/{self.kid.id}/', {
            'layer': 'intro', 'vocabulary': [{'word': '大长脖', 'meaning': '腕龙'}, {'word': '', 'meaning': 'x'}],
            'communication': {'pronoun_reversal': True}, 'confirm': True,
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.lp.refresh_from_db()
        self.assertEqual(self.lp.status, 'confirmed')
        self.assertEqual(self.lp.confirmed_by, self.teacher)
        self.assertEqual(self.lp.vocabulary, [{'word': '大长脖', 'meaning': '腕龙'}])
        self.assertTrue(self.lp.profile['communication']['pronoun_reversal'])

    def test_llm_mode_without_key_is_503(self):
        r = api(self.teacher).post(f'/api/star/teacher/learners/{self.kid.id}/tasks/', {'material': 'sum_two'},
                                   format='json')
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()['code'], 'llm_not_configured')
        self.assertFalse(AdaptedTask.objects.exists())

    def test_layer_must_match_material(self):
        r = api(self.teacher).post(f'/api/star/teacher/learners/{self.kid.id}/tasks/',
                                   {'material': 'L1', 'mode': 'template'}, format='json')
        self.assertEqual(r.status_code, 400)

    @mock.patch('star.services.adapt.reference_passes', return_value=True)
    def test_review_lifecycle(self, _ref):
        t = api(self.teacher)
        r = t.post(f'/api/star/teacher/learners/{self.kid.id}/tasks/',
                   {'material': 'sum_two', 'mode': 'template'}, format='json')
        self.assertEqual(r.status_code, 201)
        task_id = r.json()['id']
        self.assertEqual(r.json()['status'], 'draft')
        self.assertEqual(api(self.kid).get(f'/api/star/tasks/{task_id}/').status_code, 404)   # 审核前学生看不到

        content = r.json()['content']
        content['steps'][0]['prompt'] = '请你仔细想一想这个程序在一开始的时候最先需要完成的是哪一件事情'
        r = t.patch(f'/api/star/teacher/tasks/{task_id}/', {'content': content}, format='json')
        self.assertEqual(r.json()['status'], 'failed')
        self.assertEqual(t.post(f'/api/star/teacher/tasks/{task_id}/approve/').status_code, 400)

        content['steps'][0]['prompt'] = '程序先做什么？'
        r = t.patch(f'/api/star/teacher/tasks/{task_id}/', {'content': content}, format='json')
        self.assertEqual(r.json()['status'], 'draft')
        self.assertEqual([e['mode'] for e in r.json()['validation_log']], ['template', 'edit', 'edit'])

        r = t.post(f'/api/star/teacher/tasks/{task_id}/approve/')
        self.assertEqual(r.json()['status'], 'approved')
        self.assertEqual(api(self.kid).get(f'/api/star/tasks/{task_id}/').status_code, 200)
        # 通过后锁定：不能改文字
        self.assertEqual(t.patch(f'/api/star/teacher/tasks/{task_id}/', {'content': content},
                                 format='json').status_code, 409)
        # 有作答记录后不能重新生成
        StepAttempt.objects.create(task_id=task_id, step_index=0, is_correct=True)
        self.assertEqual(t.post(f'/api/star/teacher/tasks/{task_id}/regenerate/',
                                {'mode': 'template'}, format='json').status_code, 409)

    def test_report_without_llm(self):
        task = self.make_steps_task(self.kid, slug='odd_even')
        StepAttempt.objects.create(task=task, step_index=0, is_correct=True, hint_level=2)
        StepAttempt.objects.create(task=task, step_index=1, is_correct=True, hint_level=0)
        r = api(self.teacher).post(f'/api/star/teacher/learners/{self.kid.id}/report/',
                                   {'audience': 'teacher'}, format='json').json()
        self.assertEqual(r['source'], 'rule')
        self.assertIn(self.lp.nickname, r['text'])
        self.assertIn('提示等级从 2 降到 0', r['text'])
