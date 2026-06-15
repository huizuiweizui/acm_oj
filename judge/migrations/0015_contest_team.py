from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0014_dailycheckin'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='team',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='contests',
                to='judge.team',
                verbose_name='所属团队',
            ),
        ),
    ]
