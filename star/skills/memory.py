"""
Skill：个人表达记忆（规则实现）

孤独症学生常反复用同一套说法表达同一个意思。把“这个学生的这句话 → 意图”记下来，
下次说同样或很接近的话时直接给出意图，不再调用大模型：
  - 同一句话每次都被理解成同一个意思（坚持同一性）
  - 少调一次大模型

记忆条目由平台维护（大模型高置信度识别两次一致后自动生效，或教师确认、手动添加），
本模块只负责“比对”，不读写数据库。

比对规则（只认很接近的说法，宁可漏也不误配）：
  1. 去掉标点、空白和句末语气词（啦、呀、吧、呢、啊、吗、了……）后完全相同；
  2. 或者双方都至少 4 个字、相似度 ≥ 0.85，并且否定词（不、没、别）出现的次数相同——
     “要提示”和“不要提示”永远不会配上。
比对的是词表映射之后的文本，所以“呜呜车不走了”和“小火车不走了”算同一句。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from .base import Skill, SkillContext, SkillResult
from .echo import core

# 可以记忆的意图。answer 和当前题目有关、echo 和上下文有关、unclear 没有信息，都不记
MEMORABLE = ("ask_hint", "dont_know", "skip", "chat", "need_help")

_TAIL = re.compile(r"[啦呀吧呢啊哦嘛喔哇吗了]+$")
_NEG = re.compile(r"[不没别]")
FUZZY_THRESHOLD = 0.85
FUZZY_MIN_LEN = 4


def key_of(text: str) -> str:
    """比对用的规范形式：去标点、空白、句末语气词。"""
    k = core(text)
    stripped = _TAIL.sub("", k)
    return stripped or k


def match(text: str, entries: list[dict], *, threshold: float = FUZZY_THRESHOLD) -> dict | None:
    """
    在记忆条目 [{"text", "intent", ...}] 中找与 text 最接近的一条，找不到返回 None。
    返回 {"text", "intent", "method": "exact"|"fuzzy", "score"}。
    """
    k = key_of(text)
    if not k:
        return None
    best: dict | None = None
    for e in entries:
        if e.get("intent") not in MEMORABLE:
            continue
        ek = key_of(e.get("text", ""))
        if not ek:
            continue
        if ek == k:
            return {"text": e["text"], "intent": e["intent"], "method": "exact", "score": 1.0}
        if min(len(k), len(ek)) < FUZZY_MIN_LEN or len(_NEG.findall(k)) != len(_NEG.findall(ek)):
            continue
        score = SequenceMatcher(None, k, ek).ratio()
        if score >= threshold and (best is None or score > best["score"]):
            best = {"text": e["text"], "intent": e["intent"], "method": "fuzzy", "score": round(score, 3)}
    return best


class ExpressionMemorySkill(Skill):
    name = "expr_memory"
    title = "表达记忆"
    kind = "rule"
    description = "把学生的话和他的个人表达记忆比对，说过的话直接给出记住的意图，不再调用大模型。"

    def __init__(self, threshold: float = FUZZY_THRESHOLD):
        self.threshold = threshold

    def run(self, text: str, ctx: SkillContext) -> SkillResult:
        entries = ctx.learner.expressions
        if not entries:
            return SkillResult(skill=self.name, data={"hit": None}, notes=["没有表达记忆"])
        hit = match(ctx.state.get("text") or text, entries, threshold=self.threshold)
        if hit:
            ctx.state["memory_hit"] = hit
        return SkillResult(skill=self.name, data={"hit": hit})
