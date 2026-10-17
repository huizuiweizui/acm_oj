"""
星语演示数据（幂等，可重复运行）：

    1. 15 道入门题写入题库（不公开，source = "星语·<slug>"），测试数据整体替换；
       默认用评测机实跑一遍参考解，确认能通过全部测试数据（--no-verify 跳过）；
    2. 演示账号：教师 1 个（star_teacher）、学生 40 个（content/learners.py，启蒙层、入门层各 20 个），
       建一个由该教师创建的团队，40 名学生都是成员——教师端据此看到他们；
    3. 每名学生的画像（已确认）与个人词表；
    4. 每名学生一组已审核的任务：启蒙层 6 个关卡（按兴趣套主题包），入门层 5 道演示题的默认分步任务。
       已有任务的学生不动，--reset-tasks 时删掉重建（连同作答记录）。

    python manage.py seed_star [--password XXX] [--no-verify] [--reset-tasks]

演示账号的默认密码见 DEMO_PASSWORD；部署到公网前务必用 --password 换掉。
"""
import secrets

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from judge.models import Problem, Team, TeamMembership, TestCase, UserProfile
from star.content.learners import LEARNERS, TEACHER_USERNAME, TEAM_NAME
from star.content.levels import LEVELS, themed
from star.content.problems import PROBLEMS, source_of
from star.models import AdaptedTask, LearnerProfile
from star.services import profile as profile_svc
from star.services.adapt import check_content
from star.services.runner import run_against_tests

DEMO_PASSWORD = 'StarDemo2026'


