from django.core.management.base import BaseCommand

from accounts.models import Account, PendingRegistration


class Command(BaseCommand):
    help = "List pending registrations whose email or phone conflicts with an existing account."

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            choices=['gamer', 'shop_owner'],
            help='Only show conflicts for a specific pending role.',
        )

    def handle(self, *args, **options):
        queryset = PendingRegistration.objects.all().order_by('created_at')
        role = options.get('role')
        if role:
            queryset = queryset.filter(role=role)

        conflicts = []
        for pending in queryset:
            email_match = Account.objects.filter(email__iexact=pending.email).exclude(uid=pending.uid).first()
            phone_match = Account.objects.filter(phone=pending.phone).exclude(uid=pending.uid).first()

            if email_match or phone_match:
                conflicts.append((pending, email_match, phone_match))

        if not conflicts:
            self.stdout.write(self.style.SUCCESS('No pending registration conflicts found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {len(conflicts)} conflicting pending registration(s):'))
        for pending, email_match, phone_match in conflicts:
            self.stdout.write(
                f'- Pending uid={pending.uid} email={pending.email} phone={pending.phone} role={pending.role}'
            )
            if email_match:
                self.stdout.write(
                    f'  email conflict -> Account uid={email_match.uid} email={email_match.email} phone={email_match.phone}'
                )
            if phone_match:
                self.stdout.write(
                    f'  phone conflict -> Account uid={phone_match.uid} email={phone_match.email} phone={phone_match.phone}'
                )