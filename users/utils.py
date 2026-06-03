from typing import Optional, Tuple, List, Dict
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

User = get_user_model()


class EmailConflictError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A user with this email already exists'
    default_code = 'email_conflict'


class AccountNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'There is no account for this email address'
    default_code = 'account_not_found'


class InvalidPasswordError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Your password is incorrect'
    default_code = 'invalid_password'


class AccountInactiveError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Your account is not activated'
    default_code = 'account_inactive'


class InvalidActivationLinkError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid activation link'
    default_code = 'invalid_activation_link'


class AlreadyActivatedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Your account is already activated'
    default_code = 'already_activated'


class InvalidTokenError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Your token is incorrect'
    default_code = 'invalid_token'


def normalize_email(email: str) -> str:
    if not email:
        return ''
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[User]:
    normalized_email = normalize_email(email)
    if not normalized_email:
        return None
    try:
        return User.objects.get(email=normalized_email)
    except User.DoesNotExist:
        return None


def check_email_availability(email: str, exclude_user_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    normalized_email = normalize_email(email)
    if not normalized_email:
        return False, 'Email is required'

    query = User.objects.filter(email=normalized_email)
    if exclude_user_id is not None:
        query = query.exclude(id=exclude_user_id)

    if query.exists():
        return False, 'A user with this email already exists'

    return True, None


def validate_email_for_registration(email: str) -> None:
    normalized_email = normalize_email(email)
    if not normalized_email:
        raise ValidationError(_('Email is required'))

    is_available, error_msg = check_email_availability(normalized_email)
    if not is_available:
        raise EmailConflictError(detail=error_msg)


def find_duplicate_emails() -> List[Dict]:
    from django.db.models import Count

    duplicates = User.objects.values('email') \
        .annotate(email_count=Count('email')) \
        .filter(email_count__gt=1)

    result = []
    for dup in duplicates:
        users = User.objects.filter(email=dup['email']).order_by('date_joined', 'id')
        result.append({
            'email': dup['email'],
            'count': dup['email_count'],
            'user_ids': list(users.values_list('id', flat=True)),
        })
    return result


def clean_historical_emails() -> Dict:
    stats = {
        'total_users': 0,
        'needs_normalization': 0,
        'conflicts_found': 0,
        'already_normalized': 0,
        'conflicts': [],
        'to_normalize': [],
    }

    all_users = User.objects.all()
    stats['total_users'] = all_users.count()

    email_to_users: Dict[str, List[User]] = {}

    for user in all_users:
        original_email = user.email
        normalized_email = normalize_email(original_email)

        if original_email == normalized_email:
            stats['already_normalized'] += 1
            continue

        if normalized_email not in email_to_users:
            email_to_users[normalized_email] = []
        email_to_users[normalized_email].append((user, original_email))

    for normalized_email, user_entries in email_to_users.items():
        if len(user_entries) > 1:
            stats['conflicts_found'] += 1
            conflict_info = {
                'normalized_email': normalized_email,
                'users': [
                    {
                        'user_id': u.id,
                        'original_email': orig,
                        'is_active': u.is_active,
                        'is_staff': u.is_staff,
                    }
                    for u, orig in user_entries
                ],
            }
            stats['conflicts'].append(conflict_info)
        else:
            user, original_email = user_entries[0]
            stats['to_normalize'].append({
                'user_id': user.id,
                'from': original_email,
                'to': normalized_email,
            })
            stats['needs_normalization'] += 1

    return stats
