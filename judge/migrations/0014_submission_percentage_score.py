from django.db import migrations, models


def ensure_score_column(apps, schema_editor):
    submission = apps.get_model('judge', 'Submission')
    table = submission._meta.db_table
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table)
    score = next((col for col in columns if col.name == 'score'), None)
    if score is None:
        schema_editor.add_field(submission, submission._meta.get_field('score'))
    elif connection.vendor == 'mysql' and str(score.default) != '0':
        # The shared MySQL dump already contains a NOT NULL score without a default.
        schema_editor.execute('ALTER TABLE judge_submission ALTER COLUMN score SET DEFAULT 0')


def backfill_scores(apps, schema_editor):
    submission = apps.get_model('judge', 'Submission')
    unscored = submission.objects.using(schema_editor.connection.alias).filter(score=0)
    unscored.filter(status='AC').update(score=100)
    failures = unscored.filter(status__in=['WA', 'TLE', 'MLE', 'RE'])
    for pk, results in failures.values_list('pk', 'test_results').order_by('pk').iterator():
        if isinstance(results, list) and results:
            passed = sum(isinstance(case, dict) and case.get('status') == 'AC' for case in results)
            score = 100 * passed // len(results)
            if score:
                failures.filter(pk=pk, test_results=results).update(score=score)


class Migration(migrations.Migration):
    dependencies = [('judge', '0013_userprofile_is_super_admin')]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.AddField(
                model_name='submission',
                name='score',
                field=models.IntegerField('得分', default=0, db_default=0),
            ),
        ]),
        # Keep the column and its default on rollback so older branches can still submit.
        migrations.RunPython(ensure_score_column, migrations.RunPython.noop, atomic=False),
        migrations.RunPython(backfill_scores, migrations.RunPython.noop),
    ]
