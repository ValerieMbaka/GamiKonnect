from django.db import migrations, models


def forwards(apps, schema_editor):
    Competition = apps.get_model('competitions', 'Competition')

    Competition.objects.filter(status='pending_review').update(status='pending')
    Competition.objects.filter(status__in=['approved', 'registration_open', 'registration_closed']).update(status='registration')
    Competition.objects.filter(status__in=['checkin_submitted', 'results_pending', 'results_submitted', 'pending_prize_verification']).update(status='ongoing')


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0008_alter_competition_status'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='competition',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('pending', 'Pending'),
                    ('rejected', 'Rejected'),
                    ('registration', 'Registration'),
                    ('ongoing', 'Ongoing'),
                    ('completed', 'Completed'),
                ],
                db_index=True,
                default='draft',
                max_length=30,
            ),
        ),
    ]