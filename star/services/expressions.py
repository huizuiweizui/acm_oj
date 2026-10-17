"""
个人表达记忆的存取（比对逻辑在 star/skills/memory.py）。

条目存在 LearnerProfile.expressions：
    {text, intent, status, votes, hits, learned_at, last_at}
    text    学生的说法（词表映射之后的文本，和比对时用的是同一份）
    status  auto（自动学到）| confirmed（教师确认或手动添加）
    votes   大模型独立给出同一意图的次数
    hits    命中后直接用记忆、没有调大模型的次数

怎么学：大模型识别意图、置信度 ≥ 0.8、意图属于可记忆的几类时记一票；
同一句话两次得到同一意图才生效——一次误判不会被固定下来。教师确认的条目立即生效，
教师可以随时改意图或删除。大模型给出不同意图时，自动条目改成新意图、重新计票。
"""
from django.utils import timezone

from ..skills.memory import MEMORABLE, key_of

LEARN_CONFIDENCE = 0.8
VOTES_TO_ACTIVATE = 2
MAX_ENTRIES = 50
MAX_KEY_LEN = 20       # 太长的句子几乎不会原样再说一遍，不记
LLM_SOURCES = ('llm', 'llm_repaired')


def is_active(e):
    return e.get('status') == 'confirmed' or e.get('votes', 0) >= VOTES_TO_ACTIVATE


def active_entries(lp):
    """给 skills 用的已生效条目。"""
    return [{'text': e['text'], 'intent': e['intent']} for e in lp.expressions or [] if is_active(e)]


def _find(entries, text):
    k = key_of(text)
    return next((e for e in entries if key_of(e.get('text', '')) == k), None)


def _evict(entries):
    """超过上限时先删自动学到、命中少、最久没用到的。"""
    while len(entries) > MAX_ENTRIES:
        autos = [e for e in entries if e.get('status') != 'confirmed'] or entries
        entries.remove(min(autos, key=lambda e: (e.get('hits', 0), e.get('last_at', ''))))


def learn(lp, text, intent):
    """
    根据一次大模型的意图识别结果更新记忆（只改内存里的 lp.expressions，由调用方保存）。
    返回 'new'（新记下）、'vote'（又一致了一次，未生效）、'active'（刚刚生效）、'changed'（改成新意图）或 None。
    """
    if (intent.get('source') not in LLM_SOURCES or intent.get('intent') not in MEMORABLE
            or (intent.get('confidence') or 0) < LEARN_CONFIDENCE):
        return None
    k = key_of(text)
    if not k or len(k) > MAX_KEY_LEN:
        return None
    entries = list(lp.expressions or [])
    now = timezone.now().isoformat()
    e = _find(entries, text)
    if e is None:
        entries.append({'text': text, 'intent': intent['intent'], 'status': 'auto', 'votes': 1, 'hits': 0,
                        'learned_at': now, 'last_at': now})
        event = 'new'
    elif e.get('status') == 'confirmed':
        return None
    elif e['intent'] != intent['intent']:
        e.update(intent=intent['intent'], votes=1, last_at=now)
        event = 'changed'
    else:
        e['votes'] = e.get('votes', 0) + 1
        e['last_at'] = now
        event = 'active' if e['votes'] == VOTES_TO_ACTIVATE else 'vote'
    _evict(entries)
    lp.expressions = entries
    return event


def record_hit(lp, text):
    """命中一次：计数并刷新最近使用时间（只改内存，由调用方保存）。"""
    entries = list(lp.expressions or [])
    e = _find(entries, text)
    if e is not None:
        e['hits'] = e.get('hits', 0) + 1
        e['last_at'] = timezone.now().isoformat()
        lp.expressions = entries


def teacher_update(lp, rows):
    """
    教师在页面上保存整张表：rows = [{text, intent, status}]。
    表里没有的条目视为删除；保留原条目的计票、命中次数和时间；新加的条目直接算教师确认。
    """
    old = list(lp.expressions or [])
    now = timezone.now().isoformat()
    out, seen = [], set()
    for r in rows if isinstance(rows, list) else []:
        text = str((r or {}).get('text', '')).strip()[:30]
        intent = (r or {}).get('intent')
        k = key_of(text)
        if not k or intent not in MEMORABLE or k in seen:
            continue
        seen.add(k)
        prev = _find(old, text)
        e = dict(prev) if prev else {'votes': 0, 'hits': 0, 'learned_at': now, 'status': 'confirmed'}
        if prev and prev['intent'] != intent:
            e['status'] = 'confirmed'   # 教师改了意图，就是教师的判断
        elif r.get('status') == 'confirmed':
            e['status'] = 'confirmed'
        e.update(text=text, intent=intent, last_at=e.get('last_at') or now)
        out.append(e)
    lp.expressions = out[:MAX_ENTRIES]
