"""
星语接口测试：通过 HTTP 访问正在运行的后端，逐项核对状态码与关键返回字段，记录耗时。

用法（后端需已执行 migrate + seed_star）：
    python repro/api_test_star.py --base http://127.0.0.1:8000 --out repro/results

演示账号密码直接读 seed_star.py 里的 DEMO_PASSWORD 常量，不在输出里出现。
会写入测试数据：注册一个新学生、产生作答记录、生成/审核/布置任务；
对话、推荐、报告、大模型改造会真实调用 .env 里配置的大模型。
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / 'star' / 'management' / 'commands' / 'seed_star.py'


def demo_password():
    m = re.search(r"^DEMO_PASSWORD\s*=\s*['\"](.+?)['\"]", SEED.read_text(encoding='utf-8'), re.M)
    if not m:
        sys.exit('seed_star.py 里没有找到 DEMO_PASSWORD')
    return m.group(1)


class Runner:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.rows = []

    def call(self, name, method, path, expect, token=None, body=None, check=None, note=None):
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        t0 = time.perf_counter()
        r = requests.request(method, self.base + path, json=body, headers=headers, timeout=300)
        ms = (time.perf_counter() - t0) * 1000
        try:
            data = r.json()
        except ValueError:
            data = None
        ok = r.status_code == expect
        detail = ''
        if ok and check:
            try:
                res = check(data)
            except Exception as e:          # 检查函数出错也算不通过
                res = f'检查出错：{e!r}'
            if res is True or res is None:
                pass
            elif res is False:
                ok = False
            else:
                ok, detail = (not str(res).startswith('✗')), str(res).lstrip('✗')
        if ok and note:
            detail = note(data) if callable(note) else note
        if not ok and not detail:
            detail = json.dumps(data, ensure_ascii=False)[:120] if data is not None else r.text[:120]
        self.rows.append({'name': name, 'method': method, 'path': re.sub(r'/\d+/', '/{id}/', path),
                          'expect': expect, 'actual': r.status_code, 'pass': ok,
                          'ms': round(ms, 1), 'detail': detail})
        mark = '通过' if ok else '失败'
        print(f'[{mark}] {name:<24} {method:<6} {r.status_code}/{expect}  {ms:8.1f} ms  {detail}')
        return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8000')
    ap.add_argument('--out', default=str(ROOT / 'repro' / 'results'))
    args = ap.parse_args()
    pw = demo_password()
    t = Runner(args.base)
    started = datetime.now()

    # ── 认证与权限 ──────────────────────────────────────────
    t.call('未登录访问星语', 'GET', '/api/star/me/', 401)
    stu = t.call('学生登录（启蒙层）', 'POST', '/api/auth/login/', 200,
                 body={'username': 'star_hang', 'password': pw}, check=lambda d: bool(d['access']))['access']
    jie = t.call('学生登录（入门层）', 'POST', '/api/auth/login/', 200,
                 body={'username': 'star_jie', 'password': pw}, check=lambda d: bool(d['access']))['access']
    tea = t.call('教师登录', 'POST', '/api/auth/login/', 200,
                 body={'username': 'star_teacher', 'password': pw}, check=lambda d: bool(d['access']))['access']
    t.call('学生访问教师端（越权）', 'GET', '/api/star/teacher/learners/', 403, token=stu)

    # ── 新学生：问卷与引导对话 ────────────────────────────────
    uname = 'apitest_' + started.strftime('%H%M%S')
    new = t.call('注册新学生', 'POST', '/api/auth/register/', 201,
                 body={'username': uname, 'password': 'apitest123', 'password2': 'apitest123'})['access']
    me = t.call('新学生状态', 'GET', '/api/star/me/', 200, token=new,
                check=lambda d: d['status'] == 'new' or f"✗status={d['status']}",
                note=lambda d: f"问卷 {len(d['survey'])} 屏")
    answers = {}
    for q in me['survey']:
        kind = q.get('type', 'single')
        if kind == 'scale':
            answers[q['key']] = {r['key']: q['levels'][0]['value'] for r in q['rows']}
        elif kind == 'multi':
            answers[q['key']] = [q['options'][0]['value']]
        else:
            answers[q['key']] = q['options'][0]['value']
    partial = {k: v for k, v in answers.items() if k != 'typing'}
    t.call('问卷缺项校验', 'POST', '/api/star/survey/', 400, token=new, body={'answers': partial})
    t.call('提交完整问卷', 'POST', '/api/star/survey/', 200, token=new, body={'answers': answers},
           note=lambda d: f"返回界面定制 bg={d['ui']['bg']}，引导对话 {d['dialogue']['total']} 问")
    t.call('重复提交问卷', 'POST', '/api/star/survey/', 409, token=new, body={'answers': answers})
    last = None
    for a in ['高铁', '呜呜', '停停', '再说一遍', '小测']:
        last = requests.post(t.base + '/api/star/dialogue/', json={'answer': a, 'via': 'text'},
                             headers={'Authorization': f'Bearer {new}'}, timeout=120)
    t.rows.append({'name': '引导对话 5 轮', 'method': 'POST', 'path': '/api/star/dialogue/', 'expect': 200,
                   'actual': last.status_code, 'pass': last.status_code == 200 and last.json().get('done') is True,
                   'ms': None, 'detail': f"画像状态 {last.json().get('status')}（待教师确认）"})
    print(f"[{'通过' if t.rows[-1]['pass'] else '失败'}] 引导对话 5 轮  {t.rows[-1]['detail']}")

    # ── 启蒙层：卡片闯关 ──────────────────────────────────────
    tasks = t.call('学生任务列表', 'GET', '/api/star/tasks/', 200, token=stu,
                   note=lambda d: f'{len(d)} 个已审核任务')
    lv = tasks[0]['id']
    c = t.call('任务详情（不含答案）', 'GET', f'/api/star/tasks/{lv}/', 200, token=stu,
               check=lambda d: ("'answer'" not in str(d['content'])) or '✗返回了答案字段')
    jie_tasks = requests.get(t.base + '/api/star/tasks/', headers={'Authorization': f'Bearer {jie}'}).json()
    t.call('访问他人任务', 'GET', f"/api/star/tasks/{jie_tasks[0]['id']}/", 404, token=stu)
    sol = t.call('三级提示（给出解法）', 'POST', f'/api/star/tasks/{lv}/hint/', 200, token=stu,
                 body={'step': 0, 'level': 3}, check=lambda d: bool(d.get('solution')),
                 note=lambda d: f"{len(d['solution'])} 张卡片")['solution']
    t.call('关卡作答（未到终点）', 'POST', f'/api/star/tasks/{lv}/attempt/', 200, token=stu,
           body={'step': 0, 'answer': {'program': sol[:-1]}, 'hint_level': 0},
           check=lambda d: (not d['correct']) or '✗不该判对', note=lambda d: f"result={d['result']}")
    t.call('关卡作答（正确）', 'POST', f'/api/star/tasks/{lv}/attempt/', 200, token=stu,
           body={'step': 0, 'answer': {'program': sol}, 'hint_level': 3, 'duration_ms': 30000},
           check=lambda d: d['correct'] or '✗没判对',
           note=lambda d: f"result={d['result']}，用卡 {d['cards_used']} 张 = 最短 {d['shortest']} 张")
    t.call('作答格式校验', 'POST', f'/api/star/tasks/{lv}/attempt/', 400, token=stu,
           body={'step': 0, 'answer': 'forward'})

    # ── 入门层：选择 / 填空 / 排序 / 写代码 ────────────────────
    jt = jie_tasks[0]['id']
    full = requests.get(f'{t.base}/api/star/teacher/tasks/{jt}/', headers={'Authorization': f'Bearer {tea}'}).json()
    steps = full['content']['steps']
    shown = requests.get(f'{t.base}/api/star/tasks/{jt}/', headers={'Authorization': f'Bearer {jie}'}).json()
    for i, st in enumerate(steps):
        if st['type'] == 'choice':
            t.call(f'第{i+1}步 选择题', 'POST', f'/api/star/tasks/{jt}/attempt/', 200, token=jie,
                   body={'step': i, 'answer': {'choice': st['answer']}, 'hint_level': 0},
                   check=lambda d: d['correct'] or '✗没判对')
        elif st['type'] == 'fill':
            t.call(f'第{i+1}步 填空题', 'POST', f'/api/star/tasks/{jt}/attempt/', 200, token=jie,
                   body={'step': i, 'answer': {'text': st['answer']}, 'hint_level': 0},
                   check=lambda d: d['correct'] or '✗没判对')
        elif st['type'] == 'order':
            lines = shown['content']['steps'][i]['lines']
            order = [lines.index(x) for x in st['lines']]
            t.call(f'第{i+1}步 排序（沙箱运行）', 'POST', f'/api/star/tasks/{jt}/attempt/', 200, token=jie,
                   body={'step': i, 'answer': {'order': order}, 'hint_level': 0},
                   note=lambda d: f"判定 {d.get('status')}，测试点 {d.get('passed')}/{d.get('total')}")
        elif st['type'] == 'code':
            t.call(f'第{i+1}步 写代码（语法错）', 'POST', f'/api/star/tasks/{jt}/attempt/', 200, token=jie,
                   body={'step': i, 'answer': {'code': 'a = int(input()\nprint(a)\n'}},
                   check=lambda d: (not d['correct']) or '✗不该判对', note=lambda d: d.get('error_text', ''))
            t.call(f'第{i+1}步 写代码（沙箱运行）', 'POST', f'/api/star/tasks/{jt}/attempt/', 200, token=jie,
                   body={'step': i, 'answer': {'code': full['reference_code']}, 'hint_level': 0},
                   note=lambda d: f"判定 {'AC' if d['correct'] else d.get('feedback')}")

    # ── 对话助手（大模型 P5 意图 + P3 回复）──────────────────
    t.call('对话：空输入校验', 'POST', '/api/star/chat/', 400, token=stu, body={'text': ' '})
    t.call('对话：求助护栏（不调模型）', 'POST', '/api/star/chat/', 200, token=stu, body={'text': '我害怕'},
           note=lambda d: f"回复「{d.get('reply')}」")
    t.call('对话：代词逆转', 'POST', '/api/star/chat/', 200, token=stu,
           body={'text': '你要提示', 'task_id': lv, 'step': 0},
           note=lambda d: f"回复「{d.get('reply')}」，选项 {len(d.get('options') or [])} 个")
    t.call('对话：自创词', 'POST', '/api/star/chat/', 200, token=stu,
           body={'text': '呜呜在哪里', 'task_id': lv, 'step': 0},
           note=lambda d: f"回复「{d.get('reply')}」")

    # ── 教师端 ────────────────────────────────────────────────
    lst = t.call('学生列表（仅本团队）', 'GET', '/api/star/teacher/learners/', 200, token=tea,
                 note=lambda d: f"{len(d['learners'])} 名学生")
    uid = {x['username']: x['user_id'] for x in lst['learners']}
    t.call('学生详情与画像', 'GET', f"/api/star/teacher/learners/{uid['star_hang']}/", 200, token=tea,
           note=lambda d: f"词表 {len(d['learner']['vocabulary'])} 条")
    t.call('素材库', 'GET', '/api/star/teacher/materials/', 200, token=tea,
           note=lambda d: '，'.join(f'{k} {len(v)} 项' for k, v in d.items() if isinstance(v, list)))
    teams = t.call('按团队布置：团队列表', 'GET', '/api/star/teacher/assign/', 200, token=tea,
                   note=lambda d: f"{len(d['teams'])} 个团队")
    draft = t.call('生成任务（默认版本→草稿）', 'POST', f"/api/star/teacher/learners/{uid['star_jie']}/tasks/", 201,
                   token=tea, body={'material': 'abs_value', 'mode': 'template'},
                   check=lambda d: d['status'] == 'draft' or f"✗status={d['status']}",
                   note=lambda d: f"状态 {d['status']}，校验 rules_ok={d['check']['rules_ok']}")
    t.call('审核通过并锁定', 'POST', f"/api/star/teacher/tasks/{draft['id']}/approve/", 200, token=tea,
           check=lambda d: d['status'] == 'approved' or f"✗status={d['status']}")
    t.call('锁定后不可改文字', 'PATCH', f"/api/star/teacher/tasks/{draft['id']}/", 409, token=tea,
           body={'content': draft['content']})
    t.call('批量布置（重复自动跳过）', 'POST', '/api/star/teacher/assign/', 200, token=tea,
           body={'learners': [uid['star_jie']], 'materials': ['abs_value']},
           note=lambda d: f"新建 {d['created_total']} 个")
    t.call('布置给团队外学生', 'POST', '/api/star/teacher/assign/', 403, token=tea,
           body={'learners': [me_id(t, new)], 'materials': ['L1']})
    t.call('学习报告（P4）', 'POST', f"/api/star/teacher/learners/{uid['star_jie']}/report/", 200, token=tea,
           body={'audience': 'teacher'}, note=lambda d: f"来源 {d['source']}，{len(d['text'])} 字")
    t.call('任务推荐（P6）', 'POST', f"/api/star/teacher/learners/{uid['star_jie']}/recommend/", 200, token=tea,
           note=lambda d: f"来源 {d['source']}，推荐 {len(d['items'])} 项："
                          + '、'.join(x.get('title', x.get('material', '')) for x in d['items']))
    gen = t.call('大模型改造（P2，生成-校验-修复）', 'POST', f"/api/star/teacher/learners/{uid['star_yu']}/tasks/", 201,
                 token=tea, body={'material': 'abs_value', 'mode': 'llm'},
                 note=lambda d: f"状态 {d['status']}，生成 {len(d['validation_log'])} 次，"
                                f"rules_ok={d['check']['rules_ok']}")

    # ── 汇总 ──────────────────────────────────────────────────
    passed = sum(r['pass'] for r in t.rows)
    print(f'\n共 {len(t.rows)} 项，通过 {passed} 项')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"api_test_star-{started.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps({'base': t.base, 'started': started.isoformat(timespec='seconds'),
                             'total': len(t.rows), 'passed': passed, 'rows': t.rows},
                            ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'结果写入 {f}')
    return 0 if passed == len(t.rows) else 1


def me_id(t, token):
    return requests.get(t.base + '/api/auth/me/', headers={'Authorization': f'Bearer {token}'}).json()['id']


if __name__ == '__main__':
    sys.exit(main())
