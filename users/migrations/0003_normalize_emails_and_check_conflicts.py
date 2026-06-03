from django.db import migrations
from django.core.exceptions import ValidationError


def normalize_email(email):
    if not email:
        return ''
    return email.strip().lower()


def check_email_conflicts_and_normalize(apps, schema_editor):
    UserAccount = apps.get_model('users', 'UserAccount')

    email_to_users = {}
    needs_normalization = []

    for user in UserAccount.objects.all().order_by('id'):
        original_email = user.email
        normalized_email = normalize_email(original_email)

        if original_email != normalized_email:
            needs_normalization.append((user, original_email, normalized_email))

        if normalized_email not in email_to_users:
            email_to_users[normalized_email] = []
        email_to_users[normalized_email].append((user, original_email))

    conflicts = []
    for normalized_email, user_entries in email_to_users.items():
        if len(user_entries) > 1:
            conflict_users = []
            for u, orig in user_entries:
                flags = []
                if u.is_active:
                    flags.append('active')
                if u.is_staff:
                    flags.append('staff')
                flag_str = f" [{', '.join(flags)}]" if flags else ''
                conflict_users.append(f"User {u.id}: {orig}{flag_str}")
            conflicts.append(
                f"  - {normalized_email}: {'; '.join(conflict_users)}"
            )

    if conflicts:
        conflict_msg = '\n'.join(conflicts)
        raise ValidationError(
            f"Email conflicts detected after normalization. "
            f"Please resolve these conflicts manually before deploying:\n"
            f"{conflict_msg}\n\n"
            f"Run 'python manage.py check_emails' for a detailed report."
        )

    for user, original_email, normalized_email in needs_normalization:
        user.email = normalized_email
        user.save(update_fields=['email'])


def reverse_normalize(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_useraccount_dob_useraccount_gender"),
    ]

    operations = [
        migrations.RunPython(
            check_email_conflicts_and_normalize,
            reverse_code=reverse_normalize,
        ),
    ]
