import requests as http_req
from django.conf import settings

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
    """把 AI 反馈丢进 Celery 队列，由 worker 异步生成，不阻塞 verdict 返回。"""
    from ..tasks import ai_feedback_task   # 延迟导入，避免与 tasks.py 循环引用
    ai_feedback_task.delay(submission_id, problem_id)


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
