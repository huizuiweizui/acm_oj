"""
导入示例数据：标签、题目、测试用例
python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from judge.models import Tag, Problem, TestCase, UserProfile


class Command(BaseCommand):
    help = '导入 ACM OJ 示例数据'

    def handle(self, *args, **options):
        # 创建管理员
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@acmoj.com', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.create(user=admin_user, role='admin')
            self.stdout.write(self.style.SUCCESS('创建管理员: admin / admin123'))

        # 创建标签
        tag_names = ['动态规划', '贪心', '图论', '搜索', '数据结构', '数学', '字符串',
                     '模拟', '排序', '二分', '递归', '分治', '位运算', '树', '并查集']
        tags = {}
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(name=name)
            tags[name] = t
        self.stdout.write(self.style.SUCCESS(f'创建 {len(tags)} 个标签'))

        # 创建示例题目
        problems_data = [
            {
                'title': 'A+B Problem',
                'description': '给定两个整数 $a$ 和 $b$，请计算 $a+b$ 的值。',
                'input_desc': '输入一行包含两个整数 $a$ 和 $b$，以空格分隔。\n\n$-10^9 \\le a, b \\le 10^9$',
                'output_desc': '输出一个整数，表示 $a+b$ 的值。',
                'sample_input': '1 2',
                'sample_output': '3',
                'difficulty': 'Easy',
                'tags': ['模拟'],
                'test_cases': [
                    ('1 2', '3'), ('0 0', '0'), ('-1 1', '0'),
                    ('1000000000 1000000000', '2000000000'),
                ],
            },
            {
                'title': '最大子段和',
                'description': '给定一个长度为 $n$ 的整数序列，找出一个连续子段（子数组），使得该子段的元素之和最大。输出这个最大值。',
                'input_desc': '第一行一个整数 $n$ ($1 \\le n \\le 2 \\times 10^5$)。\n\n第二行 $n$ 个整数 $a_1, a_2, \\ldots, a_n$ ($|a_i| \\le 10^9$)。',
                'output_desc': '输出一个整数，表示最大子段和。',
                'sample_input': '5\n-2 1 -3 4 -1',
                'sample_output': '4',
                'hint': '经典的 Kadane 算法，时间复杂度 O(n)。',
                'difficulty': 'Medium',
                'tags': ['动态规划'],
                'test_cases': [
                    ('5\n-2 1 -3 4 -1', '4'),
                    ('1\n-1', '-1'),
                    ('3\n1 2 3', '6'),
                ],
            },
            {
                'title': '最短路径',
                'description': '给定一个 $n$ 个点 $m$ 条边的有向图，求从起点 $s$ 到终点 $t$ 的最短路径长度。',
                'input_desc': '第一行四个整数 $n, m, s, t$。\n\n接下来 $m$ 行，每行三个整数 $u, v, w$，表示一条从 $u$ 到 $v$，权值为 $w$ 的有向边。',
                'output_desc': '输出最短路径长度，若不可达输出 -1。',
                'sample_input': '4 4 1 4\n1 2 1\n2 3 2\n3 4 3\n1 4 10',
                'sample_output': '6',
                'difficulty': 'Hard',
                'tags': ['图论'],
                'test_cases': [
                    ('4 4 1 4\n1 2 1\n2 3 2\n3 4 3\n1 4 10', '6'),
                ],
            },
        ]

        for pdata in problems_data:
            tag_list = pdata.pop('tags')
            tc_list = pdata.pop('test_cases')
            p, created = Problem.objects.get_or_create(
                title=pdata['title'],
                defaults={**pdata, 'created_by': admin_user, 'is_published': True},
            )
            if created:
                for tname in tag_list:
                    if tname in tags:
                        p.tags.add(tags[tname])
                for i, (inp, out) in enumerate(tc_list):
                    TestCase.objects.create(
                        problem=p, input_data=inp, expected_output=out,
                        is_sample=(i == 0), sort_order=i,
                    )
                self.stdout.write(self.style.SUCCESS(f'  创建题目: {p.title}'))

        self.stdout.write(self.style.SUCCESS('示例数据导入完成！'))
