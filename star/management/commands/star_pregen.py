"""
提前生成演示内容（任务书 6.8："提前生成并审核演示内容，录屏时不现场等待大模型"）。

    python manage.py star_pregen                      为 4 个演示学生各生成一组大模型改造草稿
    python manage.py star_pregen --users star_jie     只给指定学生生成（逗号分隔）
    python manage.py star_pregen --replace            先删掉这些学生"没有作答记录"的旧任务（如种子数据里的默认版本）

启蒙层生成 6 个关卡、入门层生成 5 道演示题，每个都走完整的生成-校验-修复闭环。
生成结果是草稿（或"生成未通过"），仍需教师在审核页逐个预览、通过后学生才看得到。
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max

from judge.services.judge_queue import RunQueueBusy
from star.content.learners import LEARNERS, TEACHER_USERNAME
from star.content.levels import LEVELS
from star.content.problems import PROBLEMS, problem_row
from star.models import AdaptedTask, LearnerProfile
from star.services import adapt, llm


class Command(BaseCommand):
    help = '用大模型为演示学生批量生成改造任务草稿'

    def add_arguments(self, parser):
        parser.add_argument('--users', default=','.join(s['username'] for s in LEARNERS))
        parser.add_argument('--replace', action='store_true', help='先删除这些学生没有作答记录的旧任务')
        parser.add_argument('--teacher', default=TEACHER_USERNAME, help='记为发起教师')

    def handle(self, *args, **opts):
        if not llm.is_configured():
            raise CommandError('未配置大模型：请先在 .env 中填写 LLM_API_KEY / LLM_API_URL / LLM_MODEL')
        teacher = User.objects.filter(username=opts['teacher']).first()
        counts = {'draft': 0, 'failed': 0, 'error': 0}

        for username in [u.strip() for u in opts['users'].split(',') if u.strip()]:
            lp = LearnerProfile.objects.select_related('user').filter(user__username=username).first()
            if lp is None or not lp.layer:
                self.stdout.write(self.style.WARNING(f'{username}：没有画像或未定层级，跳过'))
                continue
            if opts['replace']:
                n, _ = AdaptedTask.objects.filter(student=lp.user, attempts__isnull=True).delete()
                self.stdout.write(f'{username}：删除旧任务 {n} 条')

            if lp.layer == 'enlighten':
                keys = [lv['key'] for lv in LEVELS]
            else:
                keys = [p['slug'] for p in PROBLEMS if p.get('demo')]
            order = AdaptedTask.objects.filter(student=lp.user).aggregate(m=Max('sort_order'))['m'] or 0

            for i, key in enumerate(keys, 1):
                problem = None
                if lp.layer == 'intro':
                    problem = problem_row(key)
                    if problem is None:
                        raise CommandError(f'题库里没有 {key}，请先运行 manage.py seed_star')
                task = AdaptedTask.objects.create(student=lp.user, layer=lp.layer, template=key, problem=problem,
                                                  sort_order=order + i, created_by=teacher)
                try:
                    adapt.generate(task, mode='llm', tag='pregen')
                except (adapt.MaterialError, adapt.LLMUnavailable, RunQueueBusy) as e:
                    task.delete()
                    counts['error'] += 1
                    self.stdout.write(self.style.ERROR(f'  {username} · {key}：{e}'))
                    continue
                runs = [e for e in task.validation_log if e.get('run') == task.validation_log[-1]['run']]
                counts[task.status] += 1
                mark = self.style.SUCCESS('✓ 草稿') if task.status == 'draft' else self.style.ERROR('✗ 未通过')
                self.stdout.write(f'  {username} · {key} · {task.content.get("title", "")}：{mark}'
                                  f'（{len(runs)} 次生成）')
                if task.status == 'failed':
                    for err in runs[-1].get('errors', [])[:3]:
                        self.stdout.write(f'      - {err}')

        self.stdout.write(self.style.SUCCESS(
            f'完成：草稿 {counts["draft"]} 个，未通过 {counts["failed"]} 个，出错 {counts["error"]} 个。'
            '请到 星语 → 教师端 → 学生 → 任务 里逐个审核。'))
