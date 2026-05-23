from django.core.management.base import BaseCommand
from progression.models import Achievement


class Command(BaseCommand):
    help = 'Seeds the database with GamiKonnect Progression Achievements'

    def handle(self, *args, **kwargs):
        achievements_data = [
            # --- COMMUNITY & SOCIAL ---
            {'name': 'The Scout', 'desc': 'Join 3 Communities.', 'cat': 'COMMUNITY', 'metric': 'communities_joined', 'target': 3, 'xp': 100},
            {'name': 'The Emissary', 'desc': 'Join 5 Communities.', 'cat': 'COMMUNITY', 'metric': 'communities_joined', 'target': 5, 'xp': 250},
            {'name': 'The Ambassador', 'desc': 'Join 25 Communities.', 'cat': 'COMMUNITY', 'metric': 'communities_joined', 'target': 25, 'xp': 1000},
            {'name': 'The Critic', 'desc': 'Comment on 10 different gamers posts.', 'cat': 'SOCIAL', 'metric': 'comments_made', 'target': 10, 'xp': 150},
            {'name': 'The Orator', 'desc': 'Comment on 50 different gamers posts.', 'cat': 'SOCIAL', 'metric': 'comments_made', 'target': 50, 'xp': 500},
            {'name': 'Voice of the People', 'desc': 'Comment on 100 different gamers posts.', 'cat': 'SOCIAL', 'metric': 'comments_made', 'target': 100, 'xp': 1500},

            # --- CONTENT CREATION (ANTI-SPAM) ---
            {'name': 'Paparazzi', 'desc': 'Make 5 Posts.', 'cat': 'CONTENT', 'metric': 'posts_made', 'target': 5, 'xp': 100},
            {'name': 'Rising Star', 'desc': 'Make 20 Posts (with at least 10 likes each).', 'cat': 'CONTENT', 'metric': 'posts_with_10_likes', 'target': 20, 'xp': 500},
            {'name': 'Trend Setter', 'desc': 'Make 50 Posts (with at least 25 likes each).', 'cat': 'CONTENT', 'metric': 'posts_with_25_likes', 'target': 50, 'xp': 1500},
            {'name': 'Platform Icon', 'desc': 'Make 100 Posts (with at least 75 likes each).', 'cat': 'CONTENT', 'metric': 'posts_with_75_likes', 'target': 100, 'xp': 5000},

            # --- COMPETITIONS (PARTICIPATION) ---
            {'name': 'Challenger', 'desc': 'Join 5 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_joined', 'target': 5, 'xp': 200},
            {'name': 'Contender', 'desc': 'Join 10 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_joined', 'target': 10, 'xp': 500},
            {'name': 'Gladiator', 'desc': 'Join 25 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_joined', 'target': 25, 'xp': 1200},
            {'name': 'Veteran', 'desc': 'Join 50 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_joined', 'target': 50, 'xp': 3000},
            {'name': 'Centurion', 'desc': 'Join 100 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_joined', 'target': 100, 'xp': 7500},

            # --- COMPETITIONS (VICTORY) ---
            {'name': 'First Blood', 'desc': 'Win 1 Competition.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 1, 'xp': 500},
            {'name': 'Warlord', 'desc': 'Win 5 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 5, 'xp': 1500},
            {'name': 'Conqueror', 'desc': 'Win 10 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 10, 'xp': 3500},
            {'name': 'Grand Champion', 'desc': 'Win 25 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 25, 'xp': 8000},
            {'name': 'Esports Legend', 'desc': 'Win 50 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 50, 'xp': 15000},
            {'name': 'Unstoppable Force', 'desc': 'Win 100 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 100, 'xp': 35000},
            {'name': 'Hall of Fame', 'desc': 'Win 200 Competitions.', 'cat': 'COMPETITION', 'metric': 'competitions_won', 'target': 200, 'xp': 100000},

            # --- LEAGUES / TOURNAMENTS ---
            {'name': 'Draft Pick', 'desc': 'Join your first Community League.', 'cat': 'LEAGUE', 'metric': 'leagues_joined', 'target': 1, 'xp': 300},
            {'name': 'Franchise Player', 'desc': 'Join 10 Community Leagues.', 'cat': 'LEAGUE', 'metric': 'leagues_joined', 'target': 10, 'xp': 1000},
            {'name': 'League MVP', 'desc': 'Win your first Community League.', 'cat': 'LEAGUE', 'metric': 'leagues_won', 'target': 1, 'xp': 2000},
            {'name': 'Dynasty', 'desc': 'Win 5 Community Leagues.', 'cat': 'LEAGUE', 'metric': 'leagues_won', 'target': 5, 'xp': 10000},
        ]

        self.stdout.write(self.style.WARNING('Starting Achievement Seeding...'))

        count = 0
        for data in achievements_data:
            obj, created = Achievement.objects.update_or_create(
                name=data['name'],
                defaults={
                    'description': data['desc'],
                    'category': data['cat'],
                    'metric_key': data['metric'],
                    'target_value': data['target'],
                    'xp_reward': data['xp']
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {obj.name}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Updated: {obj.name}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded/updated {count} achievements! 🎮'))
