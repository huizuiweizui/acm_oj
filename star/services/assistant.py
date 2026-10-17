"""
对话助手：学生输入先经过 star/skills 的固定流水线，再由大模型（P3）生成回复，回复固定为"一句话 + 选项"。

处理顺序（与 star/skills/README.md 的流程图一致）：
    0. 求助护栏（确定性）：说到疼、害怕、被欺负等，不经大模型，固定回复"请告诉老师"；
    1. 分词与规范化（jieba，编程术语和个人词表里的词整体保留）；
    2. 仿说检测：与系统最近两句（整句和分句）的相似度 ≥ 0.8 判为仿说；点选项、回答正反问句不算——
       仿说时不当成新内容理解，而是请模型换一种更简单的问法重问；
    3. 词表映射：按个人词表把自创词换成标准词（精确 / 同音 / 相近三轮），另列出候选新词给教师确认；
    4. 代词标注：画像标记了代词逆转时，生成"学生说的'你'可能指他自己"这类理解提示（只用于理解，不纠正）；
    5. 意图识别（大模型，P5）：结合以上结果判断学生想做什么；need_help 直接转给老师；
    6. 系统生成回复（P3），提示词里带上意图、词表替换和代词提示；
    7. 字面化检查：句长（启蒙层 12 字 / 入门层 20 字）、双重否定、反问——不合格回填给模型改一次。
一致性：温度 0.2；同一学生在同一步骤问同一句话，直接返回缓存的回答。
发给大模型的内容一律先把姓名、昵称、用户名换成 {name}。

大模型不可用或回复不合格时，返回固定的兜底回复——学生端永远拿到同样结构的回复。
is_echolalia / apply_vocabulary 是接入 skills 之前的简化实现，保留给 star_eval 的消融实验做对照。
"""
import difflib
import hashlib
import re

from django.core.cache import cache
from django.utils import timezone

from ..skills import (LEVEL_ENTRY, LEVEL_STARTER, InputPipeline, IntentSkill, LearnerView, LLMError, SkillContext,
                      Turn, check_text)
from ..skills.lexicon import HAS_PINYIN
from ..skills.plain_check import MAX_SENTENCE_LEN
from . import llm, prompts
from .validators import check_reply

ECHO_THRESHOLD = 0.8
CACHE_SECONDS = 30 * 24 * 3600
HISTORY_KEEP = 40           # 画像里最多保留的对话条数
CONTEXT_TURNS = 6           # 每次带给模型的最近几条
HELP_WORDS = ('疼', '痛', '难受', '不舒服', '害怕', '好怕', '救命', '想哭', '哭了', '打我',
              '欺负', '受伤', '流血', '头晕', '想吐', '想回家', '想妈妈', '想爸爸')

HELP_REPLY = {'intent': 'help', 'reply': '这件事请告诉老师。', 'options': ['找老师', '继续学习']}
FALLBACK_REPLY = {'intent': 'other', 'reply': '我们一起看提示吧。', 'options': ['看提示', '再试一次', '找老师']}
ECHO_FALLBACK = {'intent': 'echo', 'reply': '请点一个按钮告诉我。', 'options': ['看提示', '再试一次', '休息一下']}
ECHO_INTENT = {'intent': 'echo', 'restated': '学生重复了系统刚说的话', 'confidence': 1.0, 'source': 'rule'}

_PUNCT = re.compile(r'[\s，,。.！!？?、：:；;“”"‘’\'（）()…~～]+')


def _norm(text):
    return _PUNCT.sub('', text or '').lower()


def similarity(a, b):
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def is_echolalia(text, last_bot):
    """整句仿说看相似度；部分仿说（只复述上一句的结尾，至少 3 个字）看后缀。"""
    a, b = _norm(text), _norm(last_bot)
    if not a or not b:
        return False
    if similarity(a, b) >= ECHO_THRESHOLD:
        return True
    return len(a) >= 3 and b.endswith(a)


def apply_vocabulary(text, vocabulary):
    """按个人词表替换自创词（长词优先）。返回 (替换后文本, [(原词, 标准词)])。"""
    out, pairs = text, []
    for item in sorted(vocabulary or [], key=lambda v: len(v.get('word', '')), reverse=True):
        word, meaning = (item.get('word') or '').strip(), (item.get('meaning') or '').strip()
        if word and meaning and word in out:
            out = out.replace(word, meaning)
            pairs.append((word, meaning))
    return out, pairs


def needs_teacher(text):
    return any(w in text for w in HELP_WORDS)


