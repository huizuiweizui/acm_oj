"""
题目改造链（核心）：大模型生成 → 确定性算法校验 → 校验错误回填给大模型修复，最多 3 次；
通过后成为草稿，等教师审核，审核通过才锁定给学生。

    generate(task, mode='llm')      为一条 AdaptedTask 生成内容（mode='template' 时不经大模型）
    check_content(task, content)    按任务的层级与素材校验一份内容（教师手改后也走这里）

校验分工（神经符号结合）：
    JSON 结构            → validators 的 format 检查
    句长 / 步骤数 / 答案唯一 / 代码行来源 → validators 的规则检查
    关卡可解、卡槽数匹配  → maze 的最短路搜索
    参考解正确            → 平台评测机实跑测试数据（runner）
"""
import copy

from django.utils import timezone

from ..content.levels import get_level, themed
from ..content.problems import get_problem
from . import llm, prompts
from .runner import reference_passes
from .validators import Check, check_level, check_steps, reference_lines

MAX_ATTEMPTS = 3
API_ERROR_PREFIX = '接口调用失败：'


class MaterialError(Exception):
    """素材本身有问题（不存在、参考解跑不过测试数据……），与大模型无关，重试也没用。"""


class LLMUnavailable(Exception):
    """
    每一次都是接口调用失败（地址 / key / 模型名不对、网络不通），大模型一次输出都没拿到。
    这时生成的不是"不合格的内容"而是"没有内容"，不应留下一条空的"生成失败"任务，由调用方报错。
    """


def material_of(task):
    """返回 ('level', 模板) 或 ('problem', 题目素材)。"""
    if task.layer == 'enlighten':
        tpl = get_level(task.template)
        if not tpl:
            raise MaterialError(f'关卡模板 {task.template} 不存在')
        return 'level', tpl
    prob = get_problem(task.template)
    if not prob:
        raise MaterialError(f'题目素材 {task.template} 不存在')
    return 'problem', prob


def check_content(task, content):
    kind, material = material_of(task)
    if kind == 'level':
        return check_level(content)
    return check_steps(content, reference_lines(material['code']))


def _ensure_reference_ok(task, material):
    if task.problem is None:
        raise MaterialError('入门层任务缺少对应的题库题目，请先运行 manage.py seed_star')
    if not reference_passes(task.problem, material['code']):
        raise MaterialError('参考解没有通过测试数据，请先修正题目素材')


def _template_content(task, kind, material):
    lp = task.student.star_profile
    if kind == 'level':
        return themed(material, (lp.profile or {}).get('theme_key', ''))
    if not material.get('default_steps'):
        raise MaterialError('这道题没有默认版本，只能用大模型改造')
    return copy.deepcopy(material['default_steps'])


def run_loop(purpose, messages, checker, *, max_attempts=MAX_ATTEMPTS, tag='', task=None, learner=None,
             on_attempt=None):
    """
    生成 → 校验 → 修复的通用循环。返回 (通过校验的 JSON 或 None, 最后一次输出, 每次尝试的记录)。
    on_attempt(第几次, 解析出的 JSON 或 None, Check) 供消融实验取每一次的原始输出。

    修复轮只带"原始请求 + 上一次输出 + 错误清单"，不累积全部历史——
    上下文越长越贵，模型也越容易被早先的错误版本带偏。
    """
    attempts, last = [], None
    msgs = list(messages)
    for attempt in range(1, max_attempts + 1):
        res = llm.chat_json(purpose, msgs, attempt=attempt, tag=tag, task=task, learner=learner)
        if res.data is None:
            reason = f'{API_ERROR_PREFIX}{res.error}' if res.error else '输出不是合法的 JSON 对象'
            chk = Check(format_errors=[reason])
        else:
            chk = checker(res.data)
            last = res.data
        llm.mark(res.log, chk)
        if on_attempt:
            on_attempt(attempt, res.data, chk)
        attempts.append({
            'attempt': attempt, 'ok': chk.ok, 'format_ok': chk.format_ok, 'errors': chk.errors,
            'duration_ms': res.log.duration_ms, 'tokens': res.log.total_tokens, 'log_id': res.log.id,
        })
        if chk.ok:
            return res.data, res.data, attempts
        if res.raw and not res.error:
            msgs = list(messages) + [
                {'role': 'assistant', 'content': res.raw},
                {'role': 'user', 'content': prompts.refine_message(chk.errors)},
            ]
        # 接口错误时原样重发：这种失败与内容无关，回填错误清单没有意义
    return None, last, attempts


def build_messages(task, kind, material):
    lp = task.student.star_profile
    profile_text = prompts.profile_summary(lp.profile)
    if kind == 'level':
        return prompts.p2_level_messages(profile_text, material, (lp.profile or {}).get('theme_key', ''))
    step_size = ((lp.profile or {}).get('presentation') or {}).get('step_size', 'normal')
    return prompts.p2_steps_messages(profile_text, material, material['code'], step_size)


def generate(task, *, mode='llm', max_attempts=MAX_ATTEMPTS, tag=''):
    """
    为 task 生成内容并保存。成功 → draft（待审核）；大模型三次都没通过 → failed，
    最后一次输出留在 content 里，教师可以在审核页手动改好后再提交校验。

    mode='template'：不调用大模型，用模板主题包 / 默认分步任务生成（演示兜底）。
    未配置大模型时 mode='llm' 抛 llm.LLMNotConfigured；每次都是接口调用失败时抛 LLMUnavailable，任务不改动。
    """
    kind, material = material_of(task)
    if kind == 'problem':
        _ensure_reference_ok(task, material)

    run_no = 1 + max((e.get('run', 0) for e in task.validation_log or []), default=0)
    now = timezone.now().isoformat()

    if mode == 'template':
        content = _template_content(task, kind, material)
        chk = check_content(task, content)
        entries = [{'run': run_no, 'mode': 'template', 'attempt': 1, 'ok': chk.ok,
                    'errors': chk.errors, 'at': now}]
        task.content = content
        task.status = 'draft' if chk.ok else 'failed'
    else:
        messages = build_messages(task, kind, material)
        good, last, attempts = run_loop(
            'P2', messages, lambda d: check_content(task, d),
            max_attempts=max_attempts, tag=tag, task=task if task.pk else None, learner=task.student,
        )
        if good is None and last is None and attempts and all(
                any(e.startswith(API_ERROR_PREFIX) for e in a['errors']) for a in attempts):
            raise LLMUnavailable(attempts[-1]['errors'][0][len(API_ERROR_PREFIX):])
        entries = [dict(a, run=run_no, mode='llm', at=now) for a in attempts]
        task.gen_count += len(attempts)
        if good is not None:
            task.content, task.status = good, 'draft'
        else:
            task.content, task.status = (last or task.content or {}), 'failed'

    task.validation_log = (task.validation_log or []) + entries
    task.approved_by, task.approved_at = None, None
    task.save()
    return task
