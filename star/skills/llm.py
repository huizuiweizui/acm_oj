"""
大模型调用封装（OpenAI 兼容接口，DeepSeek 可直接使用）。

- 统一使用 JSON 输出模式：response_format = {"type": "json_object"}
  按 DeepSeek 文档要求，提示词里须出现 “json” 字样并给出示例，max_tokens 要留够
- 返回空内容、网络错误、JSON 解析失败时自动重试
- 每次调用通过 on_call 回调交出调用记录，可直接写入 LLMCallLog 表，作为测试报告的数据来源

配置沿用平台现有的 LLM_API_KEY / LLM_API_URL / LLM_MODEL：
LLM_API_URL 填完整地址（以 /chat/completions 结尾），只填到域名时会自动补全。
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Protocol

import requests


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    def chat_json(self, messages: list[dict], *, temperature: float = 0.2,
                  max_tokens: int = 512, purpose: str = "") -> dict: ...


class OpenAICompatClient:
    def __init__(self, api_key: str, url: str, model: str, *, timeout: float = 30,
                 max_retries: int = 2, on_call: Callable[[dict], Any] | None = None):
        if not api_key or not url or not model:
            raise LLMError("LLM_API_KEY / LLM_API_URL / LLM_MODEL 未配置完整")
        url = url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        self.api_key, self.url, self.model = api_key, url, model
        self.timeout, self.max_retries, self.on_call = timeout, max_retries, on_call

    @classmethod
    def from_env(cls, **kw) -> "OpenAICompatClient":
        return cls(os.environ.get("LLM_API_KEY", ""), os.environ.get("LLM_API_URL", ""),
                   os.environ.get("LLM_MODEL", ""), **kw)

    @classmethod
    def from_django_settings(cls, **kw) -> "OpenAICompatClient":
        from django.conf import settings
        return cls(getattr(settings, "LLM_API_KEY", ""), getattr(settings, "LLM_API_URL", ""),
                   getattr(settings, "LLM_MODEL", ""), **kw)

    def chat_json(self, messages: list[dict], *, temperature: float = 0.2,
                  max_tokens: int = 512, purpose: str = "") -> dict:
        payload = {"model": self.model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_err = ""
        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            content, usage = "", {}
            try:
                resp = requests.post(self.url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                body = resp.json()
                content = (body["choices"][0]["message"].get("content") or "").strip()
                usage = body.get("usage") or {}
                if not content:
                    raise ValueError("模型返回了空内容")
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("模型返回的不是 JSON 对象")
                self._record(purpose, messages, content, usage, t0, attempt, ok=True)
                return data
            except (requests.RequestException, ValueError, KeyError, IndexError) as e:
                last_err = f"{type(e).__name__}: {e}"
                self._record(purpose, messages, content, usage, t0, attempt, ok=False, error=last_err)
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
        raise LLMError(f"大模型调用失败（重试 {self.max_retries} 次）：{last_err}")

    def _record(self, purpose, messages, content, usage, t0, attempt, *, ok, error=""):
        if not self.on_call:
            return
        try:
            self.on_call({
                "purpose": purpose, "model": self.model, "ok": ok, "error": error,
                "attempt": attempt, "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "usage": usage, "messages": messages, "response": content,
            })
        except Exception:  # 记录失败不能影响主流程
            pass