def context_text(task, step_index):
    """当前学习内容的说明（不含答案）。"""
    if task is None:
        return ''
    c = task.content or {}
    if task.layer == 'enlighten':
        return f'卡片闯关：{c.get("title", "")}。{"".join(c.get("story") or [])}'
    steps = c.get('steps') or []
    head = f'任务：{c.get("title", "")}，共 {len(steps)} 步。'
    if step_index is None or not 0 <= step_index < len(steps):
        return head
    st = steps[step_index]
    kind = {'choice': '选择题', 'fill': '填空题', 'order': '排序题', 'code': '自己写代码'}.get(st.get('type'), '')
    return f'{head}现在是第 {step_index + 1} 步（{kind}）：{st.get("prompt", "")}（不要直接说出这一步的答案）'


def _cache_key(user_id, task_id, step, text, echo_of):
    raw = f'{user_id}|{task_id}|{step}|{_norm(text)}|{_norm(echo_of)}'
    return 'star:chat2:' + hashlib.sha1(raw.encode('utf-8')).hexdigest()


def learner_view(lp):
    """画像 → skills 用的学习者视图。称呼用昵称（交给大模型前会被换成 {name}）。"""
    prof = lp.profile or {}
    comm = prof.get('communication') or {}
    return LearnerView(
        name=lp.nickname,
        level=LEVEL_STARTER if lp.layer == 'enlighten' else LEVEL_ENTRY,
        glossary={v['word']: v['meaning'] for v in lp.vocabulary or [] if v.get('word') and v.get('meaning')},
        pronoun_reversal=bool(comm.get('pronoun_reversal')),
        echolalia=bool(comm.get('echolalia')),
        interests=list(prof.get('interests') or []),
    )


def _turns(history):
    """对话记录 → skills 的 Turn 列表（bot 是系统，user 是学生）。"""
    return [Turn('system' if m.get('role') == 'bot' else 'student', m.get('text', ''),
                 options=list(m.get('options') or []) if m.get('role') == 'bot' else [])
            for m in history[-CONTEXT_TURNS:]]


class _PlatformLLM:
    """
    让 skills 走平台自己的大模型封装：先把姓名换成 {name} 再发出去，每次调用照常写进 LLMCallLog
    （用途 P5 意图识别）。skills 自带的 OpenAICompatClient 不做脱敏，所以不用它。
    """

    def __init__(self, names, *, task=None, learner=None):
        self.names, self.task, self.learner = names, task, learner

    def chat_json(self, messages, *, temperature=0.2, max_tokens=512, purpose=''):
        safe = [dict(m, content=llm.redact(m.get('content', ''), self.names)) for m in messages]
        res = llm.chat_json('P5', safe, temperature=temperature, max_tokens=max_tokens,
                            task=self.task, learner=self.learner)
        if res.data is None:
            raise LLMError(res.error or '输出不是合法的 JSON 对象')
        return res.data


def run_rules(lp, text, *, task=None, step=None, history=()):
    """
    skills 流水线的规则部分：分词 → 仿说检测 → 词表映射 → 代词标注（不调大模型）。
    仿说阈值沿用平台原来的 0.8（skills 默认 0.85）。
    意图识别单独做（detect_intent）：同一句话命中缓存时就不必再调一次大模型。
    """
    pipe = InputPipeline(None, disabled={'intent'}, echo_threshold=ECHO_THRESHOLD, use_pinyin=HAS_PINYIN)
    ctx = SkillContext(learner=learner_view(lp), history=_turns(list(history)),
                       step_prompt=context_text(task, step))
    return pipe.run(text, ctx), ctx


def detect_intent(lp, text, ctx, *, task=None):
    """skills 第 5 步意图识别（大模型 P5）；未配置大模型或调用失败时退回关键词规则。"""
    client = None
    if llm.is_configured():
        client = _PlatformLLM([lp.user.username, lp.nickname], task=task, learner=lp.user)
    data = IntentSkill(client)(text, ctx).data
    return {k: data.get(k) for k in ('intent', 'restated', 'confidence', 'source')}


def plain_errors(reply_text, level):
    """字面化检查（skills 第 6 步）里的"错误"级问题，写成可以回填给大模型的句子。"""
    res = check_text(reply_text.replace(llm.NAME_PLACEHOLDER, '名字'), level)
    return [f'"{v["sentence"]}"：{v["detail"]}' for v in res['violations'] if v['severity'] == 'error']


