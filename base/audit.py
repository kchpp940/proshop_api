import json
import logging
from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from base.models import AdminActionAudit

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _sanitize_data(data):
    if data is None:
        return None
    if isinstance(data, (dict, list)):
        try:
            return json.loads(json.dumps(data, default=str))
        except (TypeError, ValueError):
            return str(data)
    return data


def admin_audit(resource_type, action_type, resource_id_param=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            operator = request.user if request.user.is_authenticated else None
            operator_email = operator.email if operator and hasattr(operator, 'email') else None

            resource_id = None
            if resource_id_param and resource_id_param in kwargs:
                resource_id = str(kwargs[resource_id_param])
            elif 'pk' in kwargs:
                resource_id = str(kwargs['pk'])

            request_data = None
            try:
                if request.data:
                    if hasattr(request.data, 'dict'):
                        request_data = _sanitize_data(request.data.dict())
                    else:
                        request_data = _sanitize_data(request.data)
            except Exception:
                request_data = str(request.data)[:2000]

            audit_kwargs = {
                'operator': operator,
                'operator_email': operator_email,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'action_type': action_type,
                'request_path': request.path,
                'request_method': request.method,
                'ip_address': _get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'request_data': request_data,
            }

            try:
                response = view_func(request, *args, **kwargs)

                response_data = None
                try:
                    if isinstance(response, Response):
                        response_data = _sanitize_data(response.data)
                except Exception:
                    response_data = str(response.data)[:2000] if hasattr(response, 'data') else None

                is_success = True
                if isinstance(response, Response):
                    is_success = 200 <= response.status_code < 400

                final_resource_id = resource_id
                if not final_resource_id and isinstance(response, Response) and response.data:
                    if isinstance(response.data, dict):
                        if '_id' in response.data:
                            final_resource_id = str(response.data['_id'])
                        elif 'id' in response.data:
                            final_resource_id = str(response.data['id'])

                AdminActionAudit.objects.create(
                    **audit_kwargs,
                    resource_id=final_resource_id,
                    status='SUCCESS' if is_success else 'FAILED',
                    error_message=None if is_success else f'HTTP {response.status_code}',
                    response_data=response_data,
                )

                return response

            except Exception as e:
                error_msg = f'{type(e).__name__}: {str(e)}'
                logger.exception('Admin action failed: %s', error_msg)

                AdminActionAudit.objects.create(
                    **audit_kwargs,
                    status='FAILED',
                    error_message=error_msg[:2000],
                    response_data=None,
                )

                return Response(
                    {'detail': str(e) if str(e) else 'Internal server error'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return wrapper
    return decorator
