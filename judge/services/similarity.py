"""代码相似度检测（Winnowing 指纹算法）。

参考 Schleimer, Wilkerson, Aiken (2003) *Winnowing: Local Algorithms for
Document Fingerprinting*。流程：

  1. 词法归一化：标识符→I、数字→N、字符串→S，保留运算符/标点、丢弃注释。
     —— 抽象掉变量名/常量/空白/注释，使「改名 + 重排版 + 改注释」的抄袭无所遁形。
  2. 取所有相邻 k 个 token 的 k-gram，对每个 k-gram 做滚动哈希。
  3. Winnowing：在每个长度为 w 的哈希窗口里取最小值作为指纹，得到文档指纹集合。
     —— 保证任意长度 ≥ w+k-1 的雷同片段必被捕获，且指纹密度可控。
  4. 用重叠系数（containment）/ Jaccard 度量两份代码指纹集合的相似度。

纯 Python（仅依赖 re），不耦合 Django，便于单元测试与论文实验复现。
"""
import re

K_GRAM = 5            # 每个片段含的 token 数
WINDOW = 4            # winnowing 窗口；可检出长度 ≥ w+k-1 的雷同片段
_MOD = (1 << 61) - 1  # 大素数模，降低哈希碰撞

_RE_CACHE = {}


def _token_re(language):
    """按语言构造词法正则（缓存）。Python 的 // 是整除而非注释，需区别对待。"""
    cached = _RE_CACHE.get(language)
    if cached is not None:
        return cached
    if language == 'Python':
        parts = [r'(?P<line_comment>\#[^\n]*)']
    else:  # C / C++ / Java / Go：// 与 /* */ 为注释，# 视作 C 预处理（一并丢弃）
        parts = [r'(?P<line_comment>//[^\n]*|\#[^\n]*)', r'(?P<block_comment>/\*.*?\*/)']
    parts += [
        r'(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')',
        r'(?P<number>\d+\.?\d*)',
        r'(?P<ident>[A-Za-z_]\w*)',
        r'(?P<op>\S)',
    ]
    compiled = re.compile('|'.join(parts), re.S)
    _RE_CACHE[language] = compiled
    return compiled


def tokenize(code, language='C++'):
    """词法归一化为 token 串。"""
    out = []
    for m in _token_re(language).finditer(code or ''):
        kind = m.lastgroup
        if kind in ('line_comment', 'block_comment'):
            continue
        if kind == 'string':
            out.append('S')
        elif kind == 'number':
            out.append('N')
        elif kind == 'ident':
            out.append('I')
        else:
            out.append(m.group())
    return out


def _hash_tokens(tokens):
    h = 0
    for t in tokens:
        for ch in t:
            h = (h * 131 + ord(ch)) % _MOD
        h = (h * 131 + 2) % _MOD  # token 分隔符，避免 "ab","c" 与 "a","bc" 撞值
    return h


def _kgram_hashes(tokens, k):
    if len(tokens) < k:
        return [_hash_tokens(tokens)] if tokens else []
    return [_hash_tokens(tokens[i:i + k]) for i in range(len(tokens) - k + 1)]


def fingerprint(code, language='C++', k=K_GRAM, w=WINDOW):
    """返回代码的指纹集合（frozenset）。"""
    hashes = _kgram_hashes(tokenize(code, language), k)
    if not hashes:
        return frozenset()
    if len(hashes) <= w:
        return frozenset([min(hashes)])
    fps = set()
    for i in range(len(hashes) - w + 1):
        fps.add(min(hashes[i:i + w]))
    return frozenset(fps)


def similarity(fp_a, fp_b):
    """重叠系数（containment）= |A∩B| / min(|A|,|B|)，0..1。
    对「抄一部分再扩写」敏感，适合查重。"""
    if not fp_a or not fp_b:
        return 0.0
    return len(fp_a & fp_b) / min(len(fp_a), len(fp_b))


def jaccard(fp_a, fp_b):
    """Jaccard = |A∩B| / |A∪B|，0..1。对称、更保守，可作对照指标。"""
    if not fp_a or not fp_b:
        return 0.0
    return len(fp_a & fp_b) / len(fp_a | fp_b)


def token_count(code, language='C++'):
    return len(tokenize(code, language))
