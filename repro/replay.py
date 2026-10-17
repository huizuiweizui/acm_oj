"""
星语消融实验 · 离线重放复算

不调用任何大模型、不需要 API Key。做法：

  1. 用评测时的源码（--source）启动 Django（临时 SQLite 库）；
  2. 把 star.services.llm.chat_json 换成"录音机"：按调用顺序返回 data/llm_calls.jsonl 里记录的
     模型原始输出、耗时和 token；同时逐条核对源码这次拼出的提示词（messages、温度、尝试序号）
     和录下来的是否完全一致；
  3. 原样执行 star_eval 的四组实验代码（run_adapt / run_levels / run_intent / run_consistency / run_logs）——
     结构校验、规则校验、Dijkstra 最短路可解性、意图比对、仿说 / 词表 / 求助护栏都在本机重新计算；
  4. 一致性实验的余弦相似度用 data/embeddings.json 里缓存的 bge-m3 向量；
  5. 把复算出的 summary.json / rows.csv 与 results/ 里报告的结果逐项比对，写出 compare.md。

用法（在复现包根目录）：
    python replay/replay.py
    python replay/replay.py --source source --data data --reported results --out replay_output
"""
import argparse
import csv
import io
import json
import os
import sys
import tempfile
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = ('adapt', 'levels', 'intent', 'consistency', 'logs')
NAMES = {'adapt': '任务改造质量', 'levels': '关卡可解率', 'intent': '意图理解',
         'consistency': '回答一致性', 'logs': '大模型调用日志汇总'}


def parse_args():
    ap = argparse.ArgumentParser(description='星语消融实验离线重放复算')
    ap.add_argument('--source', default=str(ROOT / 'source'), help='评测时的源码目录（含 manage.py）')
    ap.add_argument('--data', default=str(ROOT / 'data'), help='llm_calls.jsonl 与 embeddings.json 所在目录')
    ap.add_argument('--reported', default=str(ROOT / 'results'), help='报告中的实验结果目录')
    ap.add_argument('--out', default=str(ROOT / 'replay_output'), help='复算结果输出目录')
    return ap.parse_args()


def setup_django(source, db_path):
    sys.path.insert(0, str(source))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'acm_oj.settings'
    os.environ['SECRET_KEY'] = 'offline-replay-only'
    os.environ['DB_ENGINE'] = 'sqlite'
    os.environ['DB_NAME'] = str(db_path)          # 绝对路径，BASE_DIR / 绝对路径 = 绝对路径
    os.environ['DEBUG'] = 'False'
    os.environ['REDIS_URL'] = ''
    os.environ['EMBED_MODEL'] = 'BAAI/bge-m3'      # 让一致性实验走"向量余弦"分支（向量来自缓存）
    for k in ('LLM_API_KEY', 'LLM_API_URL', 'EMBED_API_KEY', 'EMBED_API_URL'):
        os.environ[k] = ''                        # 保证不会真的发出网络请求
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', verbosity=0)


