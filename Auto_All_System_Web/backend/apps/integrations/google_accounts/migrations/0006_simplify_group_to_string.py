# Generated migration for simplifying group from ForeignKey to string field

from django.db import migrations, models


def migrate_group_to_string(apps, schema_editor):
    """
    将 group 外键的名称迁移到 group_name 字符串字段
    """
    GoogleAccount = apps.get_model('google_accounts', 'GoogleAccount')
    for account in GoogleAccount.objects.select_related('group').all():
        if account.group:
            account.group_name = account.group.name
            account.save(update_fields=['group_name'])


def reverse_migration(apps, schema_editor):
    """
    反向迁移（不做任何操作，因为无法恢复外键关系）
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('google_accounts', '0005_rename_account_gro_owner_u_a1b2c3_idx_account_gro_owner_u_b1cba0_idx'),
    ]

    operations = [
        # 1. 添加新的 group_name 字符串字段
        migrations.AddField(
            model_name='googleaccount',
            name='group_name',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='账号分组名称，如：售后、2FA等',
                max_length=100,
                verbose_name='分组名称'
            ),
        ),
        # 2. 迁移数据：将 group 外键的名称复制到 group_name
        migrations.RunPython(migrate_group_to_string, reverse_migration),
        # 3. 移除 group 外键字段
        migrations.RemoveField(
            model_name='googleaccount',
            name='group',
        ),
        # 4. 删除 AccountGroup 模型
        migrations.DeleteModel(
            name='AccountGroup',
        ),
    ]
