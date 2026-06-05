from rest_framework.exceptions import APIException
from rest_framework import status


class ErrorCode:
    NOT_FOUND = 'not_found'
    VALIDATION_ERROR = 'validation_error'
    FIELD_ERROR = 'field_error'
    AUTHENTICATION_FAILED = 'authentication_failed'
    NOT_AUTHENTICATED = 'not_authenticated'
    PERMISSION_DENIED = 'permission_denied'
    CONFLICT = 'conflict'
    BAD_REQUEST = 'bad_request'
    INTERNAL_ERROR = 'internal_error'
    INVALID_TOKEN = 'invalid_token'
    TOKEN_EXPIRED = 'token_expired'
    USER_NOT_FOUND = 'user_not_found'
    PRODUCT_NOT_FOUND = 'product_not_found'
    ORDER_NOT_FOUND = 'order_not_found'
    ADDRESS_NOT_FOUND = 'address_not_found'
    INVALID_PASSWORD = 'invalid_password'
    ACCOUNT_NOT_ACTIVATED = 'account_not_activated'
    ALREADY_REVIEWED = 'already_reviewed'
    EMPTY_ORDER_ITEMS = 'empty_order_items'
    INVALID_RATING = 'invalid_rating'
    FILE_MISSING = 'file_missing'
    INVALID_FILE_TYPE = 'invalid_file_type'


class BaseAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A server error occurred.'
    default_code = ErrorCode.BAD_REQUEST

    def __init__(self, detail=None, code=None, status_code=None):
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        else:
            self.code = self.default_code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = ErrorCode.NOT_FOUND


class ValidationError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = ErrorCode.VALIDATION_ERROR


class AuthenticationError(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = ErrorCode.AUTHENTICATION_FAILED


class PermissionDeniedError(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = ErrorCode.PERMISSION_DENIED


class ConflictError(BaseAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = ErrorCode.CONFLICT


class UserNotFoundError(NotFoundError):
    default_detail = 'User not found'
    default_code = ErrorCode.USER_NOT_FOUND


class ProductNotFoundError(NotFoundError):
    default_detail = 'Product not found'
    default_code = ErrorCode.PRODUCT_NOT_FOUND


class OrderNotFoundError(NotFoundError):
    default_detail = 'Order not found'
    default_code = ErrorCode.ORDER_NOT_FOUND


class AddressNotFoundError(NotFoundError):
    default_detail = 'Address not found'
    default_code = ErrorCode.ADDRESS_NOT_FOUND


class InvalidPasswordError(AuthenticationError):
    default_detail = 'Incorrect password'
    default_code = ErrorCode.INVALID_PASSWORD


class AccountNotActivatedError(AuthenticationError):
    default_detail = 'Account is not activated'
    default_code = ErrorCode.ACCOUNT_NOT_ACTIVATED


class AlreadyReviewedError(ConflictError):
    default_detail = 'Product already reviewed'
    default_code = ErrorCode.ALREADY_REVIEWED


class EmptyOrderItemsError(ValidationError):
    default_detail = 'No order items'
    default_code = ErrorCode.EMPTY_ORDER_ITEMS


class InvalidRatingError(ValidationError):
    default_detail = 'Please select a rating'
    default_code = ErrorCode.INVALID_RATING


class FileMissingError(ValidationError):
    default_detail = 'No file uploaded'
    default_code = ErrorCode.FILE_MISSING


class InvalidFileTypeError(ValidationError):
    default_detail = 'Invalid file type'
    default_code = ErrorCode.INVALID_FILE_TYPE


def flatten_serializer_errors(errors, parent_key=''):
    flattened = {}
    if isinstance(errors, dict):
        for key, value in errors.items():
            new_key = f'{parent_key}.{key}' if parent_key else key
            if isinstance(value, (dict, list)):
                flattened.update(flatten_serializer_errors(value, new_key))
            else:
                flattened[new_key] = str(value)
    elif isinstance(errors, list):
        for i, item in enumerate(errors):
            new_key = f'{parent_key}[{i}]' if parent_key else f'[{i}]'
            if isinstance(item, (dict, list)):
                flattened.update(flatten_serializer_errors(item, new_key))
            else:
                flattened[new_key] = str(item)
    return flattened


def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
    from django.http import Http404
    from django.db.models import ObjectDoesNotExist
    from rest_framework.exceptions import (
        ValidationError as DRFValidationError,
        PermissionDenied as DRFPermissionDenied,
        NotAuthenticated,
        AuthenticationFailed,
        NotFound,
        ParseError,
        Throttled,
        ErrorDetail
    )
    from rest_framework_simplejwt.exceptions import (
        InvalidToken,
        TokenError,
        AuthenticationFailed as JWTAuthenticationFailed
    )
    from rest_framework.response import Response

    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, (DjangoPermissionDenied, DRFPermissionDenied)):
            response = Response(
                {'detail': 'Permission denied', 'code': ErrorCode.PERMISSION_DENIED},
                status=status.HTTP_403_FORBIDDEN
            )
        elif isinstance(exc, Http404):
            response = Response(
                {'detail': str(exc) if str(exc) else 'Not found', 'code': ErrorCode.NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )
        elif isinstance(exc, ObjectDoesNotExist):
            model_name = exc.__class__.__name__.replace('DoesNotExist', '')
            response = Response(
                {'detail': f'{model_name} not found', 'code': ErrorCode.NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            response = Response(
                {'detail': 'Internal server error', 'code': ErrorCode.INTERNAL_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return response

    detail = response.data
    code = ErrorCode.BAD_REQUEST

    if isinstance(exc, BaseAPIException):
        code = getattr(exc, 'code', ErrorCode.BAD_REQUEST)
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, DRFValidationError):
        code = ErrorCode.FIELD_ERROR
        if isinstance(detail, (dict, list)):
            field_errors = flatten_serializer_errors(detail)
            detail = {
                'message': 'Validation failed',
                'fields': field_errors
            }
    elif isinstance(exc, (AuthenticationFailed, JWTAuthenticationFailed)):
        code = ErrorCode.AUTHENTICATION_FAILED
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, NotAuthenticated):
        code = ErrorCode.NOT_AUTHENTICATED
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, (DRFPermissionDenied, DjangoPermissionDenied)):
        code = ErrorCode.PERMISSION_DENIED
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, (NotFound, Http404)):
        code = ErrorCode.NOT_FOUND
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, ParseError):
        code = ErrorCode.BAD_REQUEST
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, Throttled):
        code = 'throttled'
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, InvalidToken):
        code = ErrorCode.INVALID_TOKEN
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
    elif isinstance(exc, TokenError):
        code = ErrorCode.TOKEN_EXPIRED
        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']

    if isinstance(detail, ErrorDetail):
        detail = str(detail)
    elif isinstance(detail, list) and len(detail) == 1:
        detail = str(detail[0])

    response.data = {
        'detail': detail,
        'code': code
    }

    return response
