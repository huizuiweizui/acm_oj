import logging
import threading
from concurrent.futures import ThreadPoolExecutor

import requests as http_req
from django.conf import settings
from django.db import close_old_connections

from ..models import Problem, Submission

logger = logging.getLogger(__name__)

_LANG_CODE = {'C': 'c', 'C++': 'cpp', 'Java': 'java', 'Python': 'python'}

# AI 反馈池。原实现每条提交都 `threading.Thread(...).start()`，和评测队列修掉的
# 是同一类问题：比赛时上百条提交同时评完，就瞬间起上百个线程，每个都挂着一次
# 30 秒的 LLM 请求、各自占一条数据库连接，MySQL 的 max_connections 很快被打满。
#
# 这里用固定大小的池子接住。反馈是锦上添花的功能，慢一点没关系，绝不该拖垮评测。
_AI_WORKERS: int = int(getattr(settings, 'AI_FEEDBACK_WORKERS', 2))

_executor: ThreadPoolExecutor | None = None
_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=_AI_WORKERS, thread_name_prefix='ai-feedback',
                )
                logger.info('AI 反馈线程池已启动，max_workers=%d', _AI_WORKERS)
    return _executor


def _ai_call(prompt):
    """调用 LLM API，失败返回空字符串。"""
    key = getattr(settings, 'LLM_API_KEY', '').strip()
    url = getattr(settings, 'LLM_API_URL', '').strip()
    model = getattr(settings, 'LLM_MODEL', '').strip()
    if not key or not url:
        return ''
    try:
        r = http_req.post(
            url,
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 600,
                'temperature': 0.3,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception:
        return ''


def _feedback_task(submission_id, problem_id):
    """在池子里跑一次 AI 反馈。异常只记日志——反馈失败不该影响已经判完的结果。"""
    # 池子里的线程是复用的，Django 不会像处理请求那样帮忙收连接，
    # 必须自己在首尾回收，否则每个 worker 会各自攥着一条 MySQL 连接不放。
    close_old_connections()
    try:
        sub = Submission.objects.get(id=submission_id)
        prob = Problem.objects.get(id=problem_id)
        fb = _ai_call(_ai_suggest_prompt(sub, prob))
        if fb:
            Submission.objects.filter(id=submission_id).update(ai_feedback=fb)
    except Exception:
        logger.exception('AI 反馈生成失败 submission_id=%s', submission_id)
    finally:
        close_old_connections()


def _async_ai_feedback(submission_id, problem_id):
    """评测结束后在后台补 AI 反馈，不阻塞 verdict 返回；并发上限见 _AI_WORKERS。"""
    # 没配 LLM 就别白占线程了（判定与 _ai_call 保持一致）
    if not getattr(settings, 'LLM_API_KEY', '').strip() \
            or not getattr(settings, 'LLM_API_URL', '').strip():
        return
    _get_executor().submit(_feedback_task, submission_id, problem_id)


def _ai_verdict_prompt(submission, problem):
    """无测试点时，让 AI 判断代码是否正确。"""
    lc = _LANG_CODE.get(submission.language, 'text')
    return (
        f"你是算法竞赛评测系统。请判断以下代码是否正确解决了题目。\n\n"
        f"题目：{problem.title}\n"
        f"描述：{problem.description[:800]}\n"
        f"输入格式：{problem.input_desc[:300]}\n"
        f"输出格式：{problem.output_desc[:300]}\n"
        f"样例输入：\n{problem.sample_input[:400]}\n"
        f"样例输出：\n{problem.sample_output[:400]}\n\n"
        f"语言：{submission.language}\n"
        f"代码：\n```{lc}\n{submission.code[:3000]}\n```\n\n"
        f"请严格按此格式回答：\n"
        f"第1行：AC 或 WA（仅此二选一，不加其他文字）\n"
        f"第2行起：评测理由（分析代码逻辑、边界处理、与样例一致性，200字以内）"
    )


def _ai_suggest_prompt(submission, problem):
    """有测试点时，让 AI 给出代码改进建议。"""
    lc = _LANG_CODE.get(submission.language, 'text')
    tip = '优化和改进建议' if submission.status == 'AC' else '问题所在和改进方向'
    return (
        f"你是算法竞赛辅助系统。请对以下提交给出简洁分析。\n\n"
        f"题目：{problem.title}\n"
        f"描述：{problem.description[:600]}\n"
        f"语言：{submission.language}\n"
        f"评测结果：{submission.status}\n\n"
        f"代码：\n```{lc}\n{submission.code[:3000]}\n```\n\n"
        f"请给出：\n1. 代码主要思路（1-2句）\n2. {tip}\n\n"
        f"使用中文，200字以内，不要重复题目原文。"
    )
