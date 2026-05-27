"""
对拍器：自动生成测试点并写入数据库

用法:
  python manage.py gen_testcases --problem-id 1 --gen gen.py --brute brute.py
  python manage.py gen_testcases --problem-id 1 --gen gen.cpp --brute brute.cpp --lang cpp --count 50
  python manage.py gen_testcases --problem-id 1 --gen gen.py --brute brute.py --start-order 10

流程:
  1. 编译暴力解和生成器（若为 C/C++）
  2. 循环 --count 次：
       运行生成器 → 得到输入
       用暴力解运行该输入 → 得到期望输出
       写入 TestCase（is_sample=False）
  3. 汇总结果
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from judge.models import Problem, TestCase
from django.db.models import Max


# ─── 支持的语言与编译命令 ─────────────────────────────────
COMPILE_CMDS = {
    'c':   ['gcc', '-O2', '-std=c11',   '-o', '{out}', '{src}'],
    'cpp': ['g++', '-O2', '-std=c++17', '-o', '{out}', '{src}'],
    'java': ['javac', '{src}'],
}

RUN_CMDS = {
    'c':      ['{bin}'],
    'cpp':    ['{bin}'],
    'java':   ['java', '-cp', '{dir}', '{cls}'],
    'python': [sys.executable, '{src}'],
}


class Command(BaseCommand):
    help = '对拍器：用暴力解 + 随机数据生成器批量生成测试点'

    def add_arguments(self, parser):
        parser.add_argument('--problem-id', type=int, required=True,
                            help='目标题目 ID（数据库主键）')
        parser.add_argument('--gen', required=True,
                            help='随机数据生成器文件路径（从 stdin 读种子，向 stdout 输出测试输入）'
                                 '；也可以不读 stdin，每次运行随机输出即可')
        parser.add_argument('--brute', required=True,
                            help='暴力标程文件路径（从 stdin 读输入，向 stdout 输出答案）')
        parser.add_argument('--lang',
                            choices=['auto', 'c', 'cpp', 'java', 'python'],
                            default='auto',
                            help='语言，auto 根据扩展名判断（默认 auto）')
        parser.add_argument('--count', type=int, default=20,
                            help='要生成的测试点数量（默认 20）')
        parser.add_argument('--timeout', type=float, default=5.0,
                            help='单次运行超时秒数（默认 5）')
        parser.add_argument('--start-order', type=int, default=None,
                            help='sort_order 起始值（默认接续现有最大值+1）')
        parser.add_argument('--seed-start', type=int, default=1,
                            help='传给生成器 stdin 的种子起始值（默认 1）')

    def handle(self, *args, **options):
        pid     = options['problem_id']
        gen_src = Path(options['gen']).resolve()
        brute_src = Path(options['brute']).resolve()
        lang    = options['lang']
        count   = options['count']
        timeout = options['timeout']
        seed_start = options['seed_start']

        # ── 检查题目 ───────────────────────────────────────
        try:
            problem = Problem.objects.get(pk=pid)
        except Problem.DoesNotExist:
            raise CommandError(f'题目 ID={pid} 不存在')

        self.stdout.write(f'\n题目: #{problem.id} {problem.title}')

        # ── 检查文件 ───────────────────────────────────────
        for f in (gen_src, brute_src):
            if not f.is_file():
                raise CommandError(f'文件不存在: {f}')

        gen_lang   = lang if lang != 'auto' else _detect_lang(gen_src)
        brute_lang = lang if lang != 'auto' else _detect_lang(brute_src)

        self.stdout.write(f'生成器: {gen_src}  ({gen_lang})')
        self.stdout.write(f'暴力解: {brute_src}  ({brute_lang})')
        self.stdout.write(f'目标数量: {count}  超时: {timeout}s\n')

        tmp_dir = tempfile.mkdtemp(prefix='gen_tc_')
        try:
            # ── 编译 ────────────────────────────────────────
            gen_runner   = _compile(gen_src,   gen_lang,   tmp_dir, 'gen',   self)
            brute_runner = _compile(brute_src, brute_lang, tmp_dir, 'brute', self)

            # ── sort_order 起点 ─────────────────────────────
            if options['start_order'] is not None:
                start_order = options['start_order']
            else:
                existing_max = TestCase.objects.filter(problem=problem).aggregate(
                    m=Max('sort_order'))['m']
                start_order = (existing_max + 1) if existing_max is not None else 0

            # ── 主循环 ──────────────────────────────────────
            saved = skip = 0
            for i in range(count):
                seed = str(seed_start + i)

                # 1. 运行生成器
                inp = _run(gen_runner, gen_lang, gen_src, tmp_dir,
                           stdin=seed, timeout=timeout)
                if inp is None:
                    self.stdout.write(self.style.WARNING(
                        f'  [{i+1}/{count}] 生成器超时/崩溃，跳过'))
                    skip += 1
                    continue

                # 2. 运行暴力解
                out = _run(brute_runner, brute_lang, brute_src, tmp_dir,
                           stdin=inp, timeout=timeout)
                if out is None:
                    self.stdout.write(self.style.WARNING(
                        f'  [{i+1}/{count}] 暴力解超时/崩溃，跳过'))
                    skip += 1
                    continue

                out = _normalize(out)
                if not out:
                    skip += 1
                    continue

                # 3. 写数据库
                TestCase.objects.update_or_create(
                    problem=problem,
                    sort_order=start_order + i,
                    defaults={
                        'input_data':      inp,
                        'expected_output': out,
                        'is_sample':       False,
                    },
                )
                saved += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  [{i+1}/{count}] ✓ 种子={seed}'))

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        self.stdout.write(self.style.SUCCESS(
            f'\n完成！已保存 {saved} 个测试点，跳过 {skip} 个。'
            f'（sort_order {start_order} ~ {start_order + count - 1}）'))


# ─── 工具函数 ────────────────────────────────────────────

def _detect_lang(path: Path) -> str:
    ext = path.suffix.lower()
    return {'.c': 'c', '.cpp': 'cpp', '.cc': 'cpp',
            '.java': 'java', '.py': 'python'}.get(ext, 'python')


def _compile(src: Path, lang: str, tmp_dir: str, name: str, cmd) -> str | None:
    """编译源文件，返回可执行文件路径（解释型语言返回 None）。"""
    if lang == 'python':
        return None  # 无需编译

    if lang == 'java':
        # javac 只需把 .java 复制到 tmp_dir 并编译
        dst = Path(tmp_dir) / src.name
        shutil.copy(src, dst)
        result = subprocess.run(
            ['javac', str(dst)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise CommandError(f'{name} Java 编译失败:\n{result.stderr}')
        return str(dst)  # 路径供后续定位 .class

    # C / C++
    out_bin = str(Path(tmp_dir) / name)
    compile_cmd = [
        c.replace('{out}', out_bin).replace('{src}', str(src))
        for c in COMPILE_CMDS[lang]
    ]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CommandError(f'{name} 编译失败:\n{result.stderr}')
    cmd.stdout.write(f'  {name} 编译成功 → {out_bin}')
    return out_bin


def _run(runner, lang: str, src: Path, tmp_dir: str,
         stdin: str, timeout: float) -> str | None:
    """运行程序，返回 stdout 字符串；超时/崩溃返回 None。"""
    if lang == 'python':
        cmd = [sys.executable, str(src)]
    elif lang == 'java':
        cls = src.stem  # 类名 = 文件名去掉 .java
        cmd = ['java', '-cp', tmp_dir, cls]
    else:
        cmd = [runner]

    try:
        proc = subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def _normalize(s: str) -> str:
    return '\n'.join(
        line.rstrip()
        for line in s.replace('\r\n', '\n').replace('\r', '\n').rstrip().split('\n')
    )
