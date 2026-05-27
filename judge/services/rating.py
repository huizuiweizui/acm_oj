from django.db.models import F

from ..models import UserProfile

_DIFFICULTY_RATING = {
    '入门': 5,
    '普及-': 8,
    '普及/提高-': 12,
    '普及+/提高': 18,
    '提高+/省选-': 25,
    '省选/NOI-': 35,
    'NOI/NOI+/CTSC': 50,
    '暂无评定': 10,
}


def _update_rating(user, problem):
    """首次 AC 某题时按难度增加 rating。"""
    delta = _DIFFICULTY_RATING.get(problem.difficulty, 10)
    UserProfile.objects.filter(user=user).update(rating=F('rating') + delta)
