from .auth import index, login_view, logout_view, register_view
from .contest import (
    contest_create, contest_detail, contest_list, contest_ranking, contest_register,
)
from .discussion import (
    create_discussion, create_discussion_general, discussion_detail, discussion_list,
)
from .problem import api_problems, custom_run, problem_detail, problem_list, submit_code
from .submission import submission_detail, submission_list
from .user import leaderboard, my_profile, profile_view
from ..services.judger import judge_submission

__all__ = [
    'index', 'register_view', 'login_view', 'logout_view',
    'problem_list', 'problem_detail', 'submit_code', 'custom_run', 'api_problems',
    'submission_list', 'submission_detail',
    'contest_list', 'contest_detail', 'contest_register', 'contest_ranking', 'contest_create',
    'discussion_list', 'discussion_detail', 'create_discussion', 'create_discussion_general',
    'leaderboard', 'profile_view', 'my_profile',
    'judge_submission',
]
