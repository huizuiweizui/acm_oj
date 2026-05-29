"""
Code execution sandbox.

Two backends:
  USE_DOCKER_SANDBOX=False (default): direct subprocess — Windows dev only, NO isolation.
  USE_DOCKER_SANDBOX=True            : Docker container per run — required for production.

Docker security flags used:
  --network=none        no outbound connections
  --memory / --memory-swap  hard memory cap; OOM-kill exits with code 137
  --cpus=1              single CPU core
  --pids-limit=64       fork-bomb protection
  --tmpfs /tmp          writable scratch space inside container (no host writes)
  -v tmp_dir:/sandbox:ro  source/binary mounted read-only at run time
"""
import os
import subprocess
import sys

from django.conf import settings

_USE_DOCKER: bool = getattr(settings, 'USE_DOCKER_SANDBOX', False)
_DOCKER_IMAGE: str = getattr(settings, 'JUDGE_DOCKER_IMAGE', 'acm-oj-sandbox:latest')

_EXT = {'C': '.c', 'C++': '.cpp', 'Java': '.java', 'Python': '.py'}
_FNAME = {'C': 'main', 'C++': 'main', 'Java': 'Main', 'Python': 'main'}

# Shell commands executed *inside* the Docker container (paths are container paths)
_COMPILE_SH = {
    'C':    'gcc -O2 -o /sandbox/main /sandbox/main.c',
    'C++':  'g++ -O2 -std=c++17 -o /sandbox/main /sandbox/main.cpp',
    'Java': 'javac /sandbox/Main.java',
}
_RUN_SH = {
    'C':      '/sandbox/main',
    'C++':    '/sandbox/main',
    'Java':   'java -cp /sandbox Main',
    'Python': 'python3 /sandbox/main.py',
}


def source_path(lang: str, tmp_dir: str) -> str:
    """Absolute path where judger.py should write the source file."""
    return os.path.join(tmp_dir, _FNAME[lang] + _EXT[lang])


def compile_code(lang: str, tmp_dir: str) -> tuple:
    """
    Compile source file already written to tmp_dir.
    Returns (success: bool, error_text: str).
    Python always returns (True, '').
    """
    if lang == 'Python':
        return True, ''
    if _USE_DOCKER:
        return _docker_compile(lang, tmp_dir)
    return _direct_compile(lang, tmp_dir)


def run_code(lang: str, tmp_dir: str, input_data: str,
             timeout_sec: float, memory_mb: int) -> tuple:
    """
    Run compiled/interpreted code with the given stdin.
    Returns (returncode: int, stdout: str, stderr: str, timed_out: bool).

    Docker mode: exit code 137 means OOM-killed (MLE).
    Direct mode: memory is NOT enforced — dev only.
    """
    if _USE_DOCKER:
        return _docker_run(lang, tmp_dir, input_data, timeout_sec, memory_mb)
    return _direct_run(lang, tmp_dir, input_data, timeout_sec)


# ─── Docker backend ────────────────────────────────────────────────────────


def _docker_compile(lang: str, tmp_dir: str) -> tuple:
    try:
        proc = subprocess.run(
            [
                'docker', 'run', '--rm',
                '--network=none',
                '--memory=512m', '--memory-swap=512m',
                '--cpus=2',
                '--pids-limit=64',
                '-v', f'{tmp_dir}:/sandbox:rw',
                _DOCKER_IMAGE,
                'sh', '-c', _COMPILE_SH[lang],
            ],
            capture_output=True, text=True, timeout=35,
        )
        # gcc/javac writes errors to stderr; some compilers use stdout too
        err_text = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0, err_text
    except subprocess.TimeoutExpired:
        return False, '编译超时'
    except FileNotFoundError:
        return False, 'Docker 未找到 — 请确认已安装并设置 USE_DOCKER_SANDBOX=True'


def _docker_run(lang: str, tmp_dir: str, input_data: str,
                timeout_sec: float, memory_mb: int) -> tuple:
    try:
        proc = subprocess.run(
            [
                'docker', 'run', '--rm', '-i',
                '--network=none',
                f'--memory={memory_mb}m', f'--memory-swap={memory_mb}m',
                '--cpus=1',
                '--pids-limit=64',
                # exec-capable /tmp for JVM JIT and Python tempfile
                '--tmpfs', '/tmp:exec,size=128m',
                '-v', f'{tmp_dir}:/sandbox:ro',
                _DOCKER_IMAGE,
                'sh', '-c', _RUN_SH[lang],
            ],
            input=input_data,
            capture_output=True, text=True,
            # add 10s buffer for container startup; actual TLE enforced by problem.time_limit
            timeout=timeout_sec + 10,
        )
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired:
        return -1, '', 'TLE', True
    except FileNotFoundError:
        return -1, '', 'Docker 未找到', False


# ─── Direct backend (development / Windows only — NO sandboxing) ───────────


def _direct_compile(lang: str, tmp_dir: str) -> tuple:
    src = source_path(lang, tmp_dir)
    out = os.path.join(tmp_dir, 'main')
    # 路径加双引号防止空格问题；Windows 子进程无控制台时 MinGW DLL 可能崩溃，
    # 用 -static-libgcc/-static-libstdc++ 静态链接运行时，消除 DLL 依赖。
    _win = sys.platform == 'win32'
    _static = '-static-libgcc -static-libstdc++' if _win else ''
    _COMPILE_CMD = {
        'C':    f'gcc -O2 {_static} -o "{out}" "{src}"',
        'C++':  f'g++ -O2 -std=c++17 {_static} -o "{out}" "{src}"',
        'Java': f'javac "{src}"',
    }
    cmd = _COMPILE_CMD[lang]
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True,
            encoding='utf-8', errors='replace',
            timeout=30, cwd=tmp_dir,
        )
        err = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0, err[:2000]
    except subprocess.TimeoutExpired:
        return False, '编译超时'


def _direct_run(lang: str, tmp_dir: str, input_data: str, timeout_sec: float) -> tuple:
    _win = sys.platform == 'win32'

    # MinGW 通常自动加 .exe；部分工具链不加，两种都尝试
    if lang in ('C', 'C++'):
        if _win:
            exe = os.path.join(tmp_dir, 'main.exe')
            if not os.path.exists(exe):
                exe = os.path.join(tmp_dir, 'main')
            if not os.path.exists(exe):
                return -1, '', '找不到编译产物（main.exe / main），请确认 g++ 正常安装', False
        else:
            exe = os.path.join(tmp_dir, 'main')
    else:
        exe = ''   # Java/Python 不需要 exe 路径

    _RUN_CMD = {
        'C':      [exe],
        'C++':    [exe],
        'Java':   ['java', '-cp', tmp_dir, 'Main'],
        'Python': [sys.executable, os.path.join(tmp_dir, 'main.py')],
    }
    # Windows 上启动子进程有 200-500ms 系统开销，加缓冲避免误判 TLE。
    startup_buffer = 3.0 if _win else 1.0
    try:
        proc = subprocess.Popen(
            _RUN_CMD[lang],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding='utf-8', errors='replace',
            cwd=tmp_dir,
        )
        try:
            stdout, stderr = proc.communicate(input=input_data, timeout=timeout_sec + startup_buffer)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return -1, '', 'TLE', True
        return proc.returncode, stdout, stderr, False
    except Exception as exc:
        return -1, '', str(exc), False
