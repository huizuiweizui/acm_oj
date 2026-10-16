"""
Skill 6：字面化检查（规则实现）

检查系统将要展示给学生的文字（改写后的题面、提示语、对话回复）是否足够平实：
  - 单句长度：启蒙层不超过 12 字，入门层不超过 20 字（不计标点）          → 错误
  - 双重否定（不得不、不能不……）                                        → 错误
  - 反问句（难道、岂不、不是……吗……）                                    → 错误
  - 比喻、成语（好像、仿佛、像……一样；jieba 词性 i）                     → 提醒
  - 含糊词（差不多、大概、稍微……）                                      → 提醒
  - 一句话里逗号超过 2 个（可能不止讲一件事）                              → 提醒

有“错误”时 ok=False，改造链据此把内容打回重新生成。
stats 中的平均句长、最长句长可直接用于测试报告（改写前后对比）。
"""
from __future__ import annotations

import re

from .base import LEVEL_STARTER, Skill, SkillContext, SkillResult
from .echo import core
from .segment import normalize, segment

MAX_SENTENCE_LEN = {LEVEL_STARTER: 12, "entry": 20}

_SENT_SPLIT = re.compile(r"(?<=[。!！?？;；\n])")
_COMMA = re.compile(r"[,，、]")

DOUBLE_NEGATION = ("不得不", "不会不", "不能不", "不可不", "没有不", "无不", "未必不",
                   "不是不", "并非不", "不无")
RHETORICAL = (r"难道", r"岂不", r"何尝", r"何必", r"不是.{0,8}吗", r"怎么能.{0,8}呢")
FIGURATIVE = (r"好像", r"仿佛", r"犹如", r"宛如", r"如同", r"像.{1,8}一样", r"似的")
VAGUE = ("差不多", "大概", "大约", "也许", "稍微", "适当", "左右", "尽量", "随便", "一些")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(normalize(text)) if core(s)]


def check_text(text: str, level: str = "entry") -> dict:
    max_len = MAX_SENTENCE_LEN.get(level, 20)
    sentences = split_sentences(text)
    violations: list[dict] = []

    def add(rule: str, sentence: str, detail: str, severity: str) -> None:
        violations.append({"rule": rule, "sentence": sentence, "detail": detail, "severity": severity})

    lengths = []
    for s in sentences:
        n = len(core(s))
        lengths.append(n)
        if n > max_len:
            add("too_long", s, f"{n} 字，超过 {max_len} 字", "error")
        for w in DOUBLE_NEGATION:
            if w in s:
                add("double_negation", s, f"双重否定“{w}”", "error")
        for p in RHETORICAL:
            if m := re.search(p, s):
                add("rhetorical", s, f"反问“{m.group(0)}”", "error")
        for p in FIGURATIVE:
            if m := re.search(p, s):
                add("figurative", s, f"比喻“{m.group(0)}”", "warning")
        for t in segment(s):
            if t["pos"] == "i":
                add("idiom", s, f"成语“{t['word']}”", "warning")
        for w in VAGUE:
            if w in s:
                add("vague", s, f"含糊词“{w}”", "warning")
        if len(_COMMA.findall(s)) > 2:
            add("multi_info", s, "逗号超过 2 个，可能不止讲一件事", "warning")

    stats = {
        "sentences": len(sentences),
        "avg_len": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "max_len": max(lengths) if lengths else 0,
        "max_allowed": max_len,
    }
    ok = not any(v["severity"] == "error" for v in violations)
    return {"ok": ok, "violations": violations, "stats": stats}


class PlainCheckSkill(Skill):
    name = "plain_check"
    title = "字面化检查"
    kind = "rule"
    description = "检查系统要展示的文字：句长、双重否定、反问、比喻成语、含糊词；有错误时打回重写。"

    def run(self, text: str, ctx: SkillContext) -> SkillResult:
        result = check_text(text, ctx.learner.level)
        return SkillResult(skill=self.name, data=result)