class Command(BaseCommand):
    help = '写入星语演示数据：入门题、演示账号、画像与已审核任务'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEMO_PASSWORD, help='演示账号的密码')
        parser.add_argument('--no-verify', action='store_true', help='不用评测机校验参考解')
        parser.add_argument('--reset-tasks', action='store_true', help='删除演示学生的任务与作答记录后重建')

    def handle(self, *args, **opts):
        teacher = self._user(TEACHER_USERNAME, 'teacher', opts['password'], real_name='星语老师')
        problems = self._problems(teacher)
        if not opts['no_verify']:
            self._verify(problems)
        team = self._team(teacher)
        for spec in LEARNERS:
            user = self._user(spec['username'], 'student', opts['password'], real_name='')
            TeamMembership.objects.get_or_create(team=team, user=user)
            lp = self._profile(user, spec, teacher, opts['reset_tasks'])
            self._tasks(lp, spec, teacher, problems, opts['reset_tasks'])

        if opts['password'] == DEMO_PASSWORD:
            self.stdout.write(self.style.WARNING('演示账号使用的是默认密码（DEMO_PASSWORD），部署到公网前请用 --password 更换'))
        self.stdout.write(self.style.SUCCESS(
            f'完成：教师 {TEACHER_USERNAME}，学生 {len(LEARNERS)} 名，团队「{TEAM_NAME}」'))

    # ── 账号与团队 ───────────────────────────────────────────────────
    def _user(self, username, role, password, real_name=''):
        user, created = User.objects.get_or_create(username=username)
        if created or not user.has_usable_password() or password != DEMO_PASSWORD:
            user.set_password(password)
            user.save()
        prof, _ = UserProfile.objects.get_or_create(user=user)
        prof.role = role
        if real_name:
            prof.real_name = real_name
        prof.must_change_password = False
        prof.save()
        return user

    def _team(self, teacher):
        team = Team.objects.filter(name=TEAM_NAME, creator=teacher).first()
        if team is None:
            code = secrets.token_hex(4).upper()
            while Team.objects.filter(invite_code=code).exists():
                code = secrets.token_hex(4).upper()
            team = Team.objects.create(name=TEAM_NAME, creator=teacher, invite_code=code,
                                       description='星语演示用的虚构学生', need_review=True)
        return team

    # ── 题目 ─────────────────────────────────────────────────────────
    @transaction.atomic
    def _problems(self, teacher):
        rows = {}
        for spec in PROBLEMS:
            sample_in, sample_out = spec['tests'][0]
            defaults = dict(
                title=spec['title'], description=spec['description'],
                input_desc=spec['input_desc'], output_desc=spec['output_desc'],
                sample_input=sample_in.strip(), sample_output=sample_out,
                difficulty='入门', time_limit=1000, memory_limit=128,
                is_published=False, created_by=teacher,
            )
            prob, _ = Problem.objects.update_or_create(source=source_of(spec['slug']), defaults=defaults)
            prob.test_cases.all().delete()
            TestCase.objects.bulk_create([
                TestCase(problem=prob, input_data=i, expected_output=o, is_sample=(k == 0), sort_order=k)
                for k, (i, o) in enumerate(spec['tests'])
            ])
            rows[spec['slug']] = prob
        self.stdout.write(f'入门题 {len(rows)} 道已写入题库（不公开）')
        return rows

    def _verify(self, problems):
        bad = []
        for spec in PROBLEMS:
            res = run_against_tests(problems[spec['slug']], spec['code'], 'Python')
            if res['status'] != 'AC':
                bad.append(f'{spec["slug"]}: {res["status"]} {res["passed"]}/{res["total"]} {res["error"][:80]}')
        if bad:
            raise CommandError('参考解未通过测试数据：\n' + '\n'.join(bad))
        self.stdout.write(f'参考解校验通过（评测机实跑 {len(problems)} 道）')

    # ── 画像与任务 ───────────────────────────────────────────────────
    def _profile(self, user, spec, teacher, reset):
        lp, _ = LearnerProfile.objects.get_or_create(user=user)
        lp.layer = spec['layer']
        # 种子只写了与画像有关的题，其余题按默认答案补齐，保证问卷完整、可在教师端展示
        lp.survey = profile_svc.example_answers(**_full_scales(spec['survey']))
        lp.profile = dict(spec['profile'], nickname=spec['nickname'], layer=spec['layer'],
                          help_preference=spec['survey']['help'], ui=profile_svc.build_ui(lp.survey),
                          source='seed')
        lp.vocabulary = spec['vocabulary']
        # 重置时连对话助手的记录一起清空，演示从干净状态开始
        lp.dialogue = dict({} if reset else (lp.dialogue or {}), intro=[
            {'key': k, 'question': q, 'answer': a, 'via': 'text'} for k, q, a in spec['intro']
        ])
        lp.status, lp.confirmed_by, lp.confirmed_at = 'confirmed', teacher, timezone.now()
        lp.save()
        return lp

    def _tasks(self, lp, spec, teacher, problems, reset):
        existing = AdaptedTask.objects.filter(student=lp.user)
        if existing.exists() and not reset:
            return
        existing.delete()

        if spec['layer'] == 'enlighten':
            items = [(lv['key'], None, themed(lv, spec['profile']['theme_key'])) for lv in LEVELS]
        else:
            items = [(p['slug'], problems[p['slug']], p['default_steps'])
                     for p in PROBLEMS if p.get('demo')]
        now = timezone.now()
        for order, (key, prob, content) in enumerate(items, 1):
            task = AdaptedTask(student=lp.user, layer=spec['layer'], template=key, problem=prob,
                               content=content, status='approved', sort_order=order,
                               created_by=teacher, approved_by=teacher, approved_at=now)
            chk = check_content(task, content)
            if not chk.ok:
                raise CommandError(f'{spec["username"]} 的任务 {key} 未通过校验：{chk.errors}')
            task.validation_log = [{'run': 1, 'mode': 'template', 'attempt': 1, 'ok': True,
                                    'errors': [], 'at': now.isoformat()}]
            task.save()
        self.stdout.write(f'{spec["username"]}：{len(items)} 个已审核任务')


def _full_scales(survey):
    """打分表题只写了几行时，其余行补"一般"（3 分 / 都可以），以通过问卷完整性要求。"""
    out = dict(survey)
    for q in profile_svc.SURVEY:
        if profile_svc.qtype(q) == 'scale' and q['key'] in out:
            mid = q['levels'][len(q['levels']) // 2]['value']
            out[q['key']] = {r['key']: out[q['key']].get(r['key'], mid) for r in q['rows']}
    return out
