from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

from rest_framework import status
from rest_framework.exceptions import APIException


User = get_user_model()


class AccountErrorCodes:
    ACCOUNT_NOT_FOUND = 'account_not_found'
    ACCOUNT_INACTIVE = 'account_inactive'
    ACCOUNT_ALREADY_ACTIVE = 'account_already_active'
    INVALID_CREDENTIALS = 'invalid_credentials'
    INVALID_TOKEN = 'invalid_token'
    INVALID_LINK = 'invalid_link'
    EMAIL_ALREADY_EXISTS = 'email_already_exists'


class AccountAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Account error'
    default_code = 'account_error'

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=detail, code=code)


class AccountServiceError(AccountAPIException):
    def __init__(self, detail=None, code=None, status_code=None):
        super().__init__(detail=detail, code=code, status_code=status_code)


def normalize_email(email):
    email = email or ''
    return email.strip().lower()


def get_account_by_email(email, include_inactive=True):
    normalized_email = normalize_email(email)
    try:
        queryset = User.objects
        if include_inactive:
            user = queryset.get(email=normalized_email)
        else:
            user = queryset.get(email=normalized_email, is_active=True)
        return user
    except User.DoesNotExist:
        raise AccountServiceError(
            detail='There is no account for this email address',
            code=AccountErrorCodes.ACCOUNT_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND
        )


def get_account_by_id(user_id, include_inactive=True):
    try:
        queryset = User.objects
        if include_inactive:
            user = queryset.get(pk=user_id)
        else:
            user = queryset.get(pk=user_id, is_active=True)
        return user
    except User.DoesNotExist:
        raise AccountServiceError(
            detail='There is no account with this ID',
            code=AccountErrorCodes.ACCOUNT_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND
        )


def get_account_by_uidb64(uidb64, include_inactive=True):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        return get_account_by_id(uid, include_inactive=include_inactive)
    except (ValueError, TypeError, OverflowError):
        raise AccountServiceError(
            detail='Invalid activation link',
            code=AccountErrorCodes.INVALID_LINK,
            status_code=status.HTTP_400_BAD_REQUEST
        )


def check_account_active(user):
    if not user.is_active:
        raise AccountServiceError(
            detail='Your account is not activated',
            code=AccountErrorCodes.ACCOUNT_INACTIVE,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    return True


def check_account_inactive(user):
    if user.is_active:
        raise AccountServiceError(
            detail='Your account is already activated',
            code=AccountErrorCodes.ACCOUNT_ALREADY_ACTIVE,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    return True


def check_activation_token(user, token):
    if not default_token_generator.check_token(user, token):
        raise AccountServiceError(
            detail='Your token is incorrect',
            code=AccountErrorCodes.INVALID_TOKEN,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    return True


def check_password(user, password):
    if not user.check_password(password):
        raise AccountServiceError(
            detail='Your password is incorrect',
            code=AccountErrorCodes.INVALID_CREDENTIALS,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    return True


def check_email_available(email, exclude_user_id=None):
    normalized_email = normalize_email(email)
    queryset = User.objects.filter(email=normalized_email)
    if exclude_user_id is not None:
        queryset = queryset.exclude(pk=exclude_user_id)
    if queryset.exists():
        raise AccountServiceError(
            detail='This email address is already in use',
            code=AccountErrorCodes.EMAIL_ALREADY_EXISTS,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    return True


def activate_account(user):
    user.is_active = True
    user.save()
    return user
