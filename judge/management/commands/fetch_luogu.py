"""
从洛谷抓取题目并导入到 ACM OJ 数据库（仅使用公开 API，无需登录）

用法示例：
  python manage.py fetch_luogu P1001 P1002
  python manage.py fetch_luogu --start P1001 --end P1020
  python manage.py fetch_luogu --file pids.txt --publish
"""
import re
import time

import requests
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from judge.models import Problem, Tag, TestCase

LUOGU_API = "https://www.luogu.com.cn/problem/{}?_contentOnly=1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.luogu.com.cn/",
    "x-luogu-type": "content-only",
    "Accept": "application/json",
}

# 洛谷难度 (0‒7) → 本站难度
DIFFICULTY_MAP = {
    0: "Easy",    # 暂无评定
    1: "Easy",    # 入门
    2: "Easy",    # 普及-
    3: "Medium",  # 普及/提高-
    4: "Medium",  # 普及+/提高
    5: "Hard",    # 提高+/省选-
    6: "Hard",    # 省选/NOI-
    7: "Hard",    # NOI/NOI+/CTSC
}

# 洛谷标签 ID → 中文名（仅常见 ID，未收录的会被忽略）
LUOGU_TAG_MAP = {
    1:  "循环",
    2:  "分支",
    3:  "排序",
    4:  "高精度",
    5:  "哈希表",
    7:  "数论",
    8:  "搜索",
    9:  "动态规划",
    10: "贪心",
    11: "图论",
    12: "数据结构",
    13: "模拟",
    14: "字符串",
    15: "数学",
    16: "递推",
    17: "递归",
    18: "分治",
    19: "二分",
    20: "双指针",
    25: "树",
    26: "计算几何",
    27: "位运算",
    28: "博弈论",
    29: "线性代数",
    30: "组合数学",
    31: "概率论",
    32: "构造",
    33: "思维",
    34: "暴力",
    38: "线段树",
    39: "树状数组",
    44: "最短路",
    45: "最小生成树",
    46: "网络流",
    47: "二分图",
    48: "强连通分量",
    49: "拓扑排序",
    50: "最近公共祖先",
    51: "树链剖分",
    54: "并查集",
    56: "堆",
    57: "单调队列/单调栈",
    58: "前缀和/差分",
    75: "背包DP",
    84: "树形DP",
    92: "区间DP",
    94: "数位DP",
    97: "计数",
}


def parse_pid_range(start: str, end: str) -> list[str]:
    """将 P1001 ~ P1010 展开成 ['P1001', ..., 'P1010']"""
    m1 = re.match(r'^([A-Za-z]+)(\d+)$', start)
    m2 = re.match(r'^([A-Za-z]+)(\d+)$', end)
    if not m1 or not m2 or m1.group(1).upper() != m2.group(1).upper():
        raise CommandError(f'无效的范围: {start} ~ {end}，前缀必须相同（如 P1001 ~ P1050）')
    prefix = m1.group(1).upper()
    a, b = int(m1.group(2)), int(m2.group(2))
    if a > b:
        raise CommandError(f'--start ({start}) 必须 <= --end ({end})')
    return [f'{prefix}{i}' for i in range(a, b + 1)]


def fetch_luogu_problem(pid: str) -> dict:
    """
    调用洛谷公开 API 获取题目数据，返回 problem dict。
    若题目不存在/未公开/网络错误则抛出异常。
    """
    url = LUOGU_API.format(pid.upper())
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f'网络请求失败: {e}') from e

    data = resp.json()
    code = data.get('code', -1)
    if code == 403:
        raise RuntimeError('题目需要登录或已被设为私有')
    if code == 404:
        raise RuntimeError('题目不存在')
    if code != 200:
        raise RuntimeError(f'洛谷 API 返回 code={code}')

    problem = data.get('currentData', {}).get('problem')
    if problem is None:
        raise RuntimeError('API 响应中缺少题目数据')
    return problem


