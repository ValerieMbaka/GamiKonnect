# Generated migration to rename is_pwd to is_gwds

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_rename_is_pwa_to_is_pwd"),
    ]

    operations = [
        # Rename is_pwd to is_gwds in Gamer model
        migrations.RenameField(
            model_name='gamer',
            old_name='is_pwd',
            new_name='is_gwds',
        ),
        # Rename is_pwd to is_gwds in PendingRegistration model
        migrations.RenameField(
            model_name='pendingregistration',
            old_name='is_pwd',
            new_name='is_gwds',
        ),
        # Update field definition with new help text
        migrations.AlterField(
            model_name='gamer',
            name='is_gwds',
            field=models.BooleanField(
                default=False,
                help_text='If True, indicates the gamer is a Person With Disability (GWDS).',
                verbose_name='Is GWDS',
            ),
        ),
    ]