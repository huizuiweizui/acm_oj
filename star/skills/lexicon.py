"""
Skill 2：词表映射（规则实现）

对应原始构想中的“自创词汇：重写与专属知识库”。个人词表就是每个学生的专属知识库。

匹配分三轮，前一轮匹配到的位置后一轮不再处理：
  1. 精确匹配：文本中直接出现词表里的自创词
  2. 同音匹配（可选，需安装 pypinyin）：拼音相同，如“乌乌车”对上“呜呜车”
  3. 相近匹配：difflib 相似度达到阈值，如“呜呜火车”对上“呜呜车”

匹配到的自创词替换为标准词，并记录替换明细。
词表里没有、jieba 词典也不认识的新词列为“候选新词”，交给教师确认后再加入词表。
"""
from __future__ import annotations

from difflib import SequenceMatcher

from .base import Skill, SkillContext, SkillResult
from .segment import is_cjk_word, is_known_word, normalize, segment, word_freq

try:  # 同音匹配是可选功能
    from pypinyin import lazy_pinyin
    HAS_PINYIN = True
except ImportError:  # pragma: no cover
    lazy_pinyin = None
    HAS_PINYIN = False


def find_matches(text: str, glossary: dict[str, str], *, fuzzy_threshold: float = 0.75,
                 use_pinyin: bool = False) -> list[dict]:
    """返回不重叠的匹配列表 [{"start","end","from","key","to","method","score"}]，按位置排序。"""
    keys = sorted((k for k in glossary if k), key=len, reverse=True)
    taken = [False] * len(text)
    matches: list[dict] = []

    def free(i: int, j: int) -> bool:
        return not any(taken[i:j])

    def take(i: int, j: int, key: str, method: str, score: float) -> None:
        for p in range(i, j):
            taken[p] = True
        matches.append({"start": i, "end": j, "from": text[i:j], "key": key,
                        "to": glossary[key], "method": method, "score": round(score, 3)})

    # 第 1 轮：精确匹配
    for key in keys:
        start = 0
        while (idx := text.find(key, start)) >= 0:
            if free(idx, idx + len(key)):
                take(idx, idx + len(key), key, "exact", 1.0)
            start = idx + 1

    # 第 2 轮：同音匹配
    if use_pinyin and HAS_PINYIN:
        for key in keys:
            key_py = lazy_pinyin(key)
            n = len(key)
            for i in range(len(text) - n + 1):
                window = text[i:i + n]
                if free(i, i + n) and is_cjk_word(window) and lazy_pinyin(window) == key_py:
                    take(i, i + n, key, "pinyin", 1.0)

    # 第 3 轮：相近匹配（多音节词才做，避免单字误配）
    candidates: list[tuple[float, int, int, str]] = []
    for key in keys:
        n = len(key)
        if n < 2:
            continue
        for length in {n - 1, n, n + 1}:
            if length < 2:
                continue
            for i in range(len(text) - length + 1):
                window = text[i:i + length]
                if not is_cjk_word(window) or window == glossary[key]:
                    continue
                score = SequenceMatcher(None, window, key).ratio()
                if score >= fuzzy_threshold:
                    candidates.append((score, i, i + length, key))
    for score, i, j, key in sorted(candidates, key=lambda c: (-c[0], c[1])):
        if free(i, j):
            take(i, j, key, "fuzzy", score)

    return sorted(matches, key=lambda m: m["start"])


def apply_matches(text: str, matches: list[dict]) -> str:
    out, pos = [], 0
    for m in matches:
        out.append(text[pos:m["start"]])
        out.append(m["to"])
        pos = m["end"]
    out.append(text[pos:])
    return "".join(out)


RARE_CHAR_FREQ = 1000  # 词频低于此值的单字视为生僻字


def _is_odd(t: dict) -> bool:
    """生僻单字或拟声词，常是自创词的组成部分，如“啵啵仔”“嘟嘟噜”。"""
    w = t["word"]
    if not is_cjk_word(w) or t["glossary"]:
        return False
    return (len(w) == 1 and word_freq(w) < RARE_CHAR_FREQ) or (t["pos"] == "o" and len(w) <= 2)


def unknown_words(tokens: list[dict], matches: list[dict]) -> list[str]:
    """
    候选新词（交教师确认后再加入词表），两种来源：
      1. 两个字以上、jieba 词典中没有的中文词
      2. 连续两个以上的生僻单字或拟声词拼起来的片段，如“啵 啵 仔”→“啵啵仔”
    已被词表匹配替换的位置不计入。
    """
    covered = set()
    for m in matches:
        covered.update(range(m["start"], m["end"]))

    def free(start: int, end: int) -> bool:
        return not covered.intersection(range(start, end))

    out: list[str] = []

    def add(w: str) -> None:
        if w not in out:
            out.append(w)

    run: list[dict] = []

    def flush() -> None:
        if len(run) >= 2:
            w = "".join(t["word"] for t in run)
            if not is_known_word(w) and free(run[0]["start"], run[-1]["end"]):
                add(w)
        run.clear()

    for t in tokens:
        w = t["word"]
        if _is_odd(t):
            run.append(t)
            continue
        flush()
        if (len(w) >= 2 and not t["glossary"] and is_cjk_word(w) and not is_known_word(w)
                and free(t["start"], t["end"])):
            add(w)
    flush()
    return out


class LexiconMapSkill(Skill):
    name = "lexicon_map"
    title = "词表映射"
    kind = "rule"
    description = "按学生的个人词表把自创词替换成标准词，并找出词表中没有的候选新词。"

    def __init__(self, fuzzy_threshold: float = 0.75, use_pinyin: bool = False):
        self.fuzzy_threshold = fuzzy_threshold
        self.pinyin_requested = use_pinyin
        self.use_pinyin = use_pinyin and HAS_PINYIN

    def run(self, text: str, ctx: SkillContext) -> SkillResult:
        src = ctx.state.get("text") or normalize(text)
        tokens = ctx.state.get("tokens") or segment(src, ctx.learner.glossary)
        glossary = ctx.learner.glossary
        matches = find_matches(src, glossary, fuzzy_threshold=self.fuzzy_threshold,
                               use_pinyin=self.use_pinyin) if glossary else []
        new_text = apply_matches(src, matches)
        candidates = unknown_words(tokens, matches)

        ctx.state["text"] = new_text
        ctx.state["tokens"] = segment(new_text)
        ctx.state["mappings"] = matches
        ctx.state["candidate_words"] = candidates

        notes = []
        if self.pinyin_requested and not HAS_PINYIN:
            notes.append("未安装 pypinyin，同音匹配未启用")
        return SkillResult(
            skill=self.name,
            data={"text": new_text, "mappings": matches, "candidate_words": candidates},
            notes=notes,
        )