def reply(lp, text, *, task=None, step=None, via='text'):
    """
    返回 {'intent', 'reply', 'options', 'meta': {...}}，并把这一轮记进画像的对话记录。
    via='option' 表示学生点了上一轮的选项按钮——点按钮不算仿说。
    """
    text = (text or '').strip()[:200]
    nickname = lp.nickname
    dialogue = dict(lp.dialogue or {})
    history = list(dialogue.get('assistant') or [])
    last_bot = next((m['text'] for m in reversed(history) if m.get('role') == 'bot'), '')
    meta = {'echolalia': False, 'replaced': [], 'cached': False, 'fallback': False, 'guard': False,
            'intent': None, 'pronoun_hints': [], 'candidates': []}

    if needs_teacher(text):
        out, meta['guard'] = dict(HELP_REPLY), True
    else:
        result, ctx = run_rules(lp, text, task=task, step=step, history=history)
        echo = via != 'option' and bool((result.echo or {}).get('is_echo'))
        meta.update(
            echolalia=echo,
            replaced=[[m['from'], m['to']] for m in result.mappings],
            pronoun_hints=list(ctx.state.get('pronoun_hints') or []),
            candidates=list(result.candidate_words or []),
        )
        key = _cache_key(lp.user_id, task.id if task else 0, step, result.text, last_bot if echo else '')
        hit = cache.get(key)
        if isinstance(hit, dict) and 'out' in hit:
            out, meta['intent'], meta['cached'] = dict(hit['out']), hit.get('intent'), True
        else:
            meta['intent'] = dict(ECHO_INTENT) if echo else detect_intent(lp, text, ctx, task=task)
            if meta['intent'].get('intent') == 'need_help':
                out, meta['guard'] = dict(HELP_REPLY), True
            else:
                out = _ask_model(lp, result, task, step, history, echo, meta)
                meta['fallback'] = out.pop('_fallback', False)
                if not meta['fallback']:
                    cache.set(key, {'out': out, 'intent': meta['intent']}, CACHE_SECONDS)

    out = {k: llm.fill_name(v, nickname) for k, v in out.items()}
    now = timezone.now().isoformat()
    history += [
        {'role': 'user', 'text': text, 'at': now, 'via': via},
        {'role': 'bot', 'text': out['reply'], 'options': out['options'], 'intent': out['intent'],
         'meta': meta, 'at': now},
    ]
    dialogue['assistant'] = history[-HISTORY_KEEP:]
    lp.dialogue = dialogue
    lp.save(update_fields=['dialogue', 'updated_at'])
    return dict(out, meta=meta)


def _ask_model(lp, result, task, step, history, echo, meta):
    """
    系统生成回复（P3）→ 结构校验 + 字面化检查，不合格时把问题回填给模型改一次；仍不合格用兜底回复。
    """
    fallback = dict(ECHO_FALLBACK if echo else FALLBACK_REPLY, _fallback=True)
    if not llm.is_configured():
        return fallback

    names = [lp.user.username, lp.nickname]
    level = LEVEL_STARTER if lp.layer == 'enlighten' else LEVEL_ENTRY
    recent = [{'role': m['role'], 'text': llm.redact(m['text'], names)}
              for m in history[-CONTEXT_TURNS:]]
    comm = (lp.profile or {}).get('communication') or {}
    messages = prompts.p3_messages(
        prompts.profile_summary(lp.profile),
        context_text(task, step),
        recent,
        llm.redact(result.text, names),
        pronoun_note=bool(comm.get('pronoun_reversal')),
        echo_note=echo,
        replaced=[(m['from'], m['to']) for m in result.mappings],
        intent=None if echo else meta['intent'],
        pronoun_hints=[llm.redact(h, names) for h in meta['pronoun_hints']],
        max_len=MAX_SENTENCE_LEN[level],
    )
    for attempt in (1, 2):
        res = llm.chat_json('P3', messages, temperature=0.2, max_tokens=300, attempt=attempt,
                            task=task, learner=lp.user)
        if res.data is None:
            return fallback
        chk = check_reply(res.data)
        if chk.ok:
            chk.rule_errors.extend(plain_errors(res.data['reply'], level))
        llm.mark(res.log, chk)
        if chk.ok:
            return {
                'intent': res.data['intent'],
                'reply': res.data['reply'].strip(),
                'options': [o.strip() for o in res.data['options']],
            }
        meta['plain'] = chk.errors
        if not res.raw:
            break
        messages = messages + [{'role': 'assistant', 'content': res.raw},
                               {'role': 'user', 'content': prompts.refine_message(chk.errors)}]
    return fallback
