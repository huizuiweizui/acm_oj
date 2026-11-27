from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from .models import Problem, Submission


@skipUnless(connection.vendor == 'mysql', 'Exercises the imported MySQL schema')
class SubmissionScoreMigrationTests(TransactionTestCase):
    def test_imported_score_column_and_historical_submissions(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [('judge', '0013_userprofile_is_super_admin')]
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        executor.migrate(previous)
        old_submission = executor.loader.project_state(previous).apps.get_model('judge', 'Submission')

        # Recreate the dump's required column without a database default.
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE judge_submission ALTER COLUMN score DROP DEFAULT')
        user = get_user_model().objects.create_user(username='score-test')
        problem = Problem.objects.create(title='Score test')
        fields = dict(user_id=user.pk, problem_id=problem.pk, language='Python', code='pass')
        cases = [{'status': 'AC'}, {'status': 'WA'}, {'status': 'AC'}]
        partial = Submission.objects.create(**fields, status='WA', test_results=cases, score=0)
        saved = Submission.objects.create(**fields, status='WA', test_results=cases, score=73)
        accepted = Submission.objects.create(**fields, status='AC', score=0)

        MigrationExecutor(connection).migrate(latest)
        pending = old_submission.objects.create(**fields)
        for record, expected in [(partial, 66), (saved, 73), (accepted, 100), (pending, 0)]:
            with self.subTest(submission=record.pk):
                self.assertEqual(Submission.objects.get(pk=record.pk).score, expected)
