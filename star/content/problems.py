"""
入门层题目素材：原题题面、Python 参考解、测试数据，以及前 5 道演示题的默认分步任务。

· 原题题面按普通 OJ 的写法（长句、书面语）——它就是大模型改造前的"通用题目"，
  测试报告里"改写前后平均句长"拿它和改造结果对比；
· 参考解是排序题代码行的唯一来源（校验器要求排序题的代码行逐字来自参考解），
  种子命令会用评测机实跑一遍，确认它能通过全部测试数据；
· 输出一律用英文单词或数字：Windows 开发机上子进程的标准输出编码不是 UTF-8，
  中文输出会被误判 WA，Docker 沙箱里则没有这个问题——统一用 ASCII 两边都稳；
· default_steps 是不经大模型的通用分步任务（不含兴趣主题），用于种子数据、大模型不可用时的兜底，
  也给教师一个"改造前后"的参照。

demo=True 的 5 道是演示素材；全部 15 道用于"任务改造质量"测试（15 题 × 2 个画像）。
"""

STAR_SOURCE_PREFIX = '星语·'

PROBLEMS = [
    # ── 演示题（5 道） ───────────────────────────────────────────────
    {
        'slug': 'sum_two', 'demo': True, 'knowledge': 'sequence',
        'title': '两数之和',
        'description': '输入两个整数 a 和 b，请编写程序计算并输出它们的和。本题用于熟悉程序的基本结构：'
                       '程序需要先从标准输入中依次读入两个整数，然后对它们进行加法运算，最后将运算结果输出到标准输出。',
        'input_desc': '输入共两行，第一行为整数 a，第二行为整数 b（-1000 ≤ a, b ≤ 1000）。',
        'output_desc': '输出一个整数，表示 a 与 b 的和。',
        'code': 'a = int(input())\nb = int(input())\ns = a + b\nprint(s)\n',
        'tests': [('3\n5\n', '8'), ('-2\n7\n', '5'), ('0\n0\n', '0'), ('1000\n-1000\n', '0'), ('123\n456\n', '579')],
        'default_steps': {
            'title': '两个数相加',
            'intro': ['输入两个数。', '算出它们的和。'],
            'theme': '',
            'steps': [
                {'type': 'choice', 'prompt': '程序先做什么？',
                 'options': ['读入两个数', '输出答案', '算出和'], 'answer': 0,
                 'hints': ['先有数，才能算。', '数从输入来。', '选"读入两个数"。'], 'knowledge': 'sequence'},
                {'type': 'fill', 'prompt': '把 a 和 b 加起来。', 'code': 's = a ____ b', 'answer': '+',
                 'hints': ['加法用什么符号？', '是加号。', '填 +。'], 'knowledge': 'sequence'},
                {'type': 'order', 'prompt': '把代码排成正确的顺序。',
                 'lines': ['a = int(input())', 'b = int(input())', 's = a + b', 'print(s)'],
                 'hints': ['先读入，再计算。', '输出放在最后。', '读 a，读 b，算 s，输出 s。'], 'knowledge': 'sequence'},
            ],
        },
    },
    {
        'slug': 'odd_even', 'demo': True, 'knowledge': 'condition',
        'title': '奇数还是偶数',
        'description': '给定一个正整数 n，判断它是奇数还是偶数。如果 n 能被 2 整除，说明它是偶数，输出 even；'
                       '否则说明它是奇数，输出 odd。请注意输出的单词全部为小写字母。',
        'input_desc': '输入一行，包含一个正整数 n（1 ≤ n ≤ 10^9）。',
        'output_desc': '如果 n 是偶数输出 even，否则输出 odd。',
        'code': 'n = int(input())\nif n % 2 == 0:\n    print("even")\nelse:\n    print("odd")\n',
        'tests': [('4\n', 'even'), ('7\n', 'odd'), ('1\n', 'odd'), ('1000000000\n', 'even'), ('999999999\n', 'odd')],
        'default_steps': {
            'title': '奇数还是偶数',
            'intro': ['输入一个数。', '说出它是奇数还是偶数。'],
            'theme': '',
            'steps': [
                {'type': 'choice', 'prompt': 'n 除以 2 余 0，n 是什么数？',
                 'options': ['偶数', '奇数'], 'answer': 0,
                 'hints': ['想一想 4 除以 2。', '4 能被 2 整除。', '余 0 就是偶数。'], 'knowledge': 'condition'},
                {'type': 'fill', 'prompt': '求 n 除以 2 的余数。', 'code': 'if n ____ 2 == 0:', 'answer': '%',
                 'hints': ['余数用一个符号。', '这个符号是百分号。', '填 %。'], 'knowledge': 'condition'},
                {'type': 'choice', 'prompt': '不是偶数时，输出什么？',
                 'options': ['print("odd")', 'print("even")'], 'answer': 0,
                 'hints': ['不是偶数就是奇数。', '奇数的英文是 odd。', '选 print("odd")。'], 'knowledge': 'condition'},
                {'type': 'order', 'prompt': '把代码排成正确的顺序。',
                 'lines': ['n = int(input())', 'if n % 2 == 0:', '    print("even")', 'else:', '    print("odd")'],
                 'hints': ['先读入 n。', 'if 在 else 前面。', 'print 跟在 if 或 else 下面。'], 'knowledge': 'condition'},
            ],
        },
    },
    {
        'slug': 'max_two', 'demo': True, 'knowledge': 'condition',
        'title': '较大的数',
        'description': '输入两个整数 a 和 b，输出其中较大的那个数。如果两个数相等，输出其中任意一个即可（它们是同一个值）。'
                       '这道题需要用到条件判断语句来比较两个数的大小。',
        'input_desc': '输入共两行，每行一个整数（-10^6 ≤ a, b ≤ 10^6）。',
        'output_desc': '输出一个整数，表示较大的数。',
        'code': 'a = int(input())\nb = int(input())\nif a > b:\n    print(a)\nelse:\n    print(b)\n',
        'tests': [('3\n9\n', '9'), ('10\n2\n', '10'), ('5\n5\n', '5'), ('-3\n-8\n', '-3'), ('0\n-1\n', '0')],
        'default_steps': {
            'title': '找出大的数',
            'intro': ['输入两个数。', '输出大的那个。'],
            'theme': '',
            'steps': [
                {'type': 'choice', 'prompt': '3 和 9，哪个大？',
                 'options': ['3', '9'], 'answer': 1,
                 'hints': ['比一比两个数。', '9 比 3 多。', '选 9。'], 'knowledge': 'condition'},
                {'type': 'fill', 'prompt': 'a 比 b 大时，输出 a。', 'code': 'if a ____ b:', 'answer': '>',
                 'hints': ['用比较符号。', '大于号的开口朝左。', '填 >。'], 'knowledge': 'condition'},
                {'type': 'order', 'prompt': '把代码排成正确的顺序。',
                 'lines': ['a = int(input())', 'b = int(input())', 'if a > b:', '    print(a)', 'else:', '    print(b)'],
                 'hints': ['先读入两个数。', 'if 在 else 前面。', 'print 放在 if 和 else 下面。'], 'knowledge': 'condition'},
            ],
        },
    },
    {
        'slug': 'count_up', 'demo': True, 'knowledge': 'loop',
        'title': '从 1 数到 n',
        'description': '输入一个正整数 n，按从小到大的顺序输出 1 到 n 之间的所有整数，每个数单独占一行。'
                       '这道题需要使用循环结构，让同一条输出语句重复执行多次。',
        'input_desc': '输入一行，包含一个正整数 n（1 ≤ n ≤ 100）。',
        'output_desc': '输出 n 行，第 i 行为整数 i。',
        'code': 'n = int(input())\nfor i in range(1, n + 1):\n    print(i)\n',
        'tests': [('3\n', '1\n2\n3'), ('1\n', '1'), ('5\n', '1\n2\n3\n4\n5'),
                  ('10\n', '\n'.join(str(i) for i in range(1, 11)))],
        'default_steps': {
            'title': '从 1 数到 n',
            'intro': ['输入一个数 n。', '从 1 数到 n。'],
            'theme': '',
            'steps': [
                {'type': 'choice', 'prompt': '从 1 数到 3，要说几个数？',
                 'options': ['2 个', '3 个', '4 个'], 'answer': 1,
                 'hints': ['1、2、3。', '数一数有几个。', '选 3 个。'], 'knowledge': 'loop'},
                {'type': 'fill', 'prompt': '让 i 从 1 走到 n。', 'code': 'for i in range(1, ____):', 'answer': 'n + 1',
                 'hints': ['range 不包括最后一个数。', '要到 n，就写 n 加 1。', '填 n + 1。'], 'knowledge': 'loop'},
                {'type': 'order', 'prompt': '把代码排成正确的顺序。',
                 'lines': ['n = int(input())', 'for i in range(1, n + 1):', '    print(i)'],
                 'hints': ['先读入 n。', 'for 在 print 上面。', 'print 要缩进。'], 'knowledge': 'loop'},
            ],
        },
    },
    {
        'slug': 'sum_to_n', 'demo': True, 'knowledge': 'loop',
        'title': '1 加到 n',
        'description': '输入一个正整数 n，计算 1 + 2 + 3 + … + n 的结果并输出。可以先设置一个变量用来保存累加的和，'
                       '初始值为 0，然后用循环依次把 1 到 n 加到这个变量上，最后输出它。',
        'input_desc': '输入一行，包含一个正整数 n（1 ≤ n ≤ 10000）。',
        'output_desc': '输出一个整数，表示 1 到 n 的和。',
        'code': 'n = int(input())\ntotal = 0\nfor i in range(1, n + 1):\n    total = total + i\nprint(total)\n',
        'tests': [('3\n', '6'), ('1\n', '1'), ('10\n', '55'), ('100\n', '5050'), ('10000\n', '50005000')],
        'default_steps': {
            'title': '1 加到 n',
            'intro': ['输入一个数 n。', '把 1 到 n 都加起来。'],
            'theme': '',
            'steps': [
                {'type': 'choice', 'prompt': 'total 一开始是多少？',
                 'options': ['0', '1', 'n'], 'answer': 0,
                 'hints': ['还没加任何数。', '什么都没加就是 0。', '选 0。'], 'knowledge': 'sequence'},
                {'type': 'fill', 'prompt': '把 i 加到 total 上。', 'code': '    total = total ____ i', 'answer': '+',
                 'hints': ['用加法。', '是加号。', '填 +。'], 'knowledge': 'loop'},
                {'type': 'choice', 'prompt': 'print(total) 放在哪里？',
                 'options': ['循环里面', '循环后面'], 'answer': 1,
                 'hints': ['加完再输出。', '循环结束才算加完。', '选循环后面。'], 'knowledge': 'loop'},
                {'type': 'order', 'prompt': '把代码排成正确的顺序。',
                 'lines': ['n = int(input())', 'total = 0', 'for i in range(1, n + 1):',
                           '    total = total + i', 'print(total)'],
                 'hints': ['先读入 n，再设 total。', '累加写在 for 里面。', '最后输出 total。'], 'knowledge': 'loop'},
            ],
        },
    },

    # ── 测试用题（10 道，与演示题一起构成 15 道入门题） ───────────────
    {
        'slug': 'double', 'knowledge': 'sequence', 'title': '两倍',
        'description': '输入一个整数 n，请计算它的两倍并输出。程序需要先读入 n，再把 n 乘以 2 的结果保存到一个变量中，最后输出这个变量。',
        'input_desc': '输入一行，包含一个整数 n（-10^6 ≤ n ≤ 10^6）。',
        'output_desc': '输出一个整数，表示 n 的两倍。',
        'code': 'n = int(input())\nd = n * 2\nprint(d)\n',
        'tests': [('3\n', '6'), ('0\n', '0'), ('-5\n', '-10'), ('1000000\n', '2000000')],
    },
    {
        'slug': 'minutes', 'knowledge': 'sequence', 'title': '小时换算分钟',
        'description': '已知一小时等于六十分钟。输入一个表示小时数的整数 h，请将它换算成分钟数后输出，换算时只需要把小时数乘以六十即可。',
        'input_desc': '输入一行，包含一个整数 h（0 ≤ h ≤ 1000）。',
        'output_desc': '输出一个整数，表示对应的分钟数。',
        'code': 'h = int(input())\nm = h * 60\nprint(m)\n',
        'tests': [('1\n', '60'), ('0\n', '0'), ('2\n', '120'), ('1000\n', '60000')],
    },
    {
        'slug': 'rect_area', 'knowledge': 'sequence', 'title': '长方形面积',
        'description': '输入长方形的长和宽（均为正整数），计算并输出长方形的面积。长方形的面积等于长与宽的乘积，请先分别读入长和宽，再进行计算。',
        'input_desc': '输入共两行，第一行为长 w，第二行为宽 h（1 ≤ w, h ≤ 1000）。',
        'output_desc': '输出一个整数，表示面积。',
        'code': 'w = int(input())\nh = int(input())\narea = w * h\nprint(area)\n',
        'tests': [('3\n4\n', '12'), ('1\n1\n', '1'), ('10\n20\n', '200'), ('1000\n1000\n', '1000000')],
    },
    {
        'slug': 'pass_fail', 'knowledge': 'condition', 'title': '及格了吗',
        'description': '输入一名同学的考试成绩 s。如果成绩大于或等于 60 分，说明考试及格，输出 pass；如果成绩低于 60 分，则说明没有及格，输出 fail。',
        'input_desc': '输入一行，包含一个整数 s（0 ≤ s ≤ 100）。',
        'output_desc': '输出 pass 或 fail。',
        'code': 's = int(input())\nif s >= 60:\n    print("pass")\nelse:\n    print("fail")\n',
        'tests': [('60\n', 'pass'), ('59\n', 'fail'), ('100\n', 'pass'), ('0\n', 'fail')],
    },
    {
        'slug': 'sign', 'knowledge': 'condition', 'title': '正数负数还是零',
        'description': '输入一个整数 n，判断它的符号：如果 n 大于 0 输出 positive，如果 n 小于 0 输出 negative，如果 n 恰好等于 0 则输出 zero。',
        'input_desc': '输入一行，包含一个整数 n（-10^9 ≤ n ≤ 10^9）。',
        'output_desc': '输出 positive、negative 或 zero。',
        'code': 'n = int(input())\nif n > 0:\n    print("positive")\nelif n < 0:\n    print("negative")\nelse:\n    print("zero")\n',
        'tests': [('5\n', 'positive'), ('-3\n', 'negative'), ('0\n', 'zero'), ('1000000000\n', 'positive')],
    },
    {
        'slug': 'abs_value', 'knowledge': 'condition', 'title': '绝对值',
        'description': '输入一个整数 n，输出它的绝对值。一个数的绝对值是它到 0 的距离：正数和 0 的绝对值是它本身，负数的绝对值是它的相反数。',
        'input_desc': '输入一行，包含一个整数 n（-10^9 ≤ n ≤ 10^9）。',
        'output_desc': '输出一个非负整数。',
        'code': 'n = int(input())\nif n < 0:\n    n = -n\nprint(n)\n',
        'tests': [('-5\n', '5'), ('7\n', '7'), ('0\n', '0'), ('-1000000000\n', '1000000000')],
    },
    {
        'slug': 'count_down', 'knowledge': 'loop', 'title': '倒数',
        'description': '输入一个正整数 n，从 n 开始倒着数，依次输出 n、n-1、……、1，每个数单独占一行。这需要让循环变量从大到小变化。',
        'input_desc': '输入一行，包含一个正整数 n（1 ≤ n ≤ 100）。',
        'output_desc': '输出 n 行。',
        'code': 'n = int(input())\nfor i in range(n, 0, -1):\n    print(i)\n',
        'tests': [('3\n', '3\n2\n1'), ('1\n', '1'), ('5\n', '5\n4\n3\n2\n1')],
    },
    {
        'slug': 'stars', 'knowledge': 'loop', 'title': '打印星星',
        'description': '输入一个正整数 n，输出 n 行，每一行都只包含一个星号字符。请使用循环语句完成，而不是把输出语句手动复制很多遍。',
        'input_desc': '输入一行，包含一个正整数 n（1 ≤ n ≤ 50）。',
        'output_desc': '输出 n 行，每行一个 *。',
        'code': 'n = int(input())\nfor i in range(n):\n    print("*")\n',
        'tests': [('3\n', '*\n*\n*'), ('1\n', '*'), ('5\n', '*\n*\n*\n*\n*')],
    },
    {
        'slug': 'times_table', 'knowledge': 'loop', 'title': '乘法表的一行',
        'description': '输入一个整数 n，依次输出 n×1、n×2、……、n×9 的结果，每个结果单独占一行，也就是乘法口诀表中与 n 有关的那九个乘积。',
        'input_desc': '输入一行，包含一个整数 n（1 ≤ n ≤ 9）。',
        'output_desc': '输出 9 行。',
        'code': 'n = int(input())\nfor i in range(1, 10):\n    print(n * i)\n',
        'tests': [('1\n', '\n'.join(str(i) for i in range(1, 10))),
                  ('3\n', '\n'.join(str(3 * i) for i in range(1, 10))),
                  ('9\n', '\n'.join(str(9 * i) for i in range(1, 10)))],
    },
    {
        'slug': 'sum_even', 'knowledge': 'loop', 'title': '偶数之和',
        'description': '输入一个正整数 n，计算 1 到 n 之间所有偶数的和并输出。可以用循环依次检查每个数，如果它能被 2 整除，就把它累加到总和里。',
        'input_desc': '输入一行，包含一个正整数 n（1 ≤ n ≤ 10000）。',
        'output_desc': '输出一个整数。',
        'code': 'n = int(input())\ntotal = 0\nfor i in range(1, n + 1):\n    if i % 2 == 0:\n        total = total + i\nprint(total)\n',
        'tests': [('4\n', '6'), ('1\n', '0'), ('10\n', '30'), ('10000\n', '25005000')],
    },
]

_BY_SLUG = {p['slug']: p for p in PROBLEMS}


def get_problem(slug):
    return _BY_SLUG.get(slug)


def source_of(slug):
    """题目在 Problem.source 里的标记，种子命令和查找都靠它把素材对应到题库里的那一行。"""
    return f'{STAR_SOURCE_PREFIX}{slug}'


def slug_of(problem):
    src = (problem.source or '') if problem else ''
    return src[len(STAR_SOURCE_PREFIX):] if src.startswith(STAR_SOURCE_PREFIX) else ''


def problem_row(slug):
    from judge.models import Problem
    return Problem.objects.filter(source=source_of(slug)).first()
