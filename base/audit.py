import json
import logging
import traceback
from contextlib import contextmanager
from rest_framework import status

from base.models import AdminActionAudit

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = {
    'password', 'password1', 'password2', 'new_password', 'confirm_password',
    'token', 'access_token', 'refresh_token', 'auth_token', 'csrf_token',
    'secret', 'secret_key', 'api_key', 'private_key',
    'credit_card', 'card_number', 'cvv', 'cvc',
    'ssn', 'social_security_number',
}


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _sanitize_value(value):
    if isinstance(value, str):
        return '***'
    elif isinstance(value, (list, tuple)):
        return ['***' if isinstance(v, str) else _sanitize_value(v) for v in value]
    elif isinstance(value, dict):
        return _sanitize_dict(value)
    else:
        return '***'


def _sanitize_dict(data):
    if not isinstance(data, dict):
        return data
    sanitized = {}
    for key, value in data.items():
        if isinstance(key, str) and key.lower() in SENSITIVE_FIELDS:
            sanitized[key] = _sanitize_value(value)
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                _sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def get_sanitized_request_data(request):
    data = {}
    try:
        if hasattr(request, 'data') and request.data:
            if isinstance(request.data, dict):
                data = _sanitize_dict(request.data)
            elif isinstance(request.data, list):
                data = {'items': [
                    _sanitize_dict(item) if isinstance(item, dict) else item
                    for item in request.data
                ]}
            else:
                data = {'raw': str(request.data)}
    except Exception:
        data = {'raw': '<unserializable request data>'}
    return data


def get_sanitized_response_data(response):
    data = None
    try:
        if hasattr(response, 'data'):
            if isinstance(response.data, dict):
                data = _sanitize_dict(response.data)
            elif isinstance(response.data, list):
                data = [
                    _sanitize_dict(item) if isinstance(item, dict) else item
                    for item in response.data
                ]
            else:
                data = response.data
    except Exception:
        data = '<unserializable response data>'
    return data


def _write_audit_record(
    operator, operator_email, resource_type, resource_id, action_type,
    request_path, request_method, ip_address, user_agent,
    audit_status, error_message, request_data, response_data
):
    try:
        AdminActionAudit.objects.create(
            operator=operator,
            operator_email=operator_email,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            action_type=action_type,
            request_path=request_path,
            request_method=request_method,
            ip_address=ip_address,
            user_agent=user_agent,
            status=audit_status,
            error_message=error_message,
            request_data=request_data,
            response_data=response_data,
        )
    except Exception as e:
        logger.error(f"Failed to create audit record: {e}")


@contextmanager
def admin_audit(request, resource_type, action_type, resource_id=None, extract_resource_id_from_response=None):
    operator = request.user if request.user.is_authenticated else None
    operator_email = operator.email if operator and hasattr(operator, 'email') else None
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    request_path = request.path
    request_method = request.method
    request_data = get_sanitized_request_data(request)

    audit_context = {
        'resource_id': resource_id,
    }

    try:
        yield audit_context

        response = audit_context.get('response')
        extracted_id = audit_context.get('resource_id')
        if extract_resource_id_from_response and response and not extracted_id:
            try:
                extracted_id = extract_resource_id_from_response(response)
            except Exception as e:
                logger.warning(f"Failed to extract resource_id from response: {e}")

        audit_status = 'SUCCESS'
        error_message = None

        if response and hasattr(response, 'status_code'):
            if response.status_code == status.HTTP_403_FORBIDDEN:
                audit_status = 'FAILED'
                error_message = 'Permission denied (403)'
            elif response.status_code == status.HTTP_404_NOT_FOUND:
                audit_status = 'FAILED'
                error_message = 'Resource not found (404)'
            elif response.status_code >= 400:
                audit_status = 'FAILED'
                try:
                    if hasattr(response, 'data'):
                        error_message = str(response.data) if not isinstance(response.data, str) else response.data
                except Exception:
                    error_message = f'HTTP {response.status_code} Error'

        response_data = get_sanitized_response_data(response) if response else None

        _write_audit_record(
            operator=operator,
            operator_email=operator_email,
            resource_type=resource_type,
            resource_id=extracted_id,
            action_type=action_type,
            request_path=request_path,
            request_method=request_method,
            ip_address=ip_address,
            user_agent=user_agent,
            audit_status=audit_status,
            error_message=error_message,
            request_data=request_data,
            response_data=response_data,
        )

    except Exception as exc:
        error_msg = f'{type(exc).__name__}: {str(exc)}'
        tb = traceback.format_exc()
        logger.error(f"Admin action audit exception: {error_msg}\n{tb}")

        _write_audit_record(
            operator=operator,
            operator_email=operator_email,
            resource_type=resource_type,
            resource_id=audit_context.get('resource_id'),
            action_type=action_type,
            request_path=request_path,
            request_method=request_method,
            ip_address=ip_address,
            user_agent=user_agent,
            audit_status='FAILED',
            error_message=error_msg,
            request_data=request_data,
            response_data=None,
        )
        raise


def extract_id_from_response(response):
    if hasattr(response, 'data'):
        data = response.data
        if isinstance(data, dict):
            return data.get('_id') or data.get('id')
    return None