class Player:
    """按 tag 分队列、按 id 顺序回放录下来的调用。"""

    def __init__(self, calls):
        self.queues = defaultdict(deque)
        for c in sorted(calls, key=lambda c: c['id']):
            self.queues[c['tag']].append(c)
        self.played = 0
        self.prompt_mismatch = []

    def chat_json(self, purpose, messages, *, temperature=0.2, max_tokens=2000,
                  attempt=1, tag='', task=None, learner=None):
        from star.models import LLMCallLog
        from star.services.llm import LLMResult, parse_json
        q = self.queues.get(tag)
        if not q:
            raise RuntimeError(f'录音里没有更多 tag={tag} 的调用：源码的调用顺序与评测时不一致')
        rec = q.popleft()
        req = rec['request']
        same = (rec['purpose'] == purpose and rec['attempt'] == attempt
                and req.get('messages') == messages and req.get('temperature') == temperature
                and req.get('max_tokens') == max_tokens)
        if not same:
            self.prompt_mismatch.append(rec['id'])
        log = LLMCallLog.objects.create(
            purpose=purpose, request={'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens},
            response=rec['response'], duration_ms=rec['duration_ms'], prompt_tokens=rec['prompt_tokens'],
            completion_tokens=rec['completion_tokens'], total_tokens=rec['total_tokens'],
            attempt=attempt, error=rec['error'], tag=tag, task=task, learner=learner,
        )
        self.played += 1
        raw = rec['response']
        return LLMResult(data=parse_json(raw) if raw else None, raw=raw, log=log, error=rec['error'])


def insert_untouched(calls):
    """非实验调用（演示数据预生成 pregen）原样写进库，日志汇总要把它们算进去。"""
    from star.models import LLMCallLog
    for c in calls:
        LLMCallLog.objects.create(
            purpose=c['purpose'], request=c['request'], response=c['response'], duration_ms=c['duration_ms'],
            prompt_tokens=c['prompt_tokens'], completion_tokens=c['completion_tokens'],
            total_tokens=c['total_tokens'], passed=c['passed'], checks=c['checks'] or {},
            attempt=c['attempt'], error=c['error'], tag=c['tag'],
        )


def cell(v):
    """与 star_eval._write 写 CSV 时的取值方式一致，便于逐格比对。"""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return '' if v is None else str(v)


def read_reported(reported, name):
    dirs = sorted(p for p in Path(reported).glob(f'{name}-*') if p.is_dir())
    if not dirs:
        return None, None, None
    d = dirs[-1]
    summary = json.loads((d / 'summary.json').read_text(encoding='utf-8'))
    rows = None
    if (d / 'rows.csv').exists():
        with open(d / 'rows.csv', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
    return d, summary, rows


def flatten(obj, prefix=''):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f'{prefix}{k}' if not prefix else f'{prefix} / {k}'))
    else:
        out[prefix] = obj
    return out


