# Generated migration to rename is_pwa to is_pwd and update help text

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_pendingregistration_is_pwa"),
    ]

    operations = [
        # Rename is_pwa to is_pwd in Gamer model
        migrations.RenameField(
            model_name='gamer',
            old_name='is_pwa',
            new_name='is_pwd',
        ),
        # Rename is_pwa to is_pwd in PendingRegistration model
        migrations.RenameField(
            model_name='pendingregistration',
            old_name='is_pwa',
            new_name='is_pwd',
        ),
        # Update field definition with new help text
        migrations.AlterField(
            model_name='gamer',
            name='is_pwd',
            field=models.BooleanField(
                default=False,
                help_text='If True, indicates the gamer is a Person With Disability.',
                verbose_name='Is PWD',
            ),
        ),
    ]
