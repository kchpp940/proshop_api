import json
import logging
from functools import wraps
from rest_framework import status

from base.models import AdminActionAudit

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_request_data(request):
    data = {}
    try:
        if request.data:
            if isinstance(request.data, dict):
                data = request.data.copy()
            else:
                data = {'raw': str(request.data)}
    except Exception:
        pass

    if 'password' in data:
        data['password'] = '***'
    return data


def admin_audit(resource_type, action_type, get_resource_id=None, extract_resource_id_from_response=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            operator = request.user if request.user.is_authenticated else None
            operator_email = operator.email if operator else None
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            request_path = request.path
            request_method = request.method

            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(request, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to get resource_id: {e}")

            if not resource_id and 'pk' in kwargs:
                resource_id = str(kwargs['pk'])

            request_data = get_request_data(request)

            try:
                response = view_func(request, *args, **kwargs)

                response_status = 'SUCCESS'
                error_message = None
                response_data = None

                if hasattr(response, 'status_code'):
                    if response.status_code >= 400:
                        response_status = 'FAILED'
                        try:
                            if hasattr(response, 'data'):
                                error_message = str(response.data)
                        except Exception:
                            pass

                try:
                    if hasattr(response, 'data'):
                        response_data = response.data
                        if isinstance(response_data, dict) and 'password' in response_data:
                            response_data['password'] = '***'
                except Exception:
                    pass

                if extract_resource_id_from_response and response_status == 'SUCCESS':
                    try:
                        extracted_id = extract_resource_id_from_response(response)
                        if extracted_id:
                            resource_id = str(extracted_id)
                    except Exception as e:
                        logger.warning(f"Failed to extract resource_id from response: {e}")

                AdminActionAudit.objects.create(
                    operator=operator,
                    operator_email=operator_email,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action_type=action_type,
                    request_path=request_path,
                    request_method=request_method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status=response_status,
                    error_message=error_message,
                    request_data=request_data,
                    response_data=response_data,
                )

                return response

            except Exception as e:
                error_msg = str(e)
                AdminActionAudit.objects.create(
                    operator=operator,
                    operator_email=operator_email,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action_type=action_type,
                    request_path=request_path,
                    request_method=request_method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='FAILED',
                    error_message=error_msg,
                    request_data=request_data,
                    response_data=None,
                )
                raise

        return wrapped_view
    return decorator


def extract_id_from_response(response):
    if hasattr(response, 'data'):
        data = response.data
        if isinstance(data, dict):
            return data.get('_id') or data.get('id')
    return None
