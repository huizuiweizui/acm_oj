"""
Skill 1：分词与规范化（规则实现）

- 统一全角半角、空白
- jieba 分词并标注词性
- 编程术语和卡片名（data/terms.txt）加入用户词典，保证“循环”“左转”“跳过”等不被切碎
- 个人词表里的自创词整体保留为一个词（只对当前学生生效，不污染全局词典）

模块级函数 normalize / segment / keywords / is_known_word 也可单独使用，
例如用 keywords() 修复 rag.py 中按空格切中文的问题。
"""
from __future__ import annotations

import logging
import re
import threading
import unicodedata
from pathlib import Path

import jieba
import jieba.posseg as pseg

from .base import Skill, SkillContext, SkillResult

jieba.setLogLevel(logging.WARNING)

DATA_DIR = Path(__file__).resolve().parent / "data"
TERMS_FILE = DATA_DIR / "terms.txt"

_lock = threading.Lock()
_tokenizer: jieba.Tokenizer | None = None
_pos_tokenizer: pseg.POSTokenizer | None = None

_WS = re.compile(r"\s+")
_CJK = re.compile(r"^[一-鿿]+$")

# 关键词提取时保留的词性前缀：名词、动词、形容词、英文、成语、习用语
_KEYWORD_POS = ("n", "v", "a", "eng", "i", "l")
_STOPWORDS = {
    "的", "了", "吗", "呢", "吧", "啊", "是", "在", "有", "和", "就", "都", "也", "还",
    "要", "想", "会", "能", "可以", "这个", "那个", "什么", "怎么", "为什么", "一下",
}


def _get_tokenizers() -> tuple[jieba.Tokenizer, pseg.POSTokenizer]:
    """懒加载：第一次调用时初始化 jieba（约 1 秒），之后复用。"""
    global _tokenizer, _pos_tokenizer
    if _pos_tokenizer is None:
        with _lock:
            if _pos_tokenizer is None:
                tk = jieba.Tokenizer()
                tk.initialize()
                if TERMS_FILE.exists():
                    with open(TERMS_FILE, "rb") as f:
                        tk.load_userdict(f)
                _tokenizer = tk
                _pos_tokenizer = pseg.POSTokenizer(tk)
    return _tokenizer, _pos_tokenizer  # type: ignore[return-value]


def normalize(text: str) -> str:
    """全角转半角（NFKC），合并空白，去首尾空白。"""
    text = unicodedata.normalize("NFKC", text or "")
    return _WS.sub(" ", text).strip()


def word_freq(word: str) -> int:
    """词在 jieba 词典中的词频，不在词典中为 0。"""
    tk, _ = _get_tokenizers()
    return tk.FREQ.get(word, 0)


def is_known_word(word: str) -> bool:
    """词是否在 jieba 词典（含编程术语词典）中。"""
    return word_freq(word) > 0


def _protected_spans(text: str, protected: list[str]) -> list[tuple[int, int]]:
    """在文本中找出需要整体保留的词的位置，长词优先，互不重叠。"""
    spans: list[tuple[int, int]] = []
    taken = [False] * len(text)
    for word in sorted({w for w in protected if w}, key=len, reverse=True):
        start = 0
        while True:
            idx = text.find(word, start)
            if idx < 0:
                break
            end = idx + len(word)
            if not any(taken[idx:end]):
                spans.append((idx, end))
                for i in range(idx, end):
                    taken[i] = True
            start = idx + 1
    return sorted(spans)


def segment(text: str, glossary: dict[str, str] | None = None) -> list[dict]:
    """
    分词并标注词性。返回 [{"word", "pos", "start", "end", "glossary"}]。
    glossary 中的自创词作为整词保留，glossary=True。
    """
    _, pt = _get_tokenizers()
    spans = _protected_spans(text, list((glossary or {}).keys()))
    tokens: list[dict] = []

    def cut_gap(gap: str, offset: int) -> None:
        cursor = offset
        for pair in pt.cut(gap):
            word = pair.word
            tokens.append({"word": word, "pos": pair.flag, "start": cursor,
                           "end": cursor + len(word), "glossary": False})
            cursor += len(word)

    pos = 0
    for start, end in spans:
        if start > pos:
            cut_gap(text[pos:start], pos)
        tokens.append({"word": text[start:end], "pos": "nz", "start": start,
                       "end": end, "glossary": True})
        pos = end
    if pos < len(text):
        cut_gap(text[pos:], pos)
    return tokens


def keywords(tokens: list[dict]) -> list[str]:
    """从分词结果中取关键词（去重、保序），用于关键词检索。"""
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        w = t["word"].strip()
        if not w or w in _STOPWORDS or w in seen:
            continue
        if t["glossary"] or t["pos"].startswith(_KEYWORD_POS):
            if len(w) >= 2 or t["pos"] == "eng":
                seen.add(w)
                out.append(w)
    return out


def is_cjk_word(word: str) -> bool:
    return bool(_CJK.match(word))


class SegmentSkill(Skill):
    name = "segment"
    title = "分词与规范化"
    kind = "rule"
    description = "统一全半角和空白，用 jieba 分词并标注词性；编程术语与个人词表中的词整体保留。"

    def run(self, text: str, ctx: SkillContext) -> SkillResult:
        norm = normalize(text)
        tokens = segment(norm, ctx.learner.glossary)
        ctx.state["raw_text"] = text
        ctx.state["text"] = norm
        ctx.state["tokens"] = tokens
        return SkillResult(
            skill=self.name,
            data={"text": norm, "tokens": tokens, "keywords": keywords(tokens)},
        )
