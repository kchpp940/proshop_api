from .services import (
    normalize_email,
    get_account_by_email,
    check_account_active,
    AccountServiceError,
)


def associate_by_email_normalized(backend, details, user=None, *args, **kwargs):
    """
    Associate current auth with a user with the same email address in the DB.
    Uses our account service for email normalization and lookup.

    This pipeline entry is not 100% secure unless you know that the providers
    enabled enforce email verification on their side, otherwise a user can
    attempt to take over another user account by using the same (not validated)
    email address on some provider.
    """
    if user:
        return None

    email = details.get("email")
    if email:
        try:
            user = get_account_by_email(email, include_inactive=True)
            return {"user": user, "is_new": False}
        except AccountServiceError:
            return None


def check_user_active(backend, user, is_new=False, *args, **kwargs):
    """
    Check if the user account is active before allowing login.
    """
    if user and not is_new:
        check_account_active(user)


def normalize_user_email(backend, details, user=None, *args, **kwargs):
    """
    Normalize the email address in details before user creation or lookup.
    """
    email = details.get("email")
    if email:
        details["email"] = normalize_email(email)
    return {"details": details}
