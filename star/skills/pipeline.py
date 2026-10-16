"""
固定顺序的处理流水线。

学生输入：
  分词与规范化 → 仿说检测（是仿说就停止，换问法重问）→ 词表映射 → 代词标注 → 意图识别

系统输出：
  字面化检查（check_reply）

disabled 参数可以关掉某几个 skill，用于消融实验，例如
  InputPipeline(llm, disabled={"echo_detect", "lexicon_map", "pronoun_tag"})
表示“关闭沟通特征处理”。分词是其他 skill 的基础，不能关闭。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import Skill, SkillContext, SkillResult
from .echo import EchoDetectSkill
from .intent import IntentSkill
from .lexicon import LexiconMapSkill
from .llm import LLMClient
from .plain_check import PlainCheckSkill
from .pronoun import PronounTagSkill
from .segment import SegmentSkill

INPUT_ORDER = ("segment", "echo_detect", "lexicon_map", "pronoun_tag", "intent")
COMM_SKILLS = frozenset({"echo_detect", "lexicon_map", "pronoun_tag"})  # 沟通特征处理


@dataclass
class PipelineResult:
    intent: dict[str, Any]
    text: str
    echo: dict[str, Any] | None
    mappings: list[dict]
    candidate_words: list[str]
    trace: list[SkillResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent, "text": self.text, "echo": self.echo,
            "mappings": self.mappings, "candidate_words": self.candidate_words,
            "trace": [r.to_dict() for r in self.trace],
        }


class InputPipeline:
    def __init__(self, llm: LLMClient | None = None, *, disabled: set[str] | frozenset[str] = frozenset(),
                 use_pinyin: bool = False, echo_threshold: float = 0.85,
                 fuzzy_threshold: float = 0.75):
        self.skills: dict[str, Skill] = {
            "segment": SegmentSkill(),
            "echo_detect": EchoDetectSkill(threshold=echo_threshold),
            "lexicon_map": LexiconMapSkill(fuzzy_threshold=fuzzy_threshold, use_pinyin=use_pinyin),
            "pronoun_tag": PronounTagSkill(),
            "intent": IntentSkill(llm),
        }
        unknown = set(disabled) - set(INPUT_ORDER)
        if unknown:
            raise ValueError(f"未知的 skill：{unknown}")
        self.disabled = set(disabled) - {"segment"}

    def run(self, text: str, ctx: SkillContext) -> PipelineResult:
        ctx.state.clear()
        trace: list[SkillResult] = []
        for name in INPUT_ORDER:
            if name in self.disabled:
                continue
            res = self.skills[name](text, ctx)
            trace.append(res)
            if res.stop:
                break

        echo = ctx.state.get("echo")
        intent = ctx.state.get("intent")
        if intent is None:  # 被仿说检测提前停止
            intent = {"intent": "echo", "answer": "", "restated": "学生重复了系统刚说的话",
                      "confidence": 1.0, "source": "rule"}
        return PipelineResult(
            intent=intent,
            text=ctx.state.get("text", text),
            echo=echo,
            mappings=ctx.state.get("mappings", []),
            candidate_words=ctx.state.get("candidate_words", []),
            trace=trace,
        )


_plain = PlainCheckSkill()


def check_reply(text: str, ctx: SkillContext) -> dict[str, Any]:
    """检查系统将要展示的文字是否平实，返回 {"ok", "violations", "stats"}。"""
    return _plain(text, ctx).data
