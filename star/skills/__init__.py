"""
星语 skills：对话助手与改造链使用的处理模块。

用法见同目录 README.md。
"""
from .base import (LEVEL_ENTRY, LEVEL_STARTER, LearnerView, Skill, SkillContext,
                   SkillResult, Turn)
from .echo import EchoDetectSkill
from .intent import INTENTS, IntentSkill
from .lexicon import LexiconMapSkill
from .llm import LLMClient, LLMError, OpenAICompatClient
from .memory import ExpressionMemorySkill
from .pipeline import COMM_SKILLS, INPUT_ORDER, InputPipeline, PipelineResult, check_reply
from .plain_check import PlainCheckSkill, check_text
from .pronoun import PronounTagSkill
from .segment import SegmentSkill, keywords, normalize, segment

SKILL_CLASSES: dict[str, type[Skill]] = {
    cls.name: cls for cls in (SegmentSkill, EchoDetectSkill, LexiconMapSkill,
                              PronounTagSkill, ExpressionMemorySkill, IntentSkill, PlainCheckSkill)
}


def describe_all() -> list[dict[str, str]]:
    """所有 skill 的说明，可用于页面展示或以后改成工具调用。"""
    return [cls.describe() for cls in SKILL_CLASSES.values()]


__all__ = [
    "LEVEL_ENTRY", "LEVEL_STARTER", "LearnerView", "Skill", "SkillContext", "SkillResult", "Turn",
    "SegmentSkill", "EchoDetectSkill", "LexiconMapSkill", "PronounTagSkill", "ExpressionMemorySkill",
    "IntentSkill", "PlainCheckSkill", "INTENTS", "InputPipeline", "PipelineResult", "check_reply", "check_text",
    "COMM_SKILLS", "INPUT_ORDER", "LLMClient", "LLMError", "OpenAICompatClient",
    "SKILL_CLASSES", "describe_all", "keywords", "normalize", "segment",
]