class Command(BaseCommand):
    help = '从洛谷公开 API 抓取题目并导入数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            'pids', nargs='*', metavar='PID',
            help='洛谷题目 ID（可多个），如 P1001 P1002 B2002',
        )
        parser.add_argument(
            '--start', metavar='PID',
            help='批量抓取：范围起始（需同时指定 --end），如 --start P1001',
        )
        parser.add_argument(
            '--end', metavar='PID',
            help='批量抓取：范围结束，如 --end P1050',
        )
        parser.add_argument(
            '--file', metavar='FILE',
            help='从文本文件读取题目 ID 列表（每行一个）',
        )
        parser.add_argument(
            '--admin', default='admin', metavar='USERNAME',
            help='题目创建者用户名（默认 admin，需已存在于数据库）',
        )
        parser.add_argument(
            '--delay', type=float, default=1.5, metavar='SECONDS',
            help='两次请求间隔秒数（默认 1.5，请勿设置过小以免被封）',
        )
        parser.add_argument(
            '--publish', action='store_true', default=False,
            help='导入后立即设为已发布（默认不发布，需手动在后台发布）',
        )
        parser.add_argument(
            '--overwrite', action='store_true', default=False,
            help='若题目（按 source 字段匹配）已存在则覆盖更新',
        )

    def handle(self, *args, **options):
        # ── 收集 PID 列表 ──────────────────────────────────────────────
        pids: list[str] = [p.upper() for p in options['pids']]

        if options['start'] or options['end']:
            if not (options['start'] and options['end']):
                raise CommandError('--start 和 --end 必须同时指定')
            pids += parse_pid_range(options['start'], options['end'])

        if options['file']:
            try:
                with open(options['file'], encoding='utf-8') as f:
                    pids += [line.strip().upper() for line in f if line.strip()]
            except FileNotFoundError:
                raise CommandError(f'文件不存在: {options["file"]}')

        # 去重、保序
        seen: set[str] = set()
        pids = [p for p in pids if not (p in seen or seen.add(p))]

        if not pids:
            raise CommandError(
                '请至少提供一个题目 ID（位置参数）或使用 --start/--end/--file'
            )

        # ── 获取创建者 ─────────────────────────────────────────────────
        try:
            creator = User.objects.get(username=options['admin'])
        except User.DoesNotExist:
            raise CommandError(
                f'用户 "{options["admin"]}" 不存在。'
                '请先运行 `python manage.py seed_data`，或通过 --admin 指定已有用户名。'
            )

        delay    = options['delay']
        publish  = options['publish']
        overwrite = options['overwrite']
        ok = skip = fail = 0

        self.stdout.write(
            f'即将导入 {len(pids)} 道题目，创建者={options["admin"]}，'
            f'发布={publish}，覆盖={overwrite}，间隔={delay}s\n'
        )

        for i, pid in enumerate(pids):
            if i > 0:
                time.sleep(delay)

            prefix = f'[{i + 1}/{len(pids)}] {pid}'
            self.stdout.write(f'{prefix} ...', ending=' ')
            self.stdout.flush()

            # ── 抓取 ───────────────────────────────────────────────────
            try:
                raw = fetch_luogu_problem(pid)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'失败: {e}'))
                fail += 1
                continue

            title  = raw.get('title') or pid
            source = f'洛谷 {pid}'

            # ── 重复检测 ───────────────────────────────────────────────
            existing = Problem.objects.filter(source=source).first()
            if existing and not overwrite:
                self.stdout.write(self.style.WARNING('已存在，跳过（加 --overwrite 可覆盖）'))
                skip += 1
                continue

            # ── 字段映射 ───────────────────────────────────────────────
            difficulty   = DIFFICULTY_MAP.get(raw.get('difficulty', 0), 'Easy')
            limits       = raw.get('limits') or {}
            time_limit   = (limits.get('time')   or [1000])[0]
            # 洛谷内存单位是 KB，本站存 MB
            memory_limit = ((limits.get('memory') or [262144])[0]) // 1024

            background   = (raw.get('background') or '').strip()
            desc_body    = (raw.get('description') or '').strip()
            description  = '\n\n'.join(filter(None, [background, desc_body]))
            input_desc   = (raw.get('inputFormat')  or '').strip()
            output_desc  = (raw.get('outputFormat') or '').strip()
            hint         = (raw.get('hint') or '').strip()

            samples = raw.get('samples') or []
            sample_input  = samples[0][0] if samples else ''
            sample_output = samples[0][1] if samples else ''

            # ── 写入数据库 ─────────────────────────────────────────────
            if existing and overwrite:
                problem = existing
                problem.title         = title
                problem.description   = description
                problem.input_desc    = input_desc
                problem.output_desc   = output_desc
                problem.sample_input  = sample_input
                problem.sample_output = sample_output
                problem.hint          = hint
                problem.difficulty    = difficulty
                problem.time_limit    = time_limit
                problem.memory_limit  = memory_limit
                problem.is_published  = publish
                problem.save()
                problem.tags.clear()
                TestCase.objects.filter(problem=problem).delete()
                action = '已更新'
            else:
                problem = Problem.objects.create(
                    title         = title,
                    description   = description,
                    input_desc    = input_desc,
                    output_desc   = output_desc,
                    sample_input  = sample_input,
                    sample_output = sample_output,
                    hint          = hint,
                    difficulty    = difficulty,
                    time_limit    = time_limit,
                    memory_limit  = memory_limit,
                    source        = source,
                    is_published  = publish,
                    created_by    = creator,
                )
                action = '已创建'

            # ── 标签 ───────────────────────────────────────────────────
            for tag_id in (raw.get('tags') or []):
                tag_name = LUOGU_TAG_MAP.get(tag_id)
                if tag_name:
                    tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                    problem.tags.add(tag_obj)

            # ── 样例（公开 API 仅含样例，非全量测试数据）──────────────
            for idx, (inp, out) in enumerate(samples):
                TestCase.objects.create(
                    problem       = problem,
                    input_data    = inp,
                    expected_output = out,
                    is_sample     = True,
                    sort_order    = idx,
                )

            tag_count = problem.tags.count()
            self.stdout.write(self.style.SUCCESS(
                f'{action} — {title} | {difficulty} | '
                f'{time_limit}ms / {memory_limit}MB | {tag_count} 个标签 | {len(samples)} 个样例'
            ))
            ok += 1

        # ── 汇总 ───────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'导入完成：成功 {ok} 题，跳过 {skip} 题，失败 {fail} 题'
        ))
        if ok and not publish:
            self.stdout.write(
                self.style.WARNING(
                    '提示：题目默认未发布。可在 Django Admin 后台批量发布，'
                    '或重新运行时加 --publish 参数。'
                )
            )
        if ok:
            self.stdout.write(
                '注意：洛谷公开 API 仅返回样例数据，不含完整测试点。'
                '如需完整评测，请在 Django Admin 后台手动补充测试数据。'
            )
