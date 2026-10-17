"""
Skill 2：仿说检测（规则实现）

判断学生是不是在重复系统刚说过的话。判定为仿说时，流水线停止，由系统换一种问法重问。

为了不把正常回答误判为仿说，先排除两种情况：
  1. 学生说的正好是系统给出的某个选项（如系统给了“要 / 不要”按钮，学生打“要”）
  2. 学生在回答正反问句（如系统问“要不要看提示”，学生说“要看提示”或“不要看提示”）

然后把学生的话与系统最近几句话（整句和其中的每个分句）比较字符相似度，
达到阈值即判定为仿说。分句比较可以识别“只重复了后半句”的情况。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from .base import Skill, SkillContext, SkillResult
from .segment import normalize

_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)
_CLAUSE_SPLIT = re.compile(r"[,，。.!！?？;；:：、\s]+")
_A_NOT_A = re.compile(r"([\u4e00-\u9fff])不\1")  # 要不要、是不是、会不会、能不能……


def core(text: str) -> str:
    """去掉标点和空白后的文本，用于比较。"""
    return _NON_WORD.sub("", normalize(text)).lower()


def answer_to_a_not_a(student: str, system_text: str) -> bool | None:
    """
    学生是否在回答系统的正反问句。返回 True（肯定）、False（否定）或 None（不是这种情况）。
    例：系统“你要不要看提示” → 肯定式“你要看提示”，否定式“你不要看提示”；
        学生说“要看提示”“要”“不要”都算回答。
    """
    for clause in _CLAUSE_SPLIT.split(normalize(system_text)):
        c = core(clause)
        m = _A_NOT_A.search(c)
        if not m:
            continue
        a = m.group(1)
        yes = c[:m.start()] + a + c[m.end():]
        no = c[:m.start()] + "不" + a + c[m.end():]
        tail_yes = a + c[m.end():]
        tail_no = "不" + a + c[m.end():]
        if student in (no, tail_no) or student == "不" + a or (no.endswith(student) and student.startswith("不")):
            return False
        if student in (yes, tail_yes) or student == a or (yes.endswith(student) and student.startswith(a)):
            return True
    return None


class EchoDetectSkill(Skill):
    name = "echo_detect"
    title = "仿说检测"
    kind = "rule"
    description = "判断学生是否在重复系统刚说的话；会排除选项作答和正反问句的回答。"

    def __init__(self, threshold: float = 0.85, lookback: int = 2, min_len: int = 4,
                 stop_on_echo: bool = True):
        self.threshold = threshold    # 相似度达到多少算仿说
        self.lookback = lookback      # 和系统最近几句比较
        self.min_len = min_len        # 系统的话（或分句）至少多长才参与比较，太短的如“好的”不算
        self.stop_on_echo = stop_on_echo

    def run(self, text: str, ctx: SkillContext) -> SkillResult:
        student = core(ctx.state.get("text") or text)
        result = {"is_echo": False, "kind": None, "score": 0.0, "matched": "",
                  "chosen_option": None, "yes_no": None, "suggestion": ""}
        if not student:
            return SkillResult(skill=self.name, data=result, notes=["空输入"])

        # 情况 1：选了选项
        for opt in ctx.last_options:
            if core(opt) == student:
                ctx.state["chosen_option"] = opt
                result["chosen_option"] = opt
                return SkillResult(skill=self.name, data=result, notes=["学生选择了选项"])

        # 情况 2：回答正反问句
        yn = answer_to_a_not_a(student, ctx.last_system_text)
        if yn is not None:
            ctx.state["yes_no"] = yn
            result["yes_no"] = yn
            return SkillResult(skill=self.name, data=result, notes=["学生在回答正反问句"])

        # 与系统最近几句比较
        best_score, best_text, best_kind = 0.0, "", None
        for turn in ctx.last_system_turns(self.lookback):
            whole = core(turn.text)
            pieces = [("full", whole)] + [("partial", core(c)) for c in _CLAUSE_SPLIT.split(normalize(turn.text))]
            for kind, piece in pieces:
                if len(piece) < self.min_len:
                    continue
                score = SequenceMatcher(None, student, piece).ratio()
                if score > best_score:
                    best_score, best_text, best_kind = score, turn.text, kind
        result["score"] = round(best_score, 3)
        if best_score >= self.threshold:
            result.update(is_echo=True, kind=best_kind, matched=best_text,
                          suggestion="换一种问法重问，改用选项按钮提问")
        ctx.state["echo"] = result
        stop = result["is_echo"] and self.stop_on_echo
        return SkillResult(skill=self.name, data=result, stop=stop)
