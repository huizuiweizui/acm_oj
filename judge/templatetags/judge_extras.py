"""自定义模板标签"""
from django import template
register = template.Library()

@register.filter
def status_class(status):
    """返回评测状态对应的 CSS 类"""
    mapping = {
        'AC': 'status-ac',
        'WA': 'status-wa',
        'TLE': 'status-tle',
        'MLE': 'status-mle',
        'RE': 'status-re',
        'CE': 'status-ce',
        'Pending': 'status-pending',
        'Judging': 'status-judging',
    }
    return mapping.get(status, 'status-pending')

@register.filter
def difficulty_class(difficulty):
    mapping = {
        '暂无评定':     'diff-0',
        '入门':         'diff-1',
        '普及-':        'diff-2',
        '普及/提高-':   'diff-3',
        '普及+/提高':   'diff-4',
        '提高+/省选-':  'diff-5',
        '省选/NOI-':    'diff-6',
        'NOI/NOI+/CTSC':'diff-7',
    }
    return mapping.get(difficulty, 'diff-0')

@register.filter
def contest_status_class(status):
    mapping = {'running': 'contest-running', 'upcoming': 'contest-upcoming', 'ended': 'contest-ended'}
    return mapping.get(status, '')
