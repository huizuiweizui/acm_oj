"""
Skill 4：代词标注（规则实现）

找出学生输入里的人称代词。如果画像里标注了“你、我的用法和常规不同”，
就生成给大模型的理解提示，例如“学生说的‘你’可能指他自己”。

本 skill 不改写原文，也不对学生做任何判断，只为下一步意图识别提供参考。
"""
from __future__ import annotations

from .base import Skill, SkillContext, SkillResult
from .segment import normalize, segment

FIRST = {"我", "我们", "咱", "咱们"}
SECOND = {"你", "您", "你们"}
THIRD = {"他", "她", "它", "他们", "她们", "它们"}


class PronounTagSkill(Skill):
    name = "pronoun_tag"
    title = "代词标注"
    kind = "rule"
    description = "找出学生输入中的人称代词；画像中标注代词用法特点时，生成给大模型的理解提示。"

    def run(self, text: str, ctx: SkillContext) -> SkillResult:
        tokens = ctx.state.get("tokens") or segment(normalize(text))
        found = []
        for t in tokens:
            w = t["word"]
            person = 1 if w in FIRST else 2 if w in SECOND else 3 if w in THIRD else 0
            if person:
                found.append({"word": w, "person": person, "start": t["start"], "end": t["end"]})

        hints: list[str] = []
        if ctx.learner.pronoun_reversal:
            who = ctx.learner.name or "学生"
            if any(f["person"] == 2 for f in found):
                hints.append(f"学生说的“你”可能指他自己（{who}）")
            if any(f["person"] == 1 for f in found):
                hints.append("学生说的“我”可能指系统或老师，请结合上下文判断")
        ctx.state["pronoun_hints"] = hints
        return SkillResult(
            skill=self.name,
            data={"pronouns": found, "hints": hints, "reversal_flag": ctx.learner.pronoun_reversal},
        )
