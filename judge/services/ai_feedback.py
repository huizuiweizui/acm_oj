import threading

import requests as http_req
from django.conf import settings

from ..models import Problem, Submission

_LANG_CODE = {'C': 'c', 'C++': 'cpp', 'Java': 'java', 'Python': 'python'}


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


def _async_ai_feedback(submission_id, problem_id):
    """评测结束后在后台线程填写 AI 反馈，不阻塞 verdict 返回。"""
    def _worker():
        try:
            sub = Submission.objects.get(id=submission_id)
            prob = Problem.objects.get(id=problem_id)
            fb = _ai_call(_ai_suggest_prompt(sub, prob))
            if fb:
                sub.ai_feedback = fb
                sub.save(update_fields=['ai_feedback'])
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


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
