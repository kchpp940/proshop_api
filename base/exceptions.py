from rest_framework.exceptions import APIException
from rest_framework import status


class BaseAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A server error occurred.'
    default_code = 'error'

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
    default_code = 'not_found'


class ValidationError(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'


class AuthenticationError(BaseAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = 'authentication_failed'


class PermissionDeniedError(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'


class ConflictError(BaseAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'conflict'


class UserNotFoundError(NotFoundError):
    default_detail = 'User not found'
    default_code = 'user_not_found'


class ProductNotFoundError(NotFoundError):
    default_detail = 'Product not found'
    default_code = 'product_not_found'


class OrderNotFoundError(NotFoundError):
    default_detail = 'Order not found'
    default_code = 'order_not_found'


class AddressNotFoundError(NotFoundError):
    default_detail = 'Address not found'
    default_code = 'address_not_found'


class CategoryNotFoundError(NotFoundError):
    default_detail = 'Category not found'
    default_code = 'category_not_found'


class SubCategoryNotFoundError(NotFoundError):
    default_detail = 'Sub category not found'
    default_code = 'sub_category_not_found'


class InvalidPasswordError(AuthenticationError):
    default_detail = 'Incorrect password'
    default_code = 'invalid_password'


class AccountNotActivatedError(AuthenticationError):
    default_detail = 'Account is not activated'
    default_code = 'account_not_activated'


class InvalidActivationTokenError(AuthenticationError):
    default_detail = 'Invalid activation token'
    default_code = 'invalid_activation_token'


class AlreadyReviewedError(ConflictError):
    default_detail = 'Product already reviewed'
    default_code = 'already_reviewed'


class EmptyOrderItemsError(ValidationError):
    default_detail = 'No order items'
    default_code = 'empty_order_items'


class InvalidRatingError(ValidationError):
    default_detail = 'Please select a rating'
    default_code = 'invalid_rating'


def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    from django.core.exceptions import PermissionDenied
    from django.http import Http404
    from rest_framework.exceptions import ValidationError as DRFValidationError
    from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
    from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed

    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, PermissionDenied):
            exc = PermissionDeniedError()
            response = exception_handler(exc, context)
        elif isinstance(exc, Http404):
            exc = NotFoundError(detail=str(exc) if str(exc) else 'Not found')
            response = exception_handler(exc, context)
        else:
            return None

    if response is not None:
        if hasattr(exc, 'code'):
            code = exc.code
        elif isinstance(exc, DRFValidationError):
            code = 'validation_error'
        elif isinstance(exc, (DRFPermissionDenied, PermissionDenied)):
            code = 'permission_denied'
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            code = 'authentication_failed'
        else:
            code = 'error'

        if isinstance(response.data, dict) and 'detail' in response.data:
            detail = response.data['detail']
        elif isinstance(response.data, list):
            detail = response.data
        else:
            detail = response.data

        response.data = {
            'detail': detail,
            'code': code
        }

    return response
