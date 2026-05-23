from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_gamer_is_pwa'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingregistration',
            name='is_pwa',
            field=models.BooleanField(default=False),
        ),
    ]