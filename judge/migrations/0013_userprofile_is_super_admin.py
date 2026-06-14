from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0012_assignment_announcement'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_super_admin',
            field=models.BooleanField(default=False, verbose_name='总管理员'),
        ),
    ]
