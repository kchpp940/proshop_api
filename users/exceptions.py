from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied, NotAuthenticated, NotFound
from rest_framework import status

from social_core.exceptions import AuthException

from .services import AccountAPIException, AccountErrorCodes


def _format_account(exc):
    if isinstance(exc, AccountAPIException):
        return {
            'detail': str(exc.detail),
            'code': getattr(exc.detail, 'code', exc.default_code),
        }, exc.status_code
    return None


def _format_validation(exc):
    if not isinstance(exc, ValidationError):
        return None
    detail = exc.detail
    if isinstance(detail, dict):
        if 'detail' in detail and 'code' in detail:
            return {'detail': detail['detail'], 'code': detail['code']}, exc.status_code
        first_value = next(iter(detail.values()), None)
        if isinstance(first_value, list) and first_value:
            item = first_value[0]
            return {
                'detail': str(item),
                'code': getattr(item, 'code', 'validation_error'),
            }, exc.status_code
    if isinstance(detail, list) and detail:
        item = detail[0]
        return {
            'detail': str(item),
            'code': getattr(item, 'code', 'validation_error'),
        }, exc.status_code
    return {
        'detail': str(detail),
        'code': 'validation_error',
    }, exc.status_code


def _format_social_auth(exc):
    if not isinstance(exc, AuthException):
        return None
    message = str(exc)
    lower = message.lower()
    if 'activated' in lower or 'active' in lower:
        return {'detail': message, 'code': AccountErrorCodes.ACCOUNT_INACTIVE}, status.HTTP_401_UNAUTHORIZED
    if 'not found' in lower or 'no account' in lower:
        return {'detail': message, 'code': AccountErrorCodes.ACCOUNT_NOT_FOUND}, status.HTTP_404_NOT_FOUND
    return {'detail': message, 'code': 'oauth_error'}, status.HTTP_400_BAD_REQUEST


def _format_standard(exc):
    if isinstance(exc, PermissionDenied):
        return {'detail': str(exc.detail), 'code': 'permission_denied'}, exc.status_code
    if isinstance(exc, NotAuthenticated):
        return {'detail': str(exc.detail), 'code': 'not_authenticated'}, exc.status_code
    if isinstance(exc, NotFound):
        return {'detail': str(exc.detail), 'code': 'not_found'}, exc.status_code
    if isinstance(exc, APIException):
        return {'detail': str(exc.detail), 'code': getattr(exc.detail, 'code', 'api_error')}, exc.status_code
    return None


def unified_exception_handler(exc, context):
    response = exception_handler(exc, context)

    for formatter in (_format_account, _format_validation, _format_social_auth, _format_standard):
        result = formatter(exc)
        if result is not None:
            data, status_code = result
            if response is not None:
                response.data = data
                response.status_code = status_code
                return response
            from rest_framework.response import Response
            return Response(data, status=status_code)

    return response
