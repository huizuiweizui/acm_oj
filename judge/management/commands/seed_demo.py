"""
写入一套演示数据，便于本地快速体验三端功能（可重复执行，已存在则跳过）。

    python manage.py seed_demo

账号（密码均为 demo1234）：
    demo_admin    总管理员
    demo_teacher  教师（创建了团队「演示一班」）
    demo_s1~s6    学生（demo_s1 为队长）
"""
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from judge.models import (
    Announcement, Assignment, AssignmentProblem, Problem, Submission, Tag, Team,
    TeamMembership, TestCase, UserProfile,
)

PASSWORD = 'demo1234'

PROBLEMS = [
    ('A+B Problem', '入门', ['模拟']),
    ('数组求和', '入门', ['模拟', '前缀和']),
    ('区间和查询', '普及-', ['前缀和']),
    ('最长上升子序列', '普及/提高-', ['动态规划']),
    ('01 背包', '普及-', ['动态规划']),
    ('单源最短路', '普及+/提高', ['图论', '最短路']),
    ('最小生成树', '普及+/提高', ['图论']),
    ('并查集模板', '普及/提高-', ['数据结构', '并查集']),
    ('线段树区间加', '提高+/省选-', ['数据结构', '线段树']),
    ('KMP 字符串匹配', '普及+/提高', ['字符串']),
    ('快速幂', '普及-', ['数学']),
    ('二分答案', '普及/提高-', ['二分']),
]

STUDENTS = [
    ('demo_s1', '张三', '2023001'),
    ('demo_s2', '李四', '2023002'),
    ('demo_s3', '王五', '2023003'),
    ('demo_s4', '赵六', '2023004'),
    ('demo_s5', '孙七', '2023005'),
    ('demo_s6', '周八', '2023006'),
]


def _user(username, role, **profile):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(PASSWORD)
        user.save()
    UserProfile.objects.update_or_create(user=user, defaults={'role': role, **profile})
    return user


class Command(BaseCommand):
    help = '写入演示数据（教师 / 学生 / 团队 / 题目 / 提交 / 作业）'

    @transaction.atomic
    def handle(self, *args, **options):
        if Team.objects.filter(name='演示一班').exists():
            self.stdout.write(self.style.WARNING('演示数据已存在，跳过'))
            return

        rnd = random.Random(42)
        now = timezone.now()

        admin = _user('demo_admin', 'admin', is_super_admin=True)
        admin.is_staff = admin.is_superuser = True
        admin.save()
        teacher = _user('demo_teacher', 'teacher', real_name='陈老师')
        students = [
            _user(u, 'student', real_name=name, student_id=sid, major='计算机科学与技术', grade='2023级')
            for u, name, sid in STUDENTS
        ]

        problems = []
        for title, diff, tags in PROBLEMS:
            p, created = Problem.objects.get_or_create(title=title, defaults={
                'description': f'{title}：读入两个整数 $a, b$，输出 $a+b$。（演示题面）',
                'input_desc': '一行两个整数 a b',
                'output_desc': '一个整数',
                'sample_input': '1 2',
                'sample_output': '3',
                'difficulty': diff,
                'is_published': True,
                'source': '演示数据',
                'created_by': teacher,
            })
            if created:
                for i, (a, b) in enumerate([(1, 2), (100, 200), (-5, 7)]):
                    TestCase.objects.create(problem=p, input_data=f'{a} {b}\n',
                                            expected_output=f'{a + b}\n', sort_order=i)
            p.tags.add(*[Tag.objects.get_or_create(name=t)[0] for t in tags])
            problems.append(p)

        team = Team.objects.create(name='演示一班', description='三端功能演示团队',
                                   creator=teacher, invite_code='DEMO2026', need_review=True)
        for i, s in enumerate(students):
            TeamMembership.objects.create(team=team, user=s, role='captain' if i == 0 else 'member',
                                          remark=s.profile.real_name)

        # 提交：越靠前的学生越勤奋，时间分布在近 60 天
        statuses = ['AC', 'WA', 'TLE', 'RE', 'CE']
        for idx, s in enumerate(students):
            for p in rnd.sample(problems, k=max(3, len(problems) - idx * 2)):
                tries = rnd.randint(1, 4)
                solved = rnd.random() < 0.85 - idx * 0.08
                for t in range(tries):
                    last = t == tries - 1
                    status = 'AC' if (last and solved) else rnd.choice(statuses[1:])
                    sub = Submission.objects.create(
                        user=s, problem=p, language=rnd.choice(['C++', 'C++', 'Python', 'Java']),
                        code='#include <bits/stdc++.h>\nint main(){ long long a,b; std::cin>>a>>b; std::cout<<a+b; }\n',
                        status=status, time_used=rnd.randint(1, 900), memory_used=rnd.randint(800, 9000),
                    )
                    Submission.objects.filter(pk=sub.pk).update(
                        submitted_at=now - timedelta(days=rnd.randint(0, 60), minutes=rnd.randint(0, 1440)))

        Announcement.objects.create(team=team, title='欢迎加入演示一班', is_pinned=True, created_by=teacher,
                                    content='本周请完成 **第一周作业**，有问题在讨论区提问。')
        asgn = Assignment.objects.create(team=team, title='第一周作业', created_by=teacher,
                                         description='入门与前缀和练习',
                                         start_at=now - timedelta(days=20), deadline=now - timedelta(days=5))
        for i, p in enumerate(problems[:4]):
            AssignmentProblem.objects.create(assignment=asgn, problem=p, sort_order=i)
        asgn2 = Assignment.objects.create(team=team, title='第二周作业', created_by=teacher,
                                          description='动态规划与图论', start_at=now - timedelta(days=2),
                                          deadline=now + timedelta(days=5))
        for i, p in enumerate(problems[3:8]):
            AssignmentProblem.objects.create(assignment=asgn2, problem=p, sort_order=i)

        self.stdout.write(self.style.SUCCESS(
            f'完成：{len(problems)} 道题、{len(students)} 名学生、团队「{team.name}」（邀请码 {team.invite_code}）\n'
            f'账号 demo_admin / demo_teacher / demo_s1~s6，密码均为 {PASSWORD}'
        ))
