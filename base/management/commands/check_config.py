import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections
from django.conf import settings


class Command(BaseCommand):
    help = 'Run deep Django configuration checks before deployment'

    def is_azure_storage_enabled(self):
        if 'storages' not in settings.INSTALLED_APPS:
            return False
        default_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', '')
        azure_vars = ['AZ_STORAGE_ACCOUNT_NAME', 'AZ_STORAGE_CONTAINER', 'AZ_STORAGE_KEY']
        has_azure_env = any(os.environ.get(v) for v in azure_vars)
        return 'azure' in default_storage.lower() or has_azure_env

    def check_dir_writable_no_create(self, path_str):
        try:
            path_obj = Path(path_str)
            if not path_obj.is_absolute():
                path_obj = settings.BASE_DIR / path_obj
            if not path_obj.exists():
                return False, f"Directory does not exist: {path_obj}"
            test_file = path_obj / f'.writable_test_{os.getpid()}'
            with open(test_file, 'w') as f:
                f.write('ok')
            os.remove(test_file)
            return True, None
        except Exception as e:
            return False, str(e)

    def handle(self, *args, **options):
        errors = []
        warnings = []
        is_prod = getattr(settings, 'ENVIRONMENT', 'development') == 'production'

        self.stdout.write('🔍 Running Django deep configuration check...\n')

        self.stdout.write('  1/12 Running Django system check...')
        try:
            call_command('check', verbosity=0)
            self.stdout.write(self.style.SUCCESS('     PASSED'))
        except CommandError as e:
            errors.append(f'Django system check failed: {e}')
            self.stdout.write(self.style.ERROR('     FAILED'))

        self.stdout.write('  2/12 Checking database connectivity...')
        try:
            for db_name in connections:
                connection = connections[db_name]
                with connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
            self.stdout.write(self.style.SUCCESS('     PASSED'))
        except Exception as e:
            errors.append(f'Database connection failed: {e}')
            self.stdout.write(self.style.ERROR('     FAILED'))

        self.stdout.write('  3/12 Checking critical settings...')
        if not settings.SECRET_KEY or settings.SECRET_KEY == '':
            errors.append('SECRET_KEY is not set')
        if not hasattr(settings, 'SECRET_KEY_FALLBACKS') and (not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32):
            warnings.append('SECRET_KEY may be too short or weak')
        if settings.DEBUG:
            if is_prod:
                errors.append('DEBUG mode is enabled in production environment')
            else:
                warnings.append('DEBUG mode is enabled')
        if not settings.ALLOWED_HOSTS:
            errors.append('ALLOWED_HOSTS is empty')
        elif '*' in settings.ALLOWED_HOSTS:
            if is_prod:
                errors.append('ALLOWED_HOSTS contains "*" which is insecure in production')
            else:
                warnings.append('ALLOWED_HOSTS contains "*"')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write('  4/12 Checking JWT configuration...')
        if not hasattr(settings, 'SIMPLE_JWT'):
            errors.append('SIMPLE_JWT configuration is missing')
        else:
            jwt = settings.SIMPLE_JWT
            if 'ACCESS_TOKEN_LIFETIME' not in jwt:
                warnings.append('SIMPLE_JWT.ACCESS_TOKEN_LIFETIME not set, using default')
            if 'REFRESH_TOKEN_LIFETIME' not in jwt:
                warnings.append('SIMPLE_JWT.REFRESH_TOKEN_LIFETIME not set, using default')
            if 'AUTH_HEADER_TYPES' not in jwt:
                warnings.append('SIMPLE_JWT.AUTH_HEADER_TYPES not set, using default')
            if is_prod and jwt.get('ACCESS_TOKEN_LIFETIME') and jwt['ACCESS_TOKEN_LIFETIME'].days > 1:
                warnings.append('ACCESS_TOKEN_LIFETIME may be too long for production')
        if 'rest_framework_simplejwt.authentication.JWTAuthentication' not in \
                [c for c in settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])]:
            warnings.append('JWTAuthentication not in DEFAULT_AUTHENTICATION_CLASSES')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write('  5/12 Checking OAuth/Social Auth configuration...')
        if hasattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY'):
            if not settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
                if is_prod:
                    errors.append('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY is not set in production')
                else:
                    warnings.append('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY is not set')
        if hasattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET'):
            if not settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET:
                if is_prod:
                    errors.append('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not set in production')
                else:
                    warnings.append('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not set')
        if 'social_core.backends.google.GoogleOAuth2' not in settings.AUTHENTICATION_BACKENDS:
            warnings.append('Google OAuth2 backend not in AUTHENTICATION_BACKENDS')
        if hasattr(settings, 'DJOSER'):
            djoser = settings.DJOSER
            if not djoser.get('SOCIAL_AUTH_ALLOWED_REDIRECT_URIS'):
                warnings.append('DJOSER.SOCIAL_AUTH_ALLOWED_REDIRECT_URIS is empty')
            if is_prod and 'http://localhost' in str(djoser.get('SOCIAL_AUTH_ALLOWED_REDIRECT_URIS', [])):
                warnings.append('DJOSER.SOCIAL_AUTH_ALLOWED_REDIRECT_URIS contains localhost in production')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write('  6/12 Checking CORS configuration...')
        if getattr(settings, 'CORS_ORIGIN_ALLOW_ALL', False):
            if is_prod:
                errors.append('CORS_ORIGIN_ALLOW_ALL=True is insecure in production')
            else:
                warnings.append('CORS_ORIGIN_ALLOW_ALL=True')
        if not getattr(settings, 'CORS_ORIGIN_ALLOW_ALL', False):
            if not hasattr(settings, 'CORS_ALLOWED_ORIGINS') or not settings.CORS_ALLOWED_ORIGINS:
                warnings.append('CORS_ALLOWED_ORIGINS is empty')
        if getattr(settings, 'CORS_ALLOW_CREDENTIALS', False):
            if is_prod and getattr(settings, 'CORS_ORIGIN_ALLOW_ALL', False):
                errors.append('CORS_ALLOW_CREDENTIALS=True with CORS_ORIGIN_ALLOW_ALL=True is highly insecure')
        if 'corsheaders.middleware.CorsMiddleware' not in settings.MIDDLEWARE:
            warnings.append('CorsMiddleware not in MIDDLEWARE')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write('  7/12 Checking Email configuration...')
        if not getattr(settings, 'EMAIL_HOST', ''):
            warnings.append('EMAIL_HOST is not set')
        if not getattr(settings, 'EMAIL_PORT', None):
            warnings.append('EMAIL_PORT is not set')
        if not getattr(settings, 'EMAIL_HOST_USER', ''):
            if is_prod:
                errors.append('EMAIL_HOST_USER is not set in production')
            else:
                warnings.append('EMAIL_HOST_USER is not set')
        if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            if is_prod:
                errors.append('EMAIL_HOST_PASSWORD is not set in production')
            else:
                warnings.append('EMAIL_HOST_PASSWORD is not set')
        if is_prod and not getattr(settings, 'EMAIL_USE_TLS', False):
            warnings.append('EMAIL_USE_TLS is disabled in production')
        if is_prod and getattr(settings, 'EMAIL_BACKEND', '').endswith('smtp.EmailBackend'):
            if not getattr(settings, 'EMAIL_HOST', '').endswith('gmail.com'):
                warnings.append('Consider using a production email service instead of Gmail SMTP')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write('  8/12 Checking DJOSER configuration...')
        if hasattr(settings, 'DJOSER'):
            djoser = settings.DJOSER
            if not djoser.get('LOGIN_FIELD'):
                warnings.append('DJOSER.LOGIN_FIELD not set')
            if not djoser.get('SERIALIZERS'):
                warnings.append('DJOSER.SERIALIZERS not configured')
            if not getattr(settings, 'DOMAIN', ''):
                warnings.append('DOMAIN setting is empty (used in email templates)')
            if not getattr(settings, 'SITE_NAME', ''):
                warnings.append('SITE_NAME setting is empty (used in email templates)')
        else:
            warnings.append('DJOSER configuration is missing')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write('  9/12 Checking static files configuration...')
        if not hasattr(settings, 'STATIC_ROOT') or not settings.STATIC_ROOT:
            if is_prod:
                errors.append('STATIC_ROOT is not configured in production')
            else:
                warnings.append('STATIC_ROOT is not configured')
        if not hasattr(settings, 'STATIC_URL') or not settings.STATIC_URL:
            errors.append('STATIC_URL is not configured')
        if is_prod:
            if hasattr(settings, 'STATICFILES_STORAGE'):
                storage = settings.STATICFILES_STORAGE
                if 'whitenoise' not in storage.lower():
                    warnings.append(f'STATICFILES_STORAGE is {storage}, consider WhiteNoise for production')
            else:
                if 'whitenoise.storage.CompressedManifestStaticFilesStorage' not in str(getattr(settings, 'STORAGES', {}).get('staticfiles', {}).get('BACKEND', '')):
                    if 'whitenoise.middleware.WhiteNoiseMiddleware' not in settings.MIDDLEWARE:
                        warnings.append('WhiteNoiseMiddleware not in MIDDLEWARE for static files serving')
                    else:
                        warnings.append('Consider setting STATICFILES_STORAGE to Whitenoise storage for production')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write(' 10/12 Checking media files configuration...')
        if not hasattr(settings, 'MEDIA_URL') or not settings.MEDIA_URL:
            errors.append('MEDIA_URL is not configured')

        use_azure = self.is_azure_storage_enabled()
        if use_azure:
            self.stdout.write(self.style.WARNING('     (Azure Storage mode)'))
            for var in ['AZ_STORAGE_ACCOUNT_NAME', 'AZ_STORAGE_CONTAINER', 'AZ_STORAGE_KEY']:
                if not os.environ.get(var):
                    if is_prod:
                        errors.append(f'{var} is not set for Azure Storage in production')
                    else:
                        warnings.append(f'{var} is not set for Azure Storage')
            default_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', '')
            storages_backend = getattr(settings, 'STORAGES', {}).get('default', {}).get('BACKEND', '')
            if 'azure' not in default_storage.lower() and 'azure' not in storages_backend.lower():
                warnings.append('Azure Storage environment variables set but DEFAULT_FILE_STORAGE does not appear to be configured for Azure')
        else:
            if not hasattr(settings, 'MEDIA_ROOT') or not settings.MEDIA_ROOT:
                if is_prod:
                    errors.append('MEDIA_ROOT is not configured in production (local storage mode)')
                else:
                    warnings.append('MEDIA_ROOT is not configured (local storage mode)')
            elif is_prod:
                ok, err = self.check_dir_writable_no_create(settings.MEDIA_ROOT)
                if not ok:
                    warnings.append(f'MEDIA_ROOT directory may not be writable: {err} — '
                                   'this is expected in some deployment environments where uploads are handled separately')
            if is_prod and 'storages' not in settings.INSTALLED_APPS:
                warnings.append('django-storages not installed; media files will be stored locally')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write(' 11/12 Checking production security settings...')
        if is_prod:
            if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
                warnings.append('SECURE_SSL_REDIRECT is disabled in production')
            if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
                warnings.append('SESSION_COOKIE_SECURE is disabled in production')
            if not getattr(settings, 'CSRF_COOKIE_SECURE', False):
                warnings.append('CSRF_COOKIE_SECURE is disabled in production')
            if not getattr(settings, 'SECURE_BROWSER_XSS_FILTER', True):
                warnings.append('SECURE_BROWSER_XSS_FILTER is disabled')
            if not getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', True):
                warnings.append('SECURE_CONTENT_TYPE_NOSNIFF is disabled')
            if getattr(settings, 'X_FRAME_OPTIONS', 'DENY') != 'DENY':
                warnings.append('X_FRAME_OPTIONS is not set to DENY')
        else:
            self.stdout.write(self.style.WARNING('     SKIPPED (not production)'))
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        self.stdout.write(' 12/12 Checking authentication configuration...')
        if not hasattr(settings, 'AUTH_USER_MODEL') or not settings.AUTH_USER_MODEL:
            errors.append('AUTH_USER_MODEL is not set')
        if 'rest_framework.authtoken' not in settings.INSTALLED_APPS:
            warnings.append('rest_framework.authtoken not in INSTALLED_APPS')
        if 'rest_framework.permissions.IsAuthenticated' not in \
                [p for p in settings.REST_FRAMEWORK.get('DEFAULT_PERMISSION_CLASSES', [])]:
            warnings.append('IsAuthenticated not in DEFAULT_PERMISSION_CLASSES; API may be publicly accessible')
        self.stdout.write(self.style.SUCCESS('     PASSED'))

        if errors:
            self.stdout.write('\n❌ Configuration check FAILED with errors:')
            for error in errors:
                self.stdout.write(self.style.ERROR(f'   - {error}'))
            sys.exit(1)

        if warnings:
            self.stdout.write('\n⚠️  Configuration check PASSED with warnings:')
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'   - {warning}'))
        else:
            self.stdout.write('\n✅ All configuration checks passed!')

        sys.exit(0)