def write_result(out, name, rows, summary):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(d / 'rows.csv', 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow({k: cell(v) for k, v in r.items()})
    (d / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')


# 一致性实验的相似度来自 Embedding 服务。缓存向量是评测后重新向服务取的，服务端不保证逐位一致，
# 相似度会有万分之几的浮动。只有这几项按容差比对：逐行 0.001，汇总（两位小数）0.01；其余一律要求完全相同。
ROW_TOL = {('consistency', 'mean_similarity'): 0.001}
SUMMARY_TOL_PREFIX = {'consistency': ('平均两两相似度',)}
SUMMARY_TOL = 0.01


def _near(a, b, tol):
    try:
        return abs(float(a) - float(b)) <= tol + 1e-12
    except (TypeError, ValueError):
        return False


def compare(name, summary, rows, rep_summary, rep_rows):
    """返回 (指标比对表, 不一致的格子, 容差内的格子, 比对的格子总数)。表中一致性记 '✓' / '≈' / '✗'。"""
    got, want = flatten(summary), flatten(rep_summary or {})
    table = []
    for k in list(dict.fromkeys(list(want) + list(got))):
        w, g = want.get(k, '（缺）'), got.get(k, '（缺）')
        if w == g:
            mark = '✓'
        elif k.startswith(SUMMARY_TOL_PREFIX.get(name, ())) and _near(w, g, SUMMARY_TOL):
            mark = '≈'
        else:
            mark = '✗'
        table.append((k, w, g, mark))
    diff_cells, near_cells, total_cells = [], [], 0
    if rep_rows is not None and rows is not None:
        if len(rep_rows) != len(rows):
            diff_cells.append(f'行数不同：报告 {len(rep_rows)}，复算 {len(rows)}')
        for i, (a, b) in enumerate(zip(rep_rows, rows), 1):
            for k, v in a.items():
                total_cells += 1
                g = cell(b.get(k))
                if g == v:
                    continue
                line = f'第 {i} 行 {k}：报告 {v[:40]!r}，复算 {g[:40]!r}'
                tol = ROW_TOL.get((name, k))
                (near_cells if tol is not None and _near(v, g, tol) else diff_cells).append(line)
    return table, diff_cells, near_cells, total_cells


def main():
    args = parse_args()
    source, data, out = Path(args.source).resolve(), Path(args.data).resolve(), Path(args.out).resolve()
    calls = [json.loads(line) for line in open(data / 'llm_calls.jsonl', encoding='utf-8') if line.strip()]
    vectors = json.loads((data / 'embeddings.json').read_text(encoding='utf-8'))['vectors']

    tmp = tempfile.TemporaryDirectory(prefix='star-replay-')
    setup_django(source, Path(tmp.name) / 'replay.sqlite3')

    import judge.services.rag as rag
    import numpy as np
    from star.management.commands import star_eval
    from star.services import llm

    player = Player([c for c in calls if c['tag'].startswith('eval:')])
    llm.chat_json = player.chat_json
    missing = []

    def cached_embed(text):
        if text == '测试':                        # star_eval 用它探测 Embedding 是否可用
            return [1.0]
        v = vectors.get(text)
        if v is None:
            missing.append(text)
        return v
    rag._embed_query = cached_embed

    insert_untouched([c for c in calls if not c['tag'].startswith('eval:')])

    cmd = star_eval.Command(stdout=io.StringIO(), stderr=io.StringIO())
    out.mkdir(parents=True, exist_ok=True)
    report = ['# 离线重放复算结果', '',
              f'- 源码：`{source}`', f'- 回放调用：见下表；录音共 {len(calls)} 条', '']
    all_ok, any_near = True, False
    for name in EXPERIMENTS:
        print(f'== {name} ==', flush=True)
        rows, summary = getattr(cmd, f'run_{name}')(0, False)
        write_result(out, name, rows, summary)
        rep_dir, rep_summary, rep_rows = read_reported(args.reported, name)
        table, diffs, nears, total = compare(name, summary, rows, rep_summary, rep_rows)
        ok = all(t[3] != '✗' for t in table) and not diffs
        exact = ok and all(t[3] == '✓' for t in table) and not nears
        all_ok &= ok
        any_near = any_near or (ok and not exact)
        print(f'   指标 {sum(t[3] != "✗" for t in table)}/{len(table)} 一致；'
              f'逐行 {total - len(diffs)}/{total} 格一致（其中 {len(nears)} 格在容差内）', flush=True)
        status = '　✅ 完全一致' if exact else ('　✅ 一致（相似度在容差内）' if ok else '　❌ 有差异')
        report += [f'## {NAMES[name]}（{name}）{status}', '',
                   f'报告结果：`{rep_dir.relative_to(Path(args.reported).resolve().parent) if rep_dir else "（无）"}`', '',
                   '| 指标 | 报告值 | 复算值 | 一致 |', '|---|---|---|---|']
        report += [f'| {k} | {w} | {g} | {mark} |' for k, w, g, mark in table]
        report += ['', f'逐行比对：{total} 个格子，{len(diffs)} 个不一致，{len(nears)} 个在容差内。', '']
        report += [f'- 不一致：{d}' for d in diffs[:30]]
        report += [f'- 容差内：{d}' for d in nears[:30]]
        report.append('')

    left = {t: len(q) for t, q in player.queues.items() if q}
    report += ['## 回放核对', '',
               f'- 回放的实验调用：{player.played} 次；录音里剩余未用：{sum(left.values())} 次 {left or ""}',
               f'- 提示词与录音不一致的调用：{len(player.prompt_mismatch)} 次'
               + (f'（id：{player.prompt_mismatch[:20]}）' if player.prompt_mismatch else '（全部逐字一致）'),
               f'- 缺少缓存向量的回答：{len(missing)} 条', '']
    all_ok &= not left and not player.prompt_mismatch and not missing
    verdict = ('存在差异，见上文。' if not all_ok else
               '全部指标与报告一致；一致性实验的相似度因 Embedding 向量重取有万分之几的浮动，在容差内。'
               if any_near else '全部指标与报告完全一致。')
    report.append(f'**结论：{verdict}**')
    (out / 'compare.md').write_text('\n'.join(report) + '\n', encoding='utf-8')

    print(f'回放 {player.played} 次调用；提示词不一致 {len(player.prompt_mismatch)} 次；剩余 {sum(left.values())} 次')
    print('结论：' + verdict)
    print(f'详细对照：{out / "compare.md"}')
    from django.db import connections
    connections.close_all()
    tmp.cleanup()
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
