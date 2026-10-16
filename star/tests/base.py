"""星语测试的公共构造：学生 / 教师 / 团队、画像、任务，以及大模型接口的打桩。"""
import copy
import json
from unittest import mock

from django.test import override_settings

from judge.models import Team, TeamMembership
from judge.tests.base import OJTestCase
from star.content.levels import get_level, themed
from star.content.problems import get_problem, source_of
from star.models import AdaptedTask, LearnerProfile
from star.services import profile as profile_svc

LLM_ON = override_settings(LLM_API_KEY='test-key', LLM_API_URL='http://llm.test/chat/completions',
                           LLM_MODEL='test-model')
LLM_OFF = override_settings(LLM_API_KEY='', LLM_API_URL='', LLM_MODEL='')


def llm_reply(content, tokens=100):
    """伪造一次 OpenAI 兼容接口的返回。content 为 dict 时序列化成 JSON 字符串。"""
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return {'choices': [{'message': {'content': text}}],
            'usage': {'prompt_tokens': tokens, 'completion_tokens': tokens // 2, 'total_tokens': tokens + tokens // 2}}


def patch_llm(*replies):
    """依次返回给定的回复；用尽后再调用会让测试失败（说明多调了大模型）。"""
    return mock.patch('star.services.llm._post', side_effect=list(replies))


class StarTestCase(OJTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.teacher = cls.make_user('t_star', role='teacher')
        cls.other_teacher = cls.make_user('t_other', role='teacher')
        cls.admin = cls.make_user('a_star', role='admin')
        cls.kid = cls.make_user('kid_intro')
        cls.kid2 = cls.make_user('kid_enlighten')
        cls.outsider = cls.make_user('kid_outside')
        team = Team.objects.create(name='星语测试班', creator=cls.teacher, invite_code='STARTEST')
        for u in (cls.kid, cls.kid2):
            TeamMembership.objects.create(team=team, user=u)

    @staticmethod
    def make_profile(user, layer='intro', status='confirmed', **profile):
        base = {'nickname': f'{user.username}昵称', 'layer': layer, 'interests': ['恐龙'], 'theme_key': 'dinosaur',
                'presentation': {'prefer': 'both', 'step_size': 'normal'},
                'communication': {'pronoun_reversal': False, 'echolalia': False, 'notes': ''}}
        base.update(profile)
        return LearnerProfile.objects.create(
            user=user, layer=layer, status=status, profile=base,
            survey=profile_svc.example_answers(interest='dinosaur', reading='sentence', typing='yes',
                                               pace='few', help='hint'),
        )

    def make_problem_row(self, slug='sum_two'):
        spec = get_problem(slug)
        prob = self.make_problem(title=spec['title'], source=source_of(slug))
        for k, (i, o) in enumerate(spec['tests']):
            prob.test_cases.create(input_data=i, expected_output=o, sort_order=k)
        return prob

    def make_steps_task(self, user, slug='sum_two', status='approved', content=None):
        prob = self.make_problem_row(slug)
        return AdaptedTask.objects.create(
            student=user, layer='intro', template=slug, problem=prob, status=status,
            content=copy.deepcopy(content or get_problem(slug)['default_steps']),
        )

    @staticmethod
    def make_level_task(user, key='L5', status='approved'):
        return AdaptedTask.objects.create(
            student=user, layer='enlighten', template=key, status=status,
            content=themed(get_level(key), 'train'),
        )
