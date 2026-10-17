"""录屏前把演示库恢复到干净状态（只动演示库副本）。

    cd D:/acm/acm_oj_star && DB_ENGINE=sqlite DB_NAME=<demo.sqlite3> PYTHONPATH=. python <本文件>
"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acm_oj.settings')
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.core.management import call_command  # noqa: E402

from star.models import LearnerProfile  # noqa: E402

call_command('seed_star', no_verify=True, reset_tasks=True)
for lp in LearnerProfile.objects.filter(user__username__in=['star_yu', 'star_hang']):
    lp.dialogue = {k: v for k, v in (lp.dialogue or {}).items() if k != 'assistant'}
    lp.expressions = []
    lp.save(update_fields=['dialogue', 'expressions', 'updated_at'])
LearnerProfile.objects.filter(user__username='star_newbie').delete()
print('reset ok; newbie exists:', User.objects.filter(username='star_newbie').exists())
