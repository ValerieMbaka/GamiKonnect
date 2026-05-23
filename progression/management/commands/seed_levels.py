from django.core.management.base import BaseCommand
from progression.models import Level

class Command(BaseCommand):
    help = 'Seeds the database with GamiKonnect Hybrid XP Levels'

    def handle(self, *args, **kwargs):
        # The Hybrid Curve (Metals -> Prestige)
        levels_data = [
            {'order': 1, 'name': 'Amateur', 'min_xp': 0, 'color_hex': '#A19D94'},
            {'order': 2, 'name': 'Bronze', 'min_xp': 500, 'color_hex': '#CD7F32'},
            {'order': 3, 'name': 'Silver', 'min_xp': 2000, 'color_hex': '#C0C0C0'},
            {'order': 4, 'name': 'Gold', 'min_xp': 5000, 'color_hex': '#FFD700'},
            {'order': 5, 'name': 'Platinum', 'min_xp': 15000, 'color_hex': '#35A8F0'},
            {'order': 6, 'name': 'Diamond', 'min_xp': 35000, 'color_hex': '#00FFFF'},
            {'order': 7, 'name': 'Master', 'min_xp': 75000, 'color_hex': '#9B59B6'},
            {'order': 8, 'name': 'Grandmaster', 'min_xp': 150000, 'color_hex': '#EF4444'},
            {'order': 9, 'name': 'Legend', 'min_xp': 300000, 'color_hex': '#FF007F'},
            {'order': 10, 'name': 'Titan', 'min_xp': 500000, 'color_hex': '#FACC15'},
        ]

        self.stdout.write(self.style.WARNING('Updating Level Tiers...'))

        count = 0
        for data in levels_data:
            # Overwrites the existing levels based on their 'order' (1 through 10)
            obj, created = Level.objects.update_or_create(
                order=data['order'],
                defaults={
                    'name': data['name'],
                    'min_xp': data['min_xp'],
                    'color_hex': data['color_hex']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: [Rank {obj.order}] {obj.name}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Updated: [Rank {obj.order}] {obj.name} ({obj.min_xp} XP)"))
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} Hybrid Levels! 🏆'))