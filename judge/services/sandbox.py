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
  --cap-drop=ALL        drop every Linux capability
  --security-opt no-new-privileges  block setuid privilege escalation
  --read-only           root filesystem read-only (writes go to bind mount / tmpfs only)
  --ulimit nofile       cap file descriptors
  --user nobody         run untrusted code as non-root (JUDGE_SANDBOX_RUN_USER)
  --tmpfs /tmp          writable scratch space inside container (no host writes)
  -v tmp_dir:/sandbox:ro  source/binary mounted read-only at run time

输出上限：
  选手程序若疯狂打印（如 while(1) printf），Docker 的内存限制只管容器内，
  主机侧读取管道会把全部 stdout 缓冲进内存，几秒就能把评测机 OOM。
  这里在读取时对 stdout 设硬上限，超限立即 kill 子进程并判 OLE（Output Limit
  Exceeded）；stderr 也截断，避免异常信息撑爆内存。
"""
import os
import subprocess
import sys
import threading
import uuid

from django.conf import settings

_USE_DOCKER: bool = getattr(settings, 'USE_DOCKER_SANDBOX', False)
_DOCKER_IMAGE: str = getattr(settings, 'JUDGE_DOCKER_IMAGE', 'acm-oj-sandbox:latest')

# 输出硬上限（字符数，UTF-8 下约等于字节数）。默认 64 MB，可用 JUDGE_OUTPUT_LIMIT_KB 覆盖。
_OUTPUT_LIMIT: int = int(getattr(settings, 'JUDGE_OUTPUT_LIMIT_KB', 65536)) * 1024
# stderr 单独截断（错误信息无需很大）。
_STDERR_LIMIT: int = 64 * 1024

# Docker 沙箱加固参数
_SANDBOX_RUN_USER: str = str(getattr(settings, 'JUDGE_SANDBOX_RUN_USER', 'nobody')).strip()
_SANDBOX_NOFILE: int = int(getattr(settings, 'JUDGE_SANDBOX_NOFILE', 1024))

# 解释器 / 虚拟机的启动耗时不该算进选手的算法时间，按语言给少量宽限。
# 时间限制在容器内用 GNU timeout 强制执行（超时退出码 124，与 OOM 的 137 不冲突），
# 这样死循环在 时间限制+宽限 秒内就被掐掉，而不是拖满外层的兜底超时。
_STARTUP_GRACE = {'C': 0.5, 'C++': 0.5, 'Python': 1.0, 'Java': 2.0}
# 外层兜底超时 = 容器内限制 + 这个值，仅用于覆盖容器启动开销与守护进程异常
_DOCKER_OUTER_BUFFER: float = float(getattr(settings, 'JUDGE_DOCKER_OUTER_BUFFER', 5.0))


def _hardening_flags() -> list:
    """
    与 bind-mount 文件属主无关、可无脑开启的通用加固项：
      --cap-drop=ALL            丢弃所有 Linux capability（代码执行不需要任何 cap）
      --security-opt no-new-privileges  禁止通过 setuid 提权
      --read-only               根文件系统只读（写操作只能落到 bind mount 与 /tmp tmpfs）
      --ulimit nofile           限制文件描述符，防止 fd 耗尽
    """
    return [
        '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges',
        '--read-only',
        '--ulimit', f'nofile={_SANDBOX_NOFILE}:{_SANDBOX_NOFILE}',
    ]


def _grant_sandbox_read(tmp_dir: str) -> None:
    """
    以非 root 用户执行时，让只读挂载的沙箱目录可被该用户读取/进入。
    目录由主机进程创建（属主是自己），可 chmod 0755；
    源码文件补 o+r（应对主机 umask 077 的情况）；
    编译产物可能属 root（编译容器以 root 写入），chmod 会 EPERM——它默认已是
    world-readable，忽略即可。整体 best-effort，任何失败都不影响评测。
    """
    try:
        os.chmod(tmp_dir, 0o755)
        for name in os.listdir(tmp_dir):
            p = os.path.join(tmp_dir, name)
            try:
                os.chmod(p, os.stat(p).st_mode | 0o044)
            except OSError:
                pass
    except OSError:
        pass

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
    Returns (returncode: int, stdout: str, stderr: str, timed_out: bool, output_exceeded: bool).

    output_exceeded=True 表示 stdout 超过硬上限，已被强制终止（判 OLE）。
    Docker mode: exit code 137 means OOM-killed (MLE).
    Direct mode: memory is NOT enforced — dev only.
    """
    if _USE_DOCKER:
        return _docker_run(lang, tmp_dir, input_data, timeout_sec, memory_mb)
    return _direct_run(lang, tmp_dir, input_data, timeout_sec)


