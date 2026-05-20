"""
洛谷题目爬虫 (重构版)
用法: python manage.py crawl_luogu [选项]

主要改进:
  ✓ 请求重试 + 指数退避(网络抖动 / 429 / 5xx 自动恢复)
  ✓ 持久化日志 (logs/crawl_luogu_YYYYMMDD_HHMMSS.log)
  ✓ 进度自动保存,支持 --resume 从上次中断处继续
  ✓ 失败 PID 自动收集,支持 --retry-failed 一键重跑
  ✓ 难度筛选 (--min-difficulty / --max-difficulty)
  ✓ 完整保留多组样例
  ✓ 标签内存缓存(每个标签只查一次数据库)
  ✓ Cookie 支持环境变量 LUOGU_UID / LUOGU_CLIENT_ID
  ✓ 汇总统计:耗时 / 速率 / 失败列表

数据库模型字段保持不变,与原版完全兼容。
"""
import json
import re
import sys
import time
import random
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import requests
from django.core.management.base import BaseCommand
from judge.models import Problem, Tag, TestCase


# ===================== 配置区域 =====================
LUOGU_COOKIE = {
    '_uid': os.getenv('LUOGU_UID', '1750610'),
    '__client_id': os.getenv(
        'LUOGU_CLIENT_ID',
        'ykhyhbmzwkn7jypxd2y6lqna53evk5qluqsszviwg6s74gng',
    ),
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.luogu.com.cn/',
    'x-lentille-request': 'content-only',
    'Accept': 'application/json',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 洛谷难度数字 → 中文等级
DIFFICULTY_MAP = {
    0: '暂无评定',
    1: '入门',
    2: '普及-',
    3: '普及/提高-',
    4: '普及+/提高',
    5: '提高+/省选-',
    6: '省选/NOI-',
    7: 'NOI/NOI+/CTSC',
}

# 洛谷常用算法标签 ID → 名称
TAG_MAP = {
    1: '模拟', 2: '字符串', 3: '排序', 4: '枚举',
    5: '贪心', 6: '递推', 7: '递归', 8: '搜索',
    9: '深搜DFS', 10: '广搜BFS', 11: '动态规划',
    12: '分治', 13: '高精度', 14: '数论', 15: '图论',
    16: '数据结构', 17: '树形结构', 18: '线段树',
    19: '二分', 20: '暴力', 21: '数学', 22: '位运算',
    23: '并查集', 24: '最短路', 25: '最小生成树',
    26: '拓扑排序', 27: '哈希', 28: '前缀和', 29: '差分',
    30: '双指针', 31: '栈', 32: '队列', 33: '链表',
    34: '二叉树', 35: '堆', 36: 'ST表', 37: '树状数组',
    38: '平衡树', 39: '字典树', 40: '后缀数组',
    41: 'KMP', 42: 'AC自动机', 43: '网络流', 44: '费用流',
    45: '二分图', 46: '状压DP', 47: '区间DP', 48: '树形DP',
    49: '数位DP', 50: '博弈论', 51: '概率', 52: '组合数学',
    53: '矩阵', 54: '几何', 55: '背包', 56: '优先队列',
    57: '单调栈', 58: '单调队列', 59: '倍增', 60: 'LCA',
}

# 爬虫运行时参数
DELAY_MIN = 1.5
DELAY_MAX = 3.5
TARGET_COUNT = 200
SOURCE_PREFIX = '洛谷-'  # source 字段前缀, 同时作为去重键(如 "洛谷-P1001")
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
REST_EVERY = 20             # 每爬 N 道额外休息
REST_DURATION = (3.0, 6.0)  # 额外休息秒数范围

# 日志 / 进度文件
LOG_DIR = Path('logs')
PROGRESS_FILE = LOG_DIR / 'crawl_luogu_progress.json'
# ====================================================


class Command(BaseCommand):
    help = '从洛谷爬取算法题目并存入数据库 (重构版)'

    # ---------- 参数 ----------
    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=TARGET_COUNT,
                            help=f'要爬取的题目数量(默认 {TARGET_COUNT})')
        parser.add_argument('--start-page', type=int, default=1,
                            help='从第几页开始(默认第 1 页,被 --resume 覆盖)')
        parser.add_argument('--update', action='store_true',
                            help='强制更新已存在的题目(默认跳过)')
        parser.add_argument('--resume', action='store_true',
                            help='从进度文件恢复起始页')
        parser.add_argument('--min-difficulty', type=int, default=0,
                            help='最低难度 0~7(见 DIFFICULTY_MAP)')
        parser.add_argument('--max-difficulty', type=int, default=7,
                            help='最高难度 0~7')
        parser.add_argument('--retry-failed', action='store_true',
                            help='只重试上次进度文件中失败的 PID')
        parser.add_argument('--no-gen-tests', action='store_false', dest='gen_tests',
                            help='禁用 LLM 测试点生成（默认开启）')
        parser.add_argument('--tests-count', type=int, default=5,
                            help='每道题测试点总数目标（默认 5，样例不足时由 LLM 补齐）')

    # ---------- 入口 ----------
    def handle(self, *args, **options):
        target = options['count']
        start_page = options['start_page']
        force_update = options['update']
        resume = options['resume']
        min_diff = options['min_difficulty']
        max_diff = options['max_difficulty']
        retry_failed = options['retry_failed']
        gen_tests = options['gen_tests']
        tests_count = options['tests_count']

        self._setup_logger()

        # 解析 created_by 字段所需的默认用户(若模型为 NOT NULL FK 必需)
        self._default_user = self._resolve_default_user()

        progress = self._load_progress()
        if resume and progress.get('last_page'):
            start_page = progress['last_page']
            self._info(f'📌 从进度文件恢复, 起始页 = {start_page}')

        self._banner(target, start_page, force_update, min_diff, max_diff)

        session = requests.Session()
        session.headers.update(HEADERS)
        session.cookies.update(LUOGU_COOKIE)

        started_at = time.time()
        self._tag_cache = {}
        self._session = session

        # 累积的失败 PID(无论哪种模式都跨次保留)
        failed_pids = list(progress.get('failed_pids', []))
        # 已成功爬取的 PID 集合(--resume 时跳过重复爬取)
        processed_pids = set(progress.get('processed_pids', []))

        # === 模式选择: 重试失败 vs 正常分页 ===
        if retry_failed:
            problem_ids = list(failed_pids)
            if not problem_ids:
                self._info('没有可以重试的失败 PID')
                return
            self._info(f'🔁 重试模式: 共 {len(problem_ids)} 个失败 PID')
        else:
            self._info('\n📋 第一步: 获取题目列表...')
            problem_ids = self._fetch_problem_list(
                session, target, start_page, min_diff, max_diff, progress,
                processed_pids,
            )
            if not problem_ids:
                self._error('未获取到任何题目, 请检查 Cookie / 难度区间是否合理')
                return
            self._info(f'  获取到 {len(problem_ids)} 个题目编号')

        # === 抓详情 ===
        self._info('\n📝 第二步: 爬取题目详情...')
        success = skip = fail = 0

        for i, pid in enumerate(problem_ids, 1):
            source_key = f'{SOURCE_PREFIX}{pid}'
            existing = Problem.objects.filter(source=source_key).first()

            # 题目已存在且不强制更新：检查测试点是否够，不够则补生成
            if not force_update and existing:
                tc_count = TestCase.objects.filter(problem=existing).count()
                if not gen_tests or tc_count >= tests_count:
                    self._info(f'  [{i}/{len(problem_ids)}] {pid} - 已存在({tc_count} 个测试点), 跳过')
                    skip += 1
                    if pid in failed_pids:
                        failed_pids.remove(pid)
                    continue
                # 测试点不足，补生成
                self._info(f'  [{i}/{len(problem_ids)}] {pid} - 已存在但测试点不足({tc_count}/{tests_count})，补生成...')
                raw_samples = list(
                    TestCase.objects.filter(problem=existing, is_sample=True)
                    .values_list('input_data', 'expected_output')
                )
                n = self._generate_test_cases(existing, raw_samples, tests_count, pid)
                self._info(f'    → 补生成测试点 {n} 个')
                skip += 1
                if pid in failed_pids:
                    failed_pids.remove(pid)
                continue

            try:
                detail = self._fetch_problem_detail(session, pid)
                if detail:
                    problem = self._save_problem(detail)
                    if gen_tests:
                        n = self._generate_test_cases(
                            problem, detail.get('raw_samples', []), tests_count, pid
                        )
                        self._info(f'    → 生成测试点 {n} 个')
                    success += 1
                    processed_pids.add(pid)
                    self._success(
                        f'  [{i}/{len(problem_ids)}] ✓ {pid} - {detail.get("title", "")}'
                    )
                    if pid in failed_pids:
                        failed_pids.remove(pid)
                else:
                    fail += 1
                    if pid not in failed_pids:
                        failed_pids.append(pid)
                    self._error(f'  [{i}/{len(problem_ids)}] ✗ {pid} - 获取失败')
            except Exception as e:
                fail += 1
                if pid not in failed_pids:
                    failed_pids.append(pid)
                self._error(f'  [{i}/{len(problem_ids)}] ✗ {pid} - 异常: {e}')

            # 每题随机延迟
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            # 每 N 题额外休息
            if i % REST_EVERY == 0 and i < len(problem_ids):
                extra = random.uniform(*REST_DURATION)
                self._info(f'\n  ☕ 已爬取 {i} 道, 休息 {extra:.1f} 秒...\n')
                time.sleep(extra)

            # 每 10 题持久化进度,确保中断不丢
            if i % 10 == 0:
                self._save_progress({
                    'last_page': progress.get('last_page', start_page),
                    'failed_pids': failed_pids,
                    'processed_pids': list(processed_pids),
                    'updated_at': datetime.now().isoformat(timespec='seconds'),
                })

        # 结束时再保存一次
        self._save_progress({
            'last_page': progress.get('last_page', start_page),
            'failed_pids': failed_pids,
            'processed_pids': list(processed_pids),
            'updated_at': datetime.now().isoformat(timespec='seconds'),
        })

        elapsed = time.time() - started_at
        rate = success / elapsed if elapsed > 0 else 0.0
        self._summary(success, skip, fail, elapsed, rate, failed_pids)

    # ===================== 列表抓取 =====================

    def _fetch_problem_list(self, session, target, start_page,
                            min_diff, max_diff, progress, processed_pids=None):
        """分页抓取题目列表, 边抓边按难度过滤, 跳过已成功的 PID"""
        if processed_pids is None:
            processed_pids = set()
        problem_ids = []
        page = start_page

        while len(problem_ids) < target:
            try:
                resp = self._request_with_retry(
                    session,
                    'https://www.luogu.com.cn/problem/list',
                    params={'type': 'P', 'page': page},
                    timeout=15,
                )
                if resp is None or resp.status_code != 200:
                    code = resp.status_code if resp is not None else 'N/A'
                    self._error(f'  第 {page} 页请求失败, 状态码: {code}')
                    break

                problems = self._extract_problems_from_list(resp.json())
                if not problems:
                    self._warn(f'  第 {page} 页无更多题目, 停止')
                    break

                kept = already_done = 0
                for p in problems:
                    pid = p.get('pid', '')
                    diff = p.get('difficulty', 0) or 0
                    if pid and pid.startswith('P') and min_diff <= diff <= max_diff:
                        if pid in processed_pids:
                            already_done += 1
                            continue
                        problem_ids.append(pid)
                        kept += 1

                done_hint = f', 已成功跳过 {already_done}' if already_done else ''
                self._info(
                    f'  第 {page} 页: 共 {len(problems)} 题, '
                    f'难度过滤后保留 {kept}{done_hint}, 累计 {len(problem_ids)}'
                )

                # 边抓边写进度,中断后 --resume 能从这一页恢复
                progress['last_page'] = page
                self._save_progress({
                    'last_page': page,
                    'failed_pids': progress.get('failed_pids', []),
                    'processed_pids': list(processed_pids),
                    'updated_at': datetime.now().isoformat(timespec='seconds'),
                })

                if len(problem_ids) >= target:
                    problem_ids = problem_ids[:target]
                    break

                page += 1
                time.sleep(random.uniform(1.0, 2.0))

            except Exception as e:
                self._error(f'  第 {page} 页错误: {e}')
                break

        return problem_ids

    def _extract_problems_from_list(self, data):
        """兼容 data / currentData 两种顶层结构"""
        for key in ('data', 'currentData'):
            obj = data.get(key)
            if isinstance(obj, dict):
                prob_obj = obj.get('problems', {})
                if isinstance(prob_obj, dict):
                    result = prob_obj.get('result', [])
                    if result:
                        return result
        return []

    # ===================== 详情抓取 =====================

    def _fetch_problem_detail(self, session, pid):
        """获取单题详情(题面 / 限制 / 样例 / 标签)"""
        url = f'https://www.luogu.com.cn/problem/{pid}'
        try:
            resp = self._request_with_retry(session, url, timeout=15)
            if resp is None or resp.status_code != 200:
                return None
            data = resp.json()
        except Exception as e:
            self._error(f'    {pid} 请求异常: {e}')
            return None

        problem = None
        for key in ('data', 'currentData'):
            obj = data.get(key)
            if isinstance(obj, dict):
                problem = obj.get('problem')
                if problem:
                    break
        if not problem:
            return None

        # ----- 题面 -----
        content = problem.get('content') or {}
        if not isinstance(content, dict):
            content = {}

        description = (content.get('description') or '').strip()
        background = (content.get('background') or '').strip()
        format_i = (content.get('formatI') or '').strip()
        format_o = (content.get('formatO') or '').strip()
        hint = (content.get('hint') or '').strip()

        if background and description:
            full_description = f'{background}\n\n{description}'
        else:
            full_description = background or description

        # ----- 时间 / 内存限制 -----
        limits = problem.get('limits') or {}
        time_vals = limits.get('time') or [1000]
        mem_vals = limits.get('memory') or [262144]

        time_limit = (
            max(time_vals)
            if isinstance(time_vals, list) and time_vals else 1000
        )
        memory_limit = (
            max(mem_vals) // 1024
            if isinstance(mem_vals, list) and mem_vals else 256
        )

        # ----- 样例(全部保留)-----
        sample_input, sample_output = self._format_samples(
            problem.get('samples') or []
        )

        # ----- 标签 -----
        tag_ids = problem.get('tags') or []
        tag_names = [
            TAG_MAP[tid] for tid in tag_ids
            if isinstance(tid, int) and tid in TAG_MAP
        ]
        unknown = [tid for tid in tag_ids
                   if isinstance(tid, int) and tid not in TAG_MAP]
        if unknown:
            self.logger.debug(f'{pid} 未知标签 ID: {unknown}')

        return {
            'pid': pid,
            'title': problem.get('title', ''),
            'difficulty': problem.get('difficulty', 0),
            'description': full_description,
            'input_format': format_i,
            'output_format': format_o,
            'sample_input': sample_input,
            'sample_output': sample_output,
            'hint': hint,
            'tags': tag_names,
            'time_limit': time_limit,
            'memory_limit': memory_limit,
            'raw_samples': problem.get('samples') or [],
        }

    def _format_samples(self, samples):
        """多组样例合并为单一字符串(用 ### 样例 N 分隔)"""
        if not samples:
            return '', ''
        inputs, outputs = [], []
        for s in samples:
            if isinstance(s, (list, tuple)) and len(s) >= 2:
                inputs.append(str(s[0]).strip())
                outputs.append(str(s[1]).strip())
        if not inputs:
            return '', ''
        if len(inputs) == 1:
            return inputs[0], outputs[0]
        joined_in = '\n\n'.join(
            f'### 样例 {i + 1}\n{t}' for i, t in enumerate(inputs)
        )
        joined_out = '\n\n'.join(
            f'### 样例 {i + 1}\n{t}' for i, t in enumerate(outputs)
        )
        return joined_in, joined_out

    # ===================== 入库 =====================

    def _save_problem(self, data):
        """写入 Problem 表 + 关联标签(进程内标签缓存)"""
        difficulty_num = data.get('difficulty', 0)
        difficulty_str = DIFFICULTY_MAP.get(difficulty_num, '入门')

        # 若 Problem 模型显式声明了 DIFFICULTY_CHOICES, 做一次校验回退
        try:
            valid = [c[0] for c in Problem.DIFFICULTY_CHOICES]
            if difficulty_str not in valid:
                difficulty_str = '入门'
        except AttributeError:
            pass

        defaults = {
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'input_desc': data.get('input_format', ''),
            'output_desc': data.get('output_format', ''),
            'sample_input': data.get('sample_input', ''),
            'sample_output': data.get('sample_output', ''),
            'hint': data.get('hint', ''),
            'difficulty': difficulty_str,
            'time_limit': data.get('time_limit', 1000),
            'memory_limit': data.get('memory_limit', 256),
            'submit_count': 0,
            'ac_count': 0,
            'is_published': True,
        }
        if self._default_user is not None:
            defaults['created_by'] = self._default_user

        # source 同时承担"来源标识 + 唯一键"两个角色
        problem, _ = Problem.objects.update_or_create(
            source=f'{SOURCE_PREFIX}{data["pid"]}',
            defaults=defaults,
        )

        for name in data.get('tags', []):
            if not name:
                continue
            tag = self._tag_cache.get(name)
            if tag is None:
                tag, _ = Tag.objects.get_or_create(name=name)
                self._tag_cache[name] = tag
            problem.tags.add(tag)

        # 把爬到的样例直接存为测试点（可靠，直接来源于题目页面）
        for i, s in enumerate(data.get('raw_samples', [])):
            if not (isinstance(s, (list, tuple)) and len(s) >= 2):
                continue
            inp, out = str(s[0]).strip(), str(s[1]).strip()
            if inp and out:
                TestCase.objects.update_or_create(
                    problem=problem,
                    sort_order=i,
                    defaults={'input_data': inp, 'expected_output': out, 'is_sample': True},
                )

        return problem

    # ===================== LLM 测试点生成 =====================

    def _generate_test_cases(self, problem, raw_samples, tests_count, pid):
        """
        让 LLM 写一个 Python 参考解 + 若干测试输入，
        本地执行参考解得到输出，先用样例验证正确性，
        通过后保存为 TestCase（is_sample=False）。
        参考洛谷点赞最高的题解作为算法提示。
        """
        from django.conf import settings as _cfg

        key = getattr(_cfg, 'LLM_API_KEY', '').strip()
        url = getattr(_cfg, 'LLM_API_URL', '').strip()
        model = getattr(_cfg, 'LLM_MODEL', '').strip()
        if not key or not url:
            self._warn('    跳过测试点生成：未配置 LLM_API_KEY / LLM_API_URL')
            return 0

        # ── 计算需要 LLM 生成的数量（目标总数 - 已有样例，至少 2 个）──
        sample_count = sum(
            1 for s in raw_samples
            if isinstance(s, (list, tuple)) and len(s) >= 2
            and str(s[0]).strip() and str(s[1]).strip()
        )
        ai_count = max(tests_count - sample_count, 2)
        self._info(f'    已有样例 {sample_count} 个，将生成 {ai_count} 个（目标总数 {max(tests_count, sample_count + 2)}）')

        # ── 爬取洛谷题解列表（最多 5 条，按点赞降序）──────────
        editorials = self._fetch_editorials(pid)
        # 末尾追加一个空字符串，作为「无题解」的兜底轮次
        if not editorials:
            editorials = ['']
            self._info('    未获取到题解，仅凭题面生成')
        else:
            self._info(f'    获取到 {len(editorials)} 条洛谷题解')
            editorials.append('')  # 所有题解都失败后再无题解兜底一次

        # ── 临时文件 ──────────────────────────────────────────
        tmp_dir = tempfile.mkdtemp(prefix='judge_gen_')
        sol_file = os.path.join(tmp_dir, 'solution.py')

        def _normalize(s):
            return '\n'.join(
                line.rstrip()
                for line in s.replace('\r\n', '\n').replace('\r', '\n').rstrip().split('\n')
            )

        def _run(inp_str):
            try:
                proc = subprocess.run(
                    [sys.executable, sol_file],
                    input=inp_str, capture_output=True, text=True, timeout=5,
                )
                return proc.stdout if proc.returncode == 0 else None
            except subprocess.TimeoutExpired:
                return None
            except Exception:
                return None

        valid_samples = [
            s for s in raw_samples
            if isinstance(s, (list, tuple)) and len(s) >= 2
            and str(s[0]).strip() and str(s[1]).strip()
        ]

        def _validate_solution():
            for s in valid_samples:
                sin, sout = str(s[0]).strip(), str(s[1]).strip()
                actual = _run(sin)
                if actual is None or _normalize(actual) != _normalize(sout):
                    return False, (sin, sout, actual or '(崩溃或超时)')
            return True, None

        def _llm_call(messages, max_tokens=3000):
            r = requests.post(
                url,
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                json={'model': model, 'messages': messages,
                      'max_tokens': max_tokens, 'temperature': 0.1},
                timeout=90,
            )
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content'].strip()

        solution_code = None
        gen_inputs = None
        passed = False

        # ── 按题解轮流尝试，每条题解内允许修正 2 次 ─────────────
        for ed_idx, editorial in enumerate(editorials):
            label = f'第{ed_idx + 1}条题解' if editorial else '无题解兜底'
            self._info(f'    尝试 {label}...')

            # 生成参考解 + 测试输入
            try:
                content = _llm_call([
                    {'role': 'user', 'content': self._build_gen_prompt(problem, ai_count, editorial)}
                ])
            except Exception as e:
                self._warn(f'    LLM 调用失败: {e}')
                continue

            sol_match = (
                re.search(r'SOLUTION[^\n]*\n+```(?:python)?\n(.*?)```', content, re.DOTALL | re.IGNORECASE)
                or re.search(r'```(?:python)?\n(.*?)```', content, re.DOTALL)
            )
            if not sol_match:
                self._warn('    未提取到参考解，换下一条题解')
                continue
            solution_code = sol_match.group(1).strip()

            inp_match = (
                re.search(r'INPUTS[^\n]*\n+```(?:json)?\n(.*?)```', content, re.DOTALL | re.IGNORECASE)
                or re.search(r'(\[.*\])', content, re.DOTALL)
            )
            if not inp_match:
                self._warn('    未提取到测试输入，换下一条题解')
                continue
            try:
                gen_inputs = json.loads(self._repair_json(inp_match.group(1)))
                if not isinstance(gen_inputs, list):
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                self._warn(f'    JSON 解析失败，换下一条题解')
                continue

            with open(sol_file, 'w', encoding='utf-8') as f:
                f.write(solution_code)

            # 验证，失败时原地修正最多 2 次
            passed, fail_info = _validate_solution()
            for fix_round in range(2):
                if passed:
                    break
                sin, sout, actual_out = fail_info
                self._warn(
                    f'    验证失败（修正第{fix_round + 1}次）'
                    f' 实际={repr(actual_out[:60])} 期望={repr(sout[:60])}'
                )
                fix_prompt = (
                    f"你的 Python 解输出错误，请修正。\n\n"
                    f"题目：{problem.title}\n"
                    f"输入：\n{sin}\n期望输出：\n{sout}\n实际输出：\n{actual_out}\n\n"
                    f"原代码：\n```python\n{solution_code}\n```\n\n"
                    f"只返回修正后完整 Python 代码：\n```python\n(代码)\n```"
                )
                try:
                    fix_content = _llm_call(
                        [{'role': 'user', 'content': fix_prompt}], max_tokens=2000
                    )
                    fix_match = re.search(r'```(?:python)?\n(.*?)```', fix_content, re.DOTALL)
                    if fix_match:
                        solution_code = fix_match.group(1).strip()
                        with open(sol_file, 'w', encoding='utf-8') as f:
                            f.write(solution_code)
                except Exception as e:
                    self._warn(f'    修正调用失败: {e}')
                    break
                passed, fail_info = _validate_solution()

            if passed:
                break
            self._warn(f'    {label} 修正后仍不通过，换下一条题解')

        if not passed:
            self._warn('    所有题解均尝试失败，放弃生成')
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return 0
        if valid_samples:
            self._info(f'    参考解验证通过（{len(valid_samples)} 个样例）')

        # ── 逐组执行，保存结果 ────────────────────────────────
        # 续排在所有已有测试点之后，避免覆盖已有数据
        from django.db.models import Max
        existing_max = TestCase.objects.filter(problem=problem).aggregate(m=Max('sort_order'))['m']
        start_order = (existing_max + 1) if existing_max is not None else len(raw_samples)
        saved = 0
        for i, raw_inp in enumerate(gen_inputs):
            inp = str(raw_inp).replace('\\n', '\n').strip()
            if not inp:
                continue
            out = _run(inp)
            if out is None:
                self._warn(f'    第 {i + 1} 组运行失败，跳过')
                continue
            out = _normalize(out)
            if not out:
                continue
            TestCase.objects.update_or_create(
                problem=problem,
                sort_order=start_order + i,
                defaults={'input_data': inp, 'expected_output': out, 'is_sample': False},
            )
            saved += 1

        shutil.rmtree(tmp_dir, ignore_errors=True)
        return saved

    def _build_gen_prompt(self, problem, tests_count, editorial=''):
        hint = (problem.hint or '')[:600]
        editorial_section = (
            f"\n参考题解（来自洛谷社区，仅供理解算法思路）：\n{editorial[:1500]}\n"
            if editorial else ''
        )
        return (
            f"你是算法竞赛出题人，需要为以下题目完成两件事：\n"
            f"1. 写一个正确的 Python 3 参考解（从 stdin 读取，向 stdout 输出）\n"
            f"2. 生成 {tests_count} 组仅含输入的测试数据（不需要输出，程序执行后自动得到）\n\n"
            f"题目：{problem.title}\n"
            f"描述：{problem.description[:600]}\n"
            f"输入格式：{problem.input_desc[:400]}\n"
            f"输出格式：{problem.output_desc[:400]}\n"
            f"提示/数据范围：{hint}\n"
            f"样例输入：\n{problem.sample_input[:300]}\n"
            f"样例输出：\n{problem.sample_output[:300]}\n"
            f"{editorial_section}\n"
            f"请严格按以下格式输出，不要多余文字：\n\n"
            f"SOLUTION:\n"
            f"```python\n"
            f"（完整的 Python 3 代码）\n"
            f"```\n\n"
            f"INPUTS:\n"
            f"```json\n"
            f'["第1组输入（多行用\\n分隔）", "第2组输入", ...]\n'
            f"```\n\n"
            f"要求：\n"
            f"- 参考解必须能正确通过所有样例\n"
            f"- 测试数据必须包含边界值：n=1、n 取最大约束、全相同元素、极值等\n"
            f"- inputs 中每组是纯字符串，多行之间用 \\n 分隔\n"
            f"- 只输出上面格式，不要任何其他内容"
        )

    @staticmethod
    def _repair_json(text):
        """修复 LLM 常见错误：JSON 字符串内含裸换行/回车，转义后再解析。"""
        result = []
        in_string = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '\\' and in_string and i + 1 < len(text):
                result.append(ch)
                result.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = not in_string
            elif in_string and ch == '\n':
                ch = '\\n'
            elif in_string and ch == '\r':
                i += 1
                continue
            result.append(ch)
            i += 1
        return ''.join(result)

    def _fetch_editorials(self, pid):
        """爬取洛谷题解列表，按点赞数降序返回每条题解内容的列表（最多取 5 条）。"""
        url = f'https://www.luogu.com.cn/problem/solution/{pid}'
        try:
            resp = self._request_with_retry(self._session, url, timeout=15)
            if resp is None or resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        solutions = []
        for key in ('currentData', 'data'):
            obj = data.get(key)
            if isinstance(obj, dict):
                sol_obj = obj.get('solutions', {})
                if isinstance(sol_obj, dict):
                    solutions = sol_obj.get('result', [])
                    if solutions:
                        break

        if not solutions:
            return []

        top = sorted(solutions, key=lambda s: s.get('voteCount', 0), reverse=True)[:5]
        return [
            (sol.get('content') or '').strip()[:1200]
            for sol in top
            if (sol.get('content') or '').strip()
        ]

    # ===================== 网络重试 =====================

    def _request_with_retry(self, session, url, **kwargs):
        """指数退避: 429 / 5xx / 网络异常自动重试 MAX_RETRIES 次"""
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = session.get(url, **kwargs)
                if resp.status_code == 429:
                    wait = (RETRY_BACKOFF_BASE ** attempt) + random.uniform(2, 5)
                    self._warn(
                        f'    429 限流, 第 {attempt + 1} 次重试, 等待 {wait:.1f}s'
                    )
                    time.sleep(wait)
                    continue
                if 500 <= resp.status_code < 600:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    self._warn(
                        f'    {resp.status_code} 服务端错误, '
                        f'第 {attempt + 1} 次重试, 等待 {wait:.1f}s'
                    )
                    time.sleep(wait)
                    continue
                return resp
            except requests.RequestException as e:
                last_err = e
                wait = RETRY_BACKOFF_BASE ** attempt
                self._warn(
                    f'    网络异常 ({e}), 第 {attempt + 1} 次重试, 等待 {wait:.1f}s'
                )
                time.sleep(wait)
        if last_err:
            raise last_err
        return None

    # ===================== 日志 / 进度 =====================

    def _resolve_default_user(self):
        """为 created_by 选一个默认用户(优先 superuser, 退化到第一个用户)"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = (User.objects.filter(is_superuser=True).first()
                    or User.objects.first())
        except Exception as e:
            self._warn(f'  解析默认用户失败: {e}')
            return None

        if user is None:
            self._warn(
                '  ⚠ 数据库中没有任何用户, created_by 将留空。\n'
                '    若 Problem.created_by 为 NOT NULL 会写入失败,\n'
                '    请先执行: python manage.py createsuperuser'
            )
        else:
            self._info(f'  使用 {user.username} 作为 created_by')
        return user

    def _setup_logger(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f'crawl_luogu_{datetime.now():%Y%m%d_%H%M%S}.log'
        logger = logging.getLogger(f'crawl_luogu.{id(self)}')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.propagate = False
        fmt = logging.Formatter(
            '[%(asctime)s] %(levelname)-7s %(message)s', '%H:%M:%S'
        )
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        self.logger = logger
        self.log_file = log_file

    def _load_progress(self):
        if not PROGRESS_FILE.exists():
            return {}
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_progress(self, data):
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._warn(f'保存进度失败: {e}')

    # ---- 双通道日志: 终端着色 + 文件持久化 ----
    def _info(self, msg):
        self.stdout.write(msg)
        self.logger.info(msg.strip())

    def _success(self, msg):
        self.stdout.write(self.style.SUCCESS(msg))
        self.logger.info(msg.strip())

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(msg))
        self.logger.warning(msg.strip())

    def _error(self, msg):
        self.stdout.write(self.style.ERROR(msg))
        self.logger.error(msg.strip())

    def _banner(self, target, start_page, force_update, min_diff, max_diff):
        msg = (
            f'\n{"=" * 50}\n'
            f'  洛谷题目爬虫 (重构版)\n'
            f'  目标: {target} 道  |  起始页: {start_page}\n'
            f'  难度范围: {min_diff} ({DIFFICULTY_MAP.get(min_diff)}) '
            f'~ {max_diff} ({DIFFICULTY_MAP.get(max_diff)})\n'
            f'  强制更新: {"是" if force_update else "否"}\n'
            f'  日志文件: {self.log_file}\n'
            f'{"=" * 50}\n'
        )
        self.stdout.write(self.style.WARNING(msg))
        self.logger.info(msg.strip())

    def _summary(self, success, skip, fail, elapsed, rate, failed_pids):
        msg = (
            f'\n{"=" * 50}\n'
            f'  爬取完成!\n'
            f'  新增/更新: {success} 道\n'
            f'  跳过: {skip} 道(已存在)\n'
            f'  失败: {fail} 道\n'
            f'  耗时: {elapsed:.1f}s   平均速率: {rate:.2f} 题/秒\n'
            f'  数据库总计: {Problem.objects.count()} 道题目\n'
        )
        if failed_pids:
            preview = ', '.join(failed_pids[:10])
            if len(failed_pids) > 10:
                preview += f' ...(共 {len(failed_pids)} 个)'
            msg += (
                f'  失败 PID 已写入进度文件, 可用 --retry-failed 重试:\n'
                f'  {preview}\n'
            )
        msg += f'{"=" * 50}\n'
        self.stdout.write(self.style.SUCCESS(msg))
        self.logger.info(msg.strip())
