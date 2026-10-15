"""
对话助手：学生输入先经过沟通特征处理，再交给大模型（P3），回复固定为"一句话 + 选项"。

处理顺序：
    1. 求助护栏（确定性）：说到疼、害怕、被欺负等，不经大模型，固定回复"请告诉老师"；
    2. 仿说检测：与系统上一句的文本相似度（difflib）≥ 0.8，或原样复述上一句的结尾，
       判为仿说——不把它当成新内容理解，而是请模型换一种更简单的问法重问；
    3. 自创词替换：按个人词表把学生的说法换成标准说法，再交给模型；
    4. 代词：画像标记了代词逆转时，在提示词里说明理解方式（只用于理解，不纠正）；
    5. 一致性：温度 0.2；同一学生在同一步骤问同一句话，直接返回缓存的回答（初版为文本完全匹配）。

大模型不可用或回复不合格时，返回固定的兜底回复——学生端永远拿到同样结构的回复。
"""
import difflib
import hashlib
import re

from django.core.cache import cache
from django.utils import timezone

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
    kind = {'choice': '选择题', 'fill': '填空题', 'order': '排序题'}.get(st.get('type'), '')
    return f'{head}现在是第 {step_index + 1} 步（{kind}）：{st.get("prompt", "")}（不要直接说出这一步的答案）'


def _cache_key(user_id, task_id, step, text, echo_of):
    raw = f'{user_id}|{task_id}|{step}|{_norm(text)}|{_norm(echo_of)}'
    return 'star:chat:' + hashlib.sha1(raw.encode('utf-8')).hexdigest()


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
    meta = {'echolalia': False, 'replaced': [], 'cached': False, 'fallback': False, 'guard': False}

    if needs_teacher(text):
        out, meta['guard'] = dict(HELP_REPLY), True
    else:
        echo = via != 'option' and is_echolalia(text, last_bot)
        meta['echolalia'] = echo
        replaced_text, pairs = apply_vocabulary(text, lp.vocabulary)
        meta['replaced'] = [list(p) for p in pairs]

        key = _cache_key(lp.user_id, task.id if task else 0, step, replaced_text, last_bot if echo else '')
        out = cache.get(key)
        if out is not None:
            meta['cached'] = True
        else:
            out = _ask_model(lp, replaced_text, task, step, history, echo, pairs)
            meta['fallback'] = out.pop('_fallback', False)
            if not meta['fallback']:
                cache.set(key, out, CACHE_SECONDS)

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


def _ask_model(lp, text, task, step, history, echo, pairs):
    if not llm.is_configured():
        return dict(ECHO_FALLBACK if echo else FALLBACK_REPLY, _fallback=True)

    names = [lp.user.username, lp.nickname]
    recent = [{'role': m['role'], 'text': llm.redact(m['text'], names)}
              for m in history[-CONTEXT_TURNS:]]
    comm = (lp.profile or {}).get('communication') or {}
    messages = prompts.p3_messages(
        prompts.profile_summary(lp.profile),
        context_text(task, step),
        recent,
        llm.redact(text, names),
        pronoun_note=bool(comm.get('pronoun_reversal')),
        echo_note=echo,
        replaced=pairs,
    )
    res = llm.chat_json('P3', messages, temperature=0.2, max_tokens=300,
                        task=task, learner=lp.user)
    if res.data is None:
        return dict(ECHO_FALLBACK if echo else FALLBACK_REPLY, _fallback=True)
    chk = check_reply(res.data)
    llm.mark(res.log, chk)
    if not chk.ok:
        return dict(ECHO_FALLBACK if echo else FALLBACK_REPLY, _fallback=True)
    return {
        'intent': res.data['intent'],
        'reply': res.data['reply'].strip(),
        'options': [o.strip() for o in res.data['options']],
    }