def _capped_communicate(proc, input_data: str, timeout_sec: float,
                        stdout_cap: int, stderr_cap: int) -> tuple:
    """
    在读取线程里排空子进程输出，stdout/stderr 各设硬上限。
    stdout 超限：立即 kill 子进程并标记 output_exceeded。
    stderr 超限：仅停止收集但继续排空，避免子进程写阻塞。
    返回 (returncode, stdout, stderr, timed_out, output_exceeded)。
    """
    collected = {'out': [], 'err': []}
    exceeded = {'flag': False}

    def _feed_stdin():
        try:
            if input_data:
                proc.stdin.write(input_data)
            proc.stdin.close()
        except Exception:
            pass

    def _read(stream, key: str, cap: int, kill_on_over: bool):
        total = 0
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                if total < cap:
                    collected[key].append(chunk[:cap - total])
                total += len(chunk)
                if total > cap and kill_on_over:
                    exceeded['flag'] = True
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
        except Exception:
            pass

    workers = [
        threading.Thread(target=_feed_stdin, daemon=True),
        threading.Thread(target=_read, args=(proc.stdout, 'out', stdout_cap, True), daemon=True),
        threading.Thread(target=_read, args=(proc.stderr, 'err', stderr_cap, False), daemon=True),
    ]
    for w in workers:
        w.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    for w in workers:
        w.join(timeout=2)

    return (
        proc.returncode,
        ''.join(collected['out']),
        ''.join(collected['err']),
        timed_out,
        exceeded['flag'],
    )


# ─── Docker backend ────────────────────────────────────────────────────────


def _docker_force_remove(name: str) -> None:
    """
    强制删除可能仍在后台运行的容器。

    必须有这一步：`docker run` 只是守护进程的客户端，杀掉它**不会**停止容器，
    而 `--rm` 只在容器自行退出后才清理。TLE / 输出超限时我们杀的正是这个客户端，
    若不显式清理，死循环容器会永久占着 CPU —— 比赛中几十发超时就能拖垮评测机。
    """
    try:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=15)
    except Exception:
        pass


def _docker_compile(lang: str, tmp_dir: str) -> tuple:
    container = f'acm-compile-{uuid.uuid4().hex[:16]}'
    try:
        proc = subprocess.run(
            [
                'docker', 'run', '--rm', '--name', container,
                '--network=none',
                '--memory=512m', '--memory-swap=512m',
                '--cpus=2',
                '--pids-limit=64',
                *_hardening_flags(),
                # 只读根文件系统下，编译器的临时文件需要可写的 /tmp
                '--tmpfs', '/tmp:exec,size=256m',
                # 编译需向 /sandbox 写出产物，故以默认（root）用户运行、挂载可写
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
        _docker_force_remove(container)   # 客户端已超时退出，容器可能还在编译
        return False, '编译超时'
    except FileNotFoundError:
        return False, 'Docker 未找到 — 请确认已安装并设置 USE_DOCKER_SANDBOX=True'


def _docker_run(lang: str, tmp_dir: str, input_data: str,
                timeout_sec: float, memory_mb: int) -> tuple:
    user_flags = []
    if _SANDBOX_RUN_USER:
        # 以非 root 用户执行选手代码；先让只读挂载对该用户可读
        _grant_sandbox_read(tmp_dir)
        user_flags = ['--user', _SANDBOX_RUN_USER]
    container = f'acm-judge-{uuid.uuid4().hex[:16]}'
    # 时间限制交给容器内的 timeout 精确执行；-k 1 表示 TERM 后 1 秒仍不退出则 KILL
    inner_limit = timeout_sec + _STARTUP_GRACE.get(lang, 1.0)
    run_sh = f'timeout -k 1 {inner_limit:.2f} {_RUN_SH[lang]}'
    try:
        proc = subprocess.Popen(
            [
                'docker', 'run', '--rm', '-i', '--name', container,
                '--network=none',
                f'--memory={memory_mb}m', f'--memory-swap={memory_mb}m',
                '--cpus=1',
                '--pids-limit=64',
                *_hardening_flags(),
                *user_flags,
                # exec-capable /tmp for JVM JIT and Python tempfile
                '--tmpfs', '/tmp:exec,size=128m',
                '-v', f'{tmp_dir}:/sandbox:ro',
                _DOCKER_IMAGE,
                'sh', '-c', run_sh,
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding='utf-8', errors='replace',
        )
    except FileNotFoundError:
        return -1, '', 'Docker 未找到', False, False
    # 外层只作兜底：容器内 timeout 已按真实限制掐断，这里覆盖容器启动开销即可
    rc, out, err, outer_timed_out, exceeded = _capped_communicate(
        proc, input_data, inner_limit + _DOCKER_OUTER_BUFFER,
        _OUTPUT_LIMIT, _STDERR_LIMIT,
    )
    # 容器内 timeout 判定超时会返回 124（与 OOM 的 137 不冲突）
    inner_timed_out = (rc == 124)
    # 仅当我们主动杀掉 docker 客户端时，容器才可能仍在后台运行，需要显式清除。
    # 内层 timeout 触发时容器已自行退出，--rm 会清理，无需多花一次 docker rm 的时间。
    if outer_timed_out or exceeded:
        _docker_force_remove(container)
    return rc, out, err, (outer_timed_out or inner_timed_out), exceeded


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
                return -1, '', '找不到编译产物（main.exe / main），请确认 g++ 正常安装', False, False
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
    except Exception as exc:
        return -1, '', str(exc), False, False
    return _capped_communicate(
        proc, input_data, timeout_sec + startup_buffer, _OUTPUT_LIMIT, _STDERR_LIMIT,
    )
