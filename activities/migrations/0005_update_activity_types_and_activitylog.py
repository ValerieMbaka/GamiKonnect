# Generated migration for Activity model updates and ActivityLog gamer field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("activities", "0004_achievement_level_alter_activitylog_description_and_more"),
    ]

    operations = [
        # Update Activity model choices to include new activity types
        migrations.AlterField(
            model_name='activity',
            name='activity_type',
            field=models.CharField(
                choices=[
                    ('level_up', 'Level Up'),
                    ('achievement_earned', 'Achievement Earned'),
                    ('profile_completed', 'Profile Completed'),
                    ('profile_updated', 'Profile Updated'),
                    ('game_added', 'Game Added'),
                    ('game_removed', 'Game Removed'),
                    ('competition_registered', 'Registered for Competition'),
                    ('competition_checkedin', 'Checked In to Competition'),
                    ('competition_completed', 'Competed in Tournament'),
                    ('competition_won', 'Won Competition'),
                    ('login', 'Logged In'),
                    ('logout', 'Logged Out'),
                    ('system', 'System Event'),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
        # Add db_index to timestamp field if not already indexed
        migrations.AlterField(
            model_name='activity',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        # Add gamer field to ActivityLog for easier filtering
        migrations.AddField(
            model_name='activitylog',
            name='gamer',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='activity_logs',
                to='accounts.gamer',
                help_text="Link to gamer for easier filtering of user-specific system events"
            ),
        ),
        # Add indexes for performance
        migrations.AddIndex(
            model_name='activity',
            index=models.Index(fields=['gamer', '-timestamp'], name='activities__gamer_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='activity',
            index=models.Index(fields=['activity_type', '-timestamp'], name='activities__type_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='activitylog',
            index=models.Index(fields=['gamer', '-timestamp'], name='activitylog_gamer_timestamp_idx'),
        ),
    ]
