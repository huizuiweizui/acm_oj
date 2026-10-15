"""
任务书第七部分的四组消融实验。每次大模型调用都照常写进 LLMCallLog（tag 以 eval: 开头），
结果另存为 CSV（逐条）+ summary.json（汇总），直接用于测试报告与对比图。

    python manage.py star_eval adapt         任务改造质量：15 道入门题 × 2 个画像，直接生成 / 生成-校验-修复闭环
    python manage.py star_eval levels        关卡可解率：生成 50 个关卡，不校验 / BFS 校验并重新生成
    python manage.py star_eval intent        意图理解：50 条语句，关闭 / 开启沟通特征处理
    python manage.py star_eval consistency   回答一致性：10 个问题 × 5 次，默认温度无缓存 / 低温度 / 低温度加缓存
    python manage.py star_eval logs          汇总全部大模型调用日志（次数、通过率、耗时、token）
    python manage.py star_eval all           依次跑前四组

    --limit N        只跑前 N 个样本（试跑、估算成本）
    --independent    对照组单独生成一遍（默认是配对设计，见下）
    --out DIR        输出目录，默认 star_eval_results/

对照组的取法：默认"配对设计"——闭环第 1 次的输出就是一次直接生成（同一提示词、同一模型、同一温度），
直接拿来当对照组，样本两两配对，还省一半调用；--independent 时对照组单独再调用一次。
"""
import csv
import json
import statistics
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg, Count, Q, Sum

from star.content import eval_cases
from star.content.learners import LEARNERS
from star.content.levels import LEVELS, THEMES
from star.content.problems import PROBLEMS
from star.models import LLMCallLog
from star.services import adapt, assistant, llm, maze, prompts
from star.services.validators import avg_sentence_len, check_level, check_steps, reference_lines

EXPERIMENTS = ('adapt', 'levels', 'intent', 'consistency', 'logs')


def _rate(flags):
    flags = list(flags)
    return round(100 * sum(1 for f in flags if f) / len(flags), 1) if flags else None


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 2) if xs else None


def _steps_texts(c):
    if not isinstance(c, dict):
        return []
    texts = [c.get('title') or ''] + list(c.get('intro') or [])
    for st in c.get('steps') or []:
        if isinstance(st, dict):
            texts.append(st.get('prompt') or '')
            texts.extend(h for h in st.get('hints') or [] if isinstance(h, str))
    return [t for t in texts if isinstance(t, str)]


def _level_metrics(d):
    """一个关卡输出的可解性指标（不依赖它是否通过了全部规则）。"""
    chk = check_level(d) if d is not None else None
    if chk is None or not chk.format_ok:
        return {'format_ok': False, 'solvable': False, 'slots_match': False, 'valid': False}
    try:
        sol = maze.shortest_solution(d)
    except (KeyError, TypeError, ValueError, IndexError):
        sol = None
    return {
        'format_ok': True,
        'solvable': sol is not None,
        'slots_match': sol is not None and len(sol) <= d['slots'] <= len(sol) + 2,
        'valid': chk.ok,
    }


class Command(BaseCommand):
    help = '星语消融实验（需要已配置大模型）'

    def add_arguments(self, parser):
        parser.add_argument('experiment', choices=EXPERIMENTS + ('all',))
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--independent', action='store_true')
        parser.add_argument('--out', default=str(Path(settings.BASE_DIR) / 'star_eval_results'))

    def handle(self, *args, **opts):
        self.out = Path(opts['out'])
        exp = opts['experiment']
        if exp != 'logs' and not llm.is_configured():
            raise CommandError('未配置大模型：请先在 .env 中填写 LLM_API_KEY / LLM_API_URL / LLM_MODEL')
        todo = ('adapt', 'levels', 'intent', 'consistency') if exp == 'all' else (exp,)
        for name in todo:
            self.stdout.write(self.style.MIGRATE_HEADING(f'== {name} =='))
            rows, summary = getattr(self, f'run_{name}')(opts['limit'], opts['independent'])
            self._write(name, rows, summary)

    # ── 输出 ─────────────────────────────────────────────────────────
    def _write(self, name, rows, summary):
        out = self.out / f'{name}-{datetime.now():%Y%m%d-%H%M%S}'
        out.mkdir(parents=True, exist_ok=True)
        if rows:
            fields = list(rows[0].keys())
            with open(out / 'rows.csv', 'w', newline='', encoding='utf-8-sig') as f:     # 带 BOM，Excel 直接打开不乱码
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for r in rows:
                    w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                                for k, v in r.items()})
        (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
        self.stdout.write(self.style.SUCCESS(f'结果已写入 {out}'))

    def _progress(self, i, n, label):
        self.stdout.write(f'  [{i}/{n}] {label}')

    # ── 1. 任务改造质量 ─────────────────────────────────────────────
    def run_adapt(self, limit, independent):
        learners = [s for s in LEARNERS if s['layer'] == 'intro'][:2]
        problems = PROBLEMS[:limit] if limit else PROBLEMS
        rows, total = [], len(problems) * len(learners)
        for prob in problems:
            ref = reference_lines(prob['code'])

            def checker(d, ref=ref):
                return check_steps(d, ref)

            for spec in learners:
                self._progress(len(rows) + 1, total, f'{prob["slug"]} × {spec["username"]}')
                profile = spec['profile']
                messages = prompts.p2_steps_messages(prompts.profile_summary(profile), prob, prob['code'],
                                                     profile['presentation']['step_size'])
                seen = {}
                good, last, attempts = adapt.run_loop(
                    'P2', messages, checker, tag='eval:adapt:loop',
                    on_attempt=lambda a, d, c, seen=seen: seen.__setitem__(a, c))
                direct_chk, direct_ms, direct_tokens = seen[1], attempts[0]['duration_ms'], attempts[0]['tokens']
                if independent:
                    once = {}
                    _, _, d_att = adapt.run_loop('P2', messages, checker, max_attempts=1, tag='eval:adapt:direct',
                                                 on_attempt=lambda a, d, c, once=once: once.__setitem__(a, c))
                    direct_chk, direct_ms, direct_tokens = once[1], d_att[0]['duration_ms'], d_att[0]['tokens']
                final = good if good is not None else last
                rows.append({
                    'problem': prob['slug'], 'knowledge': prob['knowledge'], 'learner': spec['username'],
                    'direct_format_ok': direct_chk.format_ok, 'direct_rules_ok': direct_chk.ok,
                    'direct_ms': direct_ms, 'direct_tokens': direct_tokens,
                    'loop_format_ok': seen[len(attempts)].format_ok, 'loop_rules_ok': good is not None,
                    'loop_attempts': len(attempts),
                    'loop_ms': sum(a['duration_ms'] for a in attempts),
                    'loop_tokens': sum(a['tokens'] for a in attempts),
                    'sentence_len_before': avg_sentence_len([prob['description'], prob['input_desc'], prob['output_desc']]),
                    'sentence_len_after': avg_sentence_len(_steps_texts(final)) if final else None,
                    'direct_errors': ' | '.join(direct_chk.errors)[:600],
                })
        summary = {
            'experiment': '任务改造质量',
            'design': 'independent' if independent else 'paired（对照组取闭环第 1 次输出）',
            'samples': len(rows),
            '直接生成': {
                '格式合格率%': _rate(r['direct_format_ok'] for r in rows),
                '规则通过率%': _rate(r['direct_rules_ok'] for r in rows),
                '平均耗时ms': _mean([r['direct_ms'] for r in rows]),
                '平均token': _mean([r['direct_tokens'] for r in rows]),
            },
            '生成-校验-修复闭环': {
                '格式合格率%': _rate(r['loop_format_ok'] for r in rows),
                '规则通过率%': _rate(r['loop_rules_ok'] for r in rows),
                '平均尝试次数': _mean([r['loop_attempts'] for r in rows]),
                '平均重试次数': _mean([r['loop_attempts'] - 1 for r in rows]),
                '平均耗时ms': _mean([r['loop_ms'] for r in rows]),
                '平均token': _mean([r['loop_tokens'] for r in rows]),
            },
            '平均句长（字）': {
                '改写前（原题）': _mean([r['sentence_len_before'] for r in rows]),
                '改写后': _mean([r['sentence_len_after'] for r in rows]),
            },
        }
        return rows, summary

    # ── 2. 关卡可解率 ────────────────────────────────────────────────
    def run_levels(self, limit, independent):
        n = limit or 50
        theme_keys = list(THEMES)
        rows = []
        for i in range(n):
            tpl = LEVELS[i % len(LEVELS)]
            tk = theme_keys[(i + i // len(LEVELS)) % len(theme_keys)]
            self._progress(i + 1, n, f'{tpl["key"]} × {tk}')
            profile = {'interests': [THEMES[tk]['name']], 'presentation': {'prefer': 'image', 'step_size': 'small'},
                       'communication': {'pronoun_reversal': False, 'echolalia': False, 'notes': ''}}
            messages = prompts.p2_level_messages(prompts.profile_summary(profile), tpl, tk)
            outputs = {}
            good, last, attempts = adapt.run_loop(
                'P2', messages, check_level, tag='eval:levels:loop',
                on_attempt=lambda a, d, c, outputs=outputs: outputs.__setitem__(a, d))
            first = outputs.get(1)
            if independent:
                once = {}
                adapt.run_loop('P2', messages, check_level, max_attempts=1, tag='eval:levels:direct',
                               on_attempt=lambda a, d, c, once=once: once.__setitem__(a, d))
                first = once.get(1)
            d_m = _level_metrics(first)
            l_m = _level_metrics(good if good is not None else last)
            rows.append({
                'i': i + 1, 'template': tpl['key'], 'knowledge': tpl['knowledge'], 'theme': tk,
                **{f'direct_{k}': v for k, v in d_m.items()},
                **{f'loop_{k}': v for k, v in l_m.items()},
                'loop_attempts': len(attempts),
            })
        summary = {
            'experiment': '关卡可解率',
            'design': 'independent' if independent else 'paired（对照组取闭环第 1 次输出）',
            'samples': len(rows),
            '不校验': {
                '可解率%': _rate(r['direct_solvable'] for r in rows),
                '最短解与卡槽数匹配%': _rate(r['direct_slots_match'] for r in rows),
                '全部规则通过%': _rate(r['direct_valid'] for r in rows),
            },
            'BFS校验并重新生成': {
                '可解率%': _rate(r['loop_solvable'] for r in rows),
                '最短解与卡槽数匹配%': _rate(r['loop_slots_match'] for r in rows),
                '全部规则通过%': _rate(r['loop_valid'] for r in rows),
                '平均尝试次数': _mean([r['loop_attempts'] for r in rows]),
            },
        }
        return rows, summary

    # ── 3. 意图理解 ──────────────────────────────────────────────────
    def run_intent(self, limit, independent):
        cases = eval_cases.INTENT_CASES[:limit] if limit else eval_cases.INTENT_CASES
        # 测试用的虚构学习者：代词逆转、仿说、自创词三种沟通特点都有
        profile = {'interests': ['火车', '恐龙'], 'presentation': {'prefer': 'image', 'step_size': 'small'},
                   'communication': {'pronoun_reversal': True, 'echolalia': True, 'notes': ''}}
        profile_text = prompts.profile_summary(profile)
        rows = []
        for i, c in enumerate(cases, 1):
            self._progress(i, len(cases), c['text'])
            last_bot = c.get('last_bot', eval_cases.DEFAULT_LAST_BOT)
            history = [{'role': 'bot', 'text': last_bot}]

            res = llm.chat_json('P3', prompts.p3_plain_messages('', history, c['text']),
                                temperature=0.2, max_tokens=300, tag='eval:intent:off')
            off = (res.data or {}).get('intent')

            echo, pairs, guard = False, [], assistant.needs_teacher(c['text'])
            if guard:
                on = 'help'
            else:
                echo = assistant.is_echolalia(c['text'], last_bot)
                replaced, pairs = assistant.apply_vocabulary(c['text'], eval_cases.EVAL_VOCABULARY)
                msgs = prompts.p3_messages(profile_text, '', history, replaced, pronoun_note=True,
                                           echo_note=echo, replaced=pairs)
                res = llm.chat_json('P3', msgs, temperature=0.2, max_tokens=300, tag='eval:intent:on')
                on = (res.data or {}).get('intent')
            rows.append({
                'category': c['category'], 'text': c['text'], 'last_bot': last_bot, 'label': c['label'],
                'off': off, 'on': on, 'off_ok': off == c['label'], 'on_ok': on == c['label'],
                'echo_detected': echo, 'replaced': pairs, 'guard': guard,
            })
        names = {'echolalia': '仿说', 'pronoun': '代词逆转', 'neologism': '自创词', 'plain': '普通表达'}
        by_cat = {}
        for key, name in names.items():
            sub = [r for r in rows if r['category'] == key]
            if sub:
                by_cat[name] = {'条数': len(sub), '关闭%': _rate(r['off_ok'] for r in sub),
                                '开启%': _rate(r['on_ok'] for r in sub)}
        summary = {
            'experiment': '意图理解',
            'labels_reviewed': eval_cases.REVIEWED,
            'note': '' if eval_cases.REVIEWED else '意图标注尚未经人工核对（content/eval_cases.py 的 REVIEWED=False）',
            'samples': len(rows),
            '各类准确率': by_cat,
            '总体': {'关闭%': _rate(r['off_ok'] for r in rows), '开启%': _rate(r['on_ok'] for r in rows)},
        }
        return rows, summary

    # ── 4. 回答一致性 ────────────────────────────────────────────────
    def _similarity_fn(self):
        """优先用平台的 Embedding（余弦相似度）；没配置或调用失败时退回字符级相似度（difflib）。"""
        from judge.services.rag import _embed_query
        probe = _embed_query('测试') if getattr(settings, 'EMBED_MODEL', '').strip() else None
        if probe is None:
            return 'difflib 字符相似度（未配置 Embedding）', assistant.similarity

        cache = {}

        def vec(t):
            if t not in cache:
                v = _embed_query(t)
                cache[t] = np.array(v, dtype=np.float32) if v is not None else None
            return cache[t]

        def sim(a, b):
            va, vb = vec(a), vec(b)
            if va is None or vb is None:
                return assistant.similarity(a, b)
            return float(va @ vb / ((np.linalg.norm(va) * np.linalg.norm(vb)) + 1e-9))

        return f'Embedding 余弦相似度（{settings.EMBED_MODEL}）', sim

    def run_consistency(self, limit, independent, repeats=5):
        questions = eval_cases.CONSISTENCY_QUESTIONS[:limit] if limit else eval_cases.CONSISTENCY_QUESTIONS
        profile_text = prompts.profile_summary({'interests': ['火车'], 'presentation': {'prefer': 'both'},
                                                'communication': {}})
        method, sim = self._similarity_fn()
        conditions = [('默认温度无缓存', 1.0, False), ('低温度无缓存', 0.2, False), ('低温度加缓存', 0.2, True)]
        rows = []
        for i, q in enumerate(questions, 1):
            self._progress(i, len(questions), q)
            for name, temp, use_cache in conditions:
                answers, cached = [], None
                for _ in range(repeats):
                    if use_cache and cached is not None:
                        answers.append(cached)
                        continue
                    res = llm.chat_json('P3', prompts.p3_messages(profile_text, '', [], q), temperature=temp,
                                        max_tokens=300, tag=f'eval:consistency:{name}')
                    d = res.data or {}
                    ans = f'{d.get("reply", "")} / {"、".join(d.get("options") or [])}'
                    answers.append(ans)
                    cached = ans
                pair_sims = [sim(a, b) for a, b in combinations(answers, 2)]
                rows.append({'question': q, 'condition': name, 'temperature': temp, 'cache': use_cache,
                             'mean_similarity': round(statistics.mean(pair_sims), 4), 'answers': answers})
        summary = {
            'experiment': '回答一致性',
            'similarity': method,
            'samples': len(questions),
            'repeats': repeats,
            '平均两两相似度': {name: _mean([r['mean_similarity'] for r in rows if r['condition'] == name])
                         for name, _, _ in conditions},
        }
        return rows, summary

    # ── 日志汇总 ─────────────────────────────────────────────────────
    def run_logs(self, limit, independent):
        qs = (LLMCallLog.objects.values('purpose', 'tag')
              .annotate(calls=Count('id'),
                        checked=Count('id', filter=Q(passed__isnull=False)),
                        passed=Count('id', filter=Q(passed=True)),
                        errors=Count('id', filter=~Q(error='')),
                        avg_ms=Avg('duration_ms'), avg_tokens=Avg('total_tokens'), tokens=Sum('total_tokens'))
              .order_by('purpose', 'tag'))
        rows = []
        for r in qs:
            rows.append({
                'purpose': r['purpose'], 'tag': r['tag'] or '（正常使用）', 'calls': r['calls'],
                'pass_rate_%': round(100 * r['passed'] / r['checked'], 1) if r['checked'] else None,
                'api_errors': r['errors'], 'avg_ms': round(r['avg_ms'] or 0), 'avg_tokens': round(r['avg_tokens'] or 0),
                'total_tokens': r['tokens'] or 0,
            })
        summary = {
            'experiment': '大模型调用日志汇总',
            'total_calls': sum(r['calls'] for r in rows),
            'total_tokens': sum(r['total_tokens'] for r in rows),
            'by_purpose': {p: sum(r['calls'] for r in rows if r['purpose'] == p) for p in ('P1', 'P2', 'P3', 'P4')},
        }
        return rows, summary
