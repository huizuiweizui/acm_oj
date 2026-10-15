"""
大模型统一调用入口（P1–P4 全部走这里）。

    chat_json(purpose, messages, ...)  →  LLMResult

做四件事：
  1. JSON 输出：请求带 response_format=json_object，返回时容错剥掉 ```json 围栏再解析；
  2. 低温度：默认 0.2。面对坚持同一性的学习者，同样的输入应尽量得到同样的输出；
  3. 超时重试：网络超时 / 5xx / 429 最多重试 2 次。这和"生成-校验-修复"的 attempt
     是两回事——后者由调用方控制，这里的重试对上层透明；
  4. 落日志：输入、输出、耗时、token 写入 LLMCallLog，是测试报告的数据来源。

复用平台已有的 LLM_API_KEY / LLM_API_URL / LLM_MODEL 配置，DeepSeek 等 OpenAI 兼容接口都能接
（LLM_API_URL 填完整的 chat/completions 地址，与 AI 反馈功能一致）。

隐私：调用方负责在拼提示词前把学生的姓名、昵称换成占位符 {name}（见 redact），
模型输出回来后再用 fill_name 换回昵称——学生的身份信息不出平台。
"""
import json
import logging
import re
import time
from dataclasses import dataclass

import requests
from django.conf import settings

from ..models import LLMCallLog

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.2
NAME_PLACEHOLDER = '{name}'
_TIMEOUT = 60
_NET_RETRIES = 2


class LLMNotConfigured(Exception):
    """没配 LLM_API_KEY / LLM_API_URL。上层据此走确定性的兜底逻辑。"""


def is_configured() -> bool:
    return bool(getattr(settings, 'LLM_API_KEY', '').strip()
                and getattr(settings, 'LLM_API_URL', '').strip())


@dataclass
class LLMResult:
    data: dict | None       # 解析出的 JSON 对象；接口出错或解析失败为 None
    raw: str                # 模型原始输出
    log: LLMCallLog
    error: str = ''         # 网络 / 接口错误

    @property
    def ok(self):
        return self.data is not None


_FENCE_RE = re.compile(r'^\s*```(?:json)?\s*|\s*```\s*$', re.I)


def parse_json(text):
    """容错解析：剥掉 Markdown 代码围栏；只接受 JSON 对象。失败返回 None。"""
    s = _FENCE_RE.sub('', (text or '').strip()).strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        # 模型偶尔在 JSON 前后多说一句话：截取第一个 { 到最后一个 }
        start, end = s.find('{'), s.rfind('}')
        if start == -1 or end <= start:
            return None
        try:
            obj = json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _post(payload):
    """真正发请求的一层。单独拆出来，测试里只需打桩这一个函数。"""
    r = requests.post(
        settings.LLM_API_URL.strip(),
        headers={
            'Authorization': f'Bearer {settings.LLM_API_KEY.strip()}',
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def chat_json(purpose, messages, *, temperature=DEFAULT_TEMPERATURE, max_tokens=2000,
              attempt=1, tag='', task=None, learner=None):
    """
    调一次大模型并要求 JSON 输出。未配置时抛 LLMNotConfigured；其余错误都不抛，
    体现在返回值的 error / data=None 上，并照常写日志（失败调用也是测试数据）。
    """
    if not is_configured():
        raise LLMNotConfigured('未配置大模型：请在 .env 中填写 LLM_API_KEY / LLM_API_URL / LLM_MODEL')

    payload = {
        'model': getattr(settings, 'LLM_MODEL', '').strip(),
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }

    t0 = time.monotonic()
    resp, err = None, ''
    for i in range(_NET_RETRIES + 1):
        try:
            resp, err = _post(payload), ''
            break
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            err = f'HTTP {code}'
            if code and code < 500 and code != 429:
                break           # key 错、参数错之类，重试也没用
        except (requests.Timeout, requests.ConnectionError) as e:
            err = f'{type(e).__name__}: {e}'
        except Exception as e:  # 非预期错误不重试
            err = f'{type(e).__name__}: {e}'
            break
        if i < _NET_RETRIES:
            time.sleep(1.5 * (i + 1))
    duration = int((time.monotonic() - t0) * 1000)

    raw, usage = '', {}
    if resp is not None:
        try:
            raw = resp['choices'][0]['message']['content'] or ''
        except (KeyError, IndexError, TypeError):
            err = err or '接口返回格式异常'
        if isinstance(resp, dict):
            usage = resp.get('usage') or {}
    if err:
        logger.warning('LLM 调用失败 purpose=%s attempt=%s: %s', purpose, attempt, err)

    log = LLMCallLog.objects.create(
        purpose=purpose,
        request={'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens},
        response=raw,
        duration_ms=duration,
        prompt_tokens=usage.get('prompt_tokens') or 0,
        completion_tokens=usage.get('completion_tokens') or 0,
        total_tokens=usage.get('total_tokens') or 0,
        attempt=attempt,
        error=err,
        tag=tag,
        task=task,
        learner=learner,
    )
    return LLMResult(data=parse_json(raw) if raw else None, raw=raw, log=log, error=err)


def mark(log, check):
    """把校验结论回写到调用日志（格式是否合格、规则是否通过、错误清单）。"""
    if log is None:
        return
    log.passed = check.ok
    log.checks = check.as_dict()
    log.save(update_fields=['passed', 'checks'])


# ── 隐私：身份信息不出平台 ──────────────────────────────────────────

def redact(text, names):
    """把文本里出现的姓名 / 昵称 / 用户名换成 {name}。长的先换，避免"小航"被"航"截断。"""
    out = text or ''
    for n in sorted({(n or '').strip() for n in names if n and len(n.strip()) >= 2},
                    key=len, reverse=True):
        out = out.replace(n, NAME_PLACEHOLDER)
    return out


def fill_name(obj, nickname):
    """把模型输出里的 {name} 换回昵称（递归处理 dict / list 里的所有字符串）。"""
    if isinstance(obj, str):
        return obj.replace(NAME_PLACEHOLDER, nickname)
    if isinstance(obj, list):
        return [fill_name(x, nickname) for x in obj]
    if isinstance(obj, dict):
        return {k: fill_name(v, nickname) for k, v in obj.items()}
    return obj
