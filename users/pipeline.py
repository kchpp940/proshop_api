from django.contrib.auth import get_user_model
from .utils import normalize_email, get_user_by_email, EmailConflictError

User = get_user_model()


def normalize_email_pipeline(strategy, details, backend, user=None, *args, **kwargs):
    email = details.get('email')
    if not email:
        return {}

    normalized_email = normalize_email(email)
    details['email'] = normalized_email
    details['username'] = normalized_email

    return {'details': details}


def associate_by_normalized_email(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        return {}

    email = details.get('email')
    if not email:
        return {}

    normalized_email = normalize_email(email)
    existing_user = get_user_by_email(normalized_email)

    if existing_user is not None:
        social = backend.strategy.storage.user.get_social_auth_for_user(
            existing_user, backend.name
        )
        if social.exists():
            return {'user': existing_user, 'is_new': False}

        raise EmailConflictError(
            detail='An account with this email already exists. '
                   'Please log in with your existing account first, '
                   'then connect your Google account from settings.'
        )

    return {}
