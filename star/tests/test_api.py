"""星语接口：学生流程、作答判定、教师审核、权限边界。"""
from unittest import mock

from rest_framework.test import APIClient

from star.models import AdaptedTask, LearnerProfile, StepAttempt
from star.services import learning, profile as profile_svc

from .base import LLM_OFF, StarTestCase

ALL_SURVEY = {q['key']: q['options'][0]['value'] for q in profile_svc.SURVEY}


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
        order = c['steps'][-1]['lines']
        self.assertNotEqual(order, self.task.content['steps'][-1]['lines'])   # 打乱了
        again = api(self.kid).get(f'/api/star/tasks/{self.task.id}/').json()['content']
        self.assertEqual(again['steps'][-1]['lines'], order)                   # 每次一样

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
        shown = api(self.kid).get(f'/api/star/tasks/{self.task.id}/').json()['content']['steps'][-1]['lines']
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
