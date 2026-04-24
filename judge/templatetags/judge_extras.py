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
    mapping = {'Easy': 'diff-easy', 'Medium': 'diff-medium', 'Hard': 'diff-hard'}
    return mapping.get(difficulty, '')

@register.filter
def contest_status_class(status):
    mapping = {'running': 'contest-running', 'upcoming': 'contest-upcoming', 'ended': 'contest-ended'}
    return mapping.get(status, '')
