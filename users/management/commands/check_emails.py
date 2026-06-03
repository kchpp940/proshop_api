from django.core.management.base import BaseCommand
from users.utils import clean_historical_emails, find_duplicate_emails
import json
import sys


class Command(BaseCommand):
    help = 'Read-only check for email normalization status and conflicts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            dest='output_json',
            default=False,
            help='Output results as JSON',
        )

    def handle(self, *args, **options):
        output_json = options['output_json']

        stats = clean_historical_emails()

        if output_json:
            self.stdout.write(json.dumps(stats, indent=2))
            return

        self.stdout.write(self.style.HEADER('=== Email Normalization Status ==='))
        self.stdout.write(f'Total users: {stats["total_users"]}')
        self.stdout.write(self.style.SUCCESS(f'Already normalized: {stats["already_normalized"]}'))
        self.stdout.write(f'Needs normalization: {stats["needs_normalization"]}')
        self.stdout.write(self.style.WARNING(f'Conflicts found: {stats["conflicts_found"]}'))

        if stats['to_normalize']:
            self.stdout.write('\n' + self.style.MIGRATE_HEADING('Users needing normalization:'))
            for item in stats['to_normalize']:
                self.stdout.write(
                    f'  User {item["user_id"]}: "{item["from"]}" -> "{item["to"]}"'
                )

        if stats['conflicts']:
            self.stdout.write('\n' + self.style.ERROR('CONFLICTS DETECTED:'))
            self.stdout.write(self.style.ERROR('These must be resolved manually before deployment.'))
            for conflict in stats['conflicts']:
                self.stdout.write(f'\n  Normalized: {conflict["normalized_email"]}')
                self.stdout.write(f'  Affected users:')
                for user_info in conflict['users']:
                    flags = []
                    if user_info['is_active']:
                        flags.append('active')
                    if user_info['is_staff']:
                        flags.append('staff')
                    flag_str = f' [{", ".join(flags)}]' if flags else ''
                    self.stdout.write(
                        f'    - User {user_info["user_id"]}: '
                        f'"{user_info["original_email"]}"{flag_str}'
                    )

            self.stdout.write('\n' + self.style.ERROR(
                'Migration will be blocked until conflicts are resolved.'
            ))
            self.stdout.write(
                'For each conflict group, decide which account to keep and update the others '
                'with different email addresses.'
            )
            sys.exit(1)

        if stats['needs_normalization'] == 0 and stats['conflicts_found'] == 0:
            self.stdout.write('\n' + self.style.SUCCESS('All emails are properly normalized. No conflicts found.'))

        if stats['needs_normalization'] > 0 and stats['conflicts_found'] == 0:
            self.stdout.write(
                '\n' + self.style.SUCCESS(
                    'No conflicts found. These users will be automatically normalized '
                    'when migration 0003 is applied.'
                )
            )
