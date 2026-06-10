from django.db import migrations, models


def migrate_user_role(apps, schema_editor):
    """将所有 role='user' 的旧记录迁移为 'student'"""
    UserProfile = apps.get_model('judge', 'UserProfile')
    UserProfile.objects.filter(role='user').update(role='student')


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0008_add_rag_models'),
    ]

    operations = [
        # 1. 先加新字段（允许 blank，不影响现有数据）
        migrations.AddField(
            model_name='userprofile',
            name='student_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=30, verbose_name='学号'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='real_name',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='真实姓名'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='major',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='专业'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='grade',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='年级'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='must_change_password',
            field=models.BooleanField(default=False, verbose_name='首次登录需改密'),
        ),
        # 2. 数据迁移：user → student
        migrations.RunPython(migrate_user_role, migrations.RunPython.noop),
        # 3. 更新 role 字段的 choices 和 default
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('student', '学生'),
                    ('teacher', '教师'),
                    ('admin', '管理员'),
                ],
                default='student',
                max_length=10,
                verbose_name='角色',
            ),
        ),
    ]
