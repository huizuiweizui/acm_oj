"""
Skill 基础定义：统一接口、上下文、结果。

每个 skill 都是一个类，调用方式统一为 ``skill(text, ctx) -> SkillResult``：
  - text：本次要处理的文本（学生输入，或系统将要说的话）
  - ctx ：上下文，包含学习者画像、对话历史，以及 skill 之间传递的中间结果 ctx.state
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

LEVEL_STARTER = "starter"  # 启蒙层
LEVEL_ENTRY = "entry"      # 入门层


@dataclass
class LearnerView:
    """
    skill 用到的画像子集，由 LearnerProfile 的画像 JSON 转换而来。
    只包含学习相关信息，不包含任何诊断信息。
    """
    name: str = ""
    level: str = LEVEL_ENTRY
    glossary: dict[str, str] = field(default_factory=dict)  # 个人词表：自创词 -> 标准词
    pronoun_reversal: bool = False  # 沟通特点：你、我的用法和常规不同
    echolalia: bool = False         # 沟通特点：常重复别人刚说过的话
    interests: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict | None) -> "LearnerView":
        d = d or {}
        return cls(
            name=str(d.get("name", "")),
            level=str(d.get("level", LEVEL_ENTRY)),
            glossary={str(k): str(v) for k, v in (d.get("glossary") or {}).items()},
            pronoun_reversal=bool(d.get("pronoun_reversal", False)),
            echolalia=bool(d.get("echolalia", False)),
            interests=[str(x) for x in (d.get("interests") or [])],
        )


@dataclass
class Turn:
    """对话中的一句话。"""
    role: str                     # "system" | "student"
    text: str
    options: list[str] = field(default_factory=list)  # 系统这句话附带的选项按钮

    @classmethod
    def from_dict(cls, d: dict) -> "Turn":
        return cls(role=d.get("role", "system"), text=d.get("text", ""),
                   options=list(d.get("options") or []))


@dataclass
class SkillContext:
    learner: LearnerView = field(default_factory=LearnerView)
    history: list[Turn] = field(default_factory=list)  # 按时间顺序，不含本次输入
    step_prompt: str = ""                               # 当前学习步骤的题面，给意图识别做上下文
    state: dict[str, Any] = field(default_factory=dict)  # skill 之间传递的中间结果

    def last_system_turns(self, n: int = 2) -> list[Turn]:
        """最近 n 句系统发言，最新的在前。"""
        turns = [t for t in reversed(self.history) if t.role == "system"]
        return turns[:n]

    @property
    def last_system_text(self) -> str:
        turns = self.last_system_turns(1)
        return turns[0].text if turns else ""

    @property
    def last_options(self) -> list[str]:
        turns = self.last_system_turns(1)
        return turns[0].options if turns else []


@dataclass
class SkillResult:
    skill: str
    data: dict[str, Any] = field(default_factory=dict)
    stop: bool = False  # True 时流水线不再继续往下执行
    notes: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Skill:
    """所有 skill 的基类。"""
    name = "base"
    title = ""          # 中文名
    kind = "rule"       # "rule" 规则实现 | "llm" 调用大模型
    description = ""

    def run(self, text: str, ctx: SkillContext) -> SkillResult:  # pragma: no cover
        raise NotImplementedError

    def __call__(self, text: str, ctx: SkillContext) -> SkillResult:
        t0 = time.perf_counter()
        res = self.run(text, ctx)
        res.elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return res

    @classmethod
    def describe(cls) -> dict[str, str]:
        """skill 的自我描述。以后如果改成让大模型自己选择调用哪个 skill，可直接用作工具说明。"""
        return {"name": cls.name, "title": cls.title, "kind": cls.kind,
                "description": cls.description}
