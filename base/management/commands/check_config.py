import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Pre-start configuration check for Django project'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with non-zero code on warnings',
        )
        parser.add_argument(
            '--env-only',
            action='store_true',
            help='Only check environment variables',
        )

    def __init__(self):
        super().__init__()
        self.errors = []
        self.warnings = []
        self.info = []
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent

    def handle(self, *args, **options):
        self.strict = options.get('strict', False)
        self.env_only = options.get('env_only', False)

        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('Django Pre-Start Configuration Check'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write('')

        env = getattr(settings, 'ENVIRONMENT', 'development')
        self.info.append(f'Running environment: {env}')

        self._check_environment_variables(env)

        if not self.env_only:
            self._check_dangerous_configs(env)
            self._check_database_connection()
            self._check_storage_directories()
            self._check_oauth_configuration()
            self._check_cors_configuration(env)
            self._check_jwt_configuration()
            self._check_email_configuration(env)

        self._print_results()

        if self.errors:
            raise CommandError(f'Configuration check failed with {len(self.errors)} error(s).')

        if self.warnings and self.strict:
            raise CommandError(f'Configuration check failed with {len(self.warnings)} warning(s) (strict mode).')

        if self.warnings:
            self.stdout.write(self.style.WARNING(f'\nConfiguration check passed with {len(self.warnings)} warning(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll configuration checks passed!'))

    def _check_environment_variables(self, env):
        self.stdout.write(self.style.MIGRATE_HEADING('[1/7] Checking Environment Variables'))

        required_vars = {
            'SECRET_KEY': {
                'required': True,
                'default': None,
                'source': 'settings.py line 29',
                'description': 'Django secret key for cryptographic signing',
            },
            'DOMAIN': {
                'required': env == 'production',
                'default': None,
                'source': 'settings.py line 191',
                'description': 'Domain for email templates and OAuth redirects',
            },
            'SITE_NAME': {
                'required': env == 'production',
                'default': None,
                'source': 'settings.py line 192',
                'description': 'Site name for email templates',
            },
            'EMAIL_HOST_USER': {
                'required': env == 'production',
                'default': None,
                'source': 'settings.py line 118',
                'description': 'SMTP email username',
            },
            'EMAIL_HOST_PASSWORD': {
                'required': env == 'production',
                'default': None,
                'source': 'settings.py line 119',
                'description': 'SMTP email password',
            },
            'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY': {
                'required': False,
                'default': None,
                'source': 'settings.py line 221',
                'description': 'Google OAuth2 client ID',
            },
            'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET': {
                'required': False,
                'default': None,
                'source': 'settings.py line 222',
                'description': 'Google OAuth2 client secret',
            },
        }

        if env == 'production':
            required_vars.update({
                'APP_DB_NAME': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 22',
                    'description': 'PostgreSQL database name',
                },
                'POSTGRES_ADMIN_USER': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 23',
                    'description': 'PostgreSQL admin username',
                },
                'POSTGRES_ADMIN_PASSWORD': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 24',
                    'description': 'PostgreSQL admin password',
                },
                'POSTGRES_HOST': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 25',
                    'description': 'PostgreSQL host address',
                },
                'AZ_STORAGE_ACCOUNT_NAME': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 15',
                    'description': 'Azure storage account name',
                },
                'AZ_STORAGE_CONTAINER': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 16',
                    'description': 'Azure storage container name',
                },
                'AZ_STORAGE_KEY': {
                    'required': True,
                    'default': None,
                    'source': 'azure_settings.py line 17',
                    'description': 'Azure storage account key',
                },
            })

        has_env_file = (self.base_dir / '.env').exists()
        if has_env_file:
            self.info.append('Found .env file in project root')
        else:
            self.warnings.append('No .env file found - make sure environment variables are set')

        for var_name, spec in required_vars.items():
            value = os.environ.get(var_name)
            is_set = value is not None and value != ''

            status = 'SET' if is_set else 'MISSING'
            default_str = f' (default: {spec["default"]})' if spec['default'] else ''
            source_str = f' [source: {spec["source"]}]'

            if spec['required'] and not is_set:
                self.errors.append(
                    f'{var_name}: {spec["description"]}{source_str}'
                )
                self.stdout.write(f'  {self.style.ERROR("✗")} {var_name}: {status} - REQUIRED{default_str}{source_str}')
            elif not is_set:
                self.warnings.append(
                    f'{var_name}: {spec["description"]}{source_str}'
                )
                self.stdout.write(f'  {self.style.WARNING("△")} {var_name}: {status} - optional{default_str}{source_str}')
            else:
                masked = '*' * 8 if 'KEY' in var_name or 'SECRET' in var_name or 'PASSWORD' in var_name else value[:20]
                self.stdout.write(f'  {self.style.SUCCESS("✓")} {var_name}: SET = {masked}{source_str}')

        self.stdout.write('')

    def _check_dangerous_configs(self, env):
        self.stdout.write(self.style.MIGRATE_HEADING('[2/7] Checking Dangerous Debug Configurations'))

        debug = getattr(settings, 'DEBUG', False)
        if debug and env == 'production':
            self.errors.append(
                'DEBUG is True in production environment. '
                'Set DEBUG=False or ENVIRONMENT=production in azure_settings.py'
            )
            self.stdout.write(f'  {self.style.ERROR("✗")} DEBUG: True (DANGEROUS in production)')
        elif debug:
            self.warnings.append('DEBUG is True - this should only be used in development')
            self.stdout.write(f'  {self.style.WARNING("△")} DEBUG: True (development mode)')
        else:
            self.stdout.write(f'  {self.style.SUCCESS("✓")} DEBUG: False')

        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        if '*' in allowed_hosts and env == 'production':
            self.errors.append(
                "ALLOWED_HOSTS contains '*' in production. "
                "Set specific hostnames in azure_settings.py"
            )
            self.stdout.write(f"  {self.style.ERROR('✗')} ALLOWED_HOSTS: {allowed_hosts} (DANGEROUS in production)")
        elif '*' in allowed_hosts:
            self.warnings.append("ALLOWED_HOSTS contains '*' - restrict in production")
            self.stdout.write(f"  {self.style.WARNING('△')} ALLOWED_HOSTS: {allowed_hosts}")
        else:
            self.stdout.write(f"  {self.style.SUCCESS('✓')} ALLOWED_HOSTS: {allowed_hosts}")

        self.stdout.write('')

    def _check_database_connection(self):
        self.stdout.write(self.style.MIGRATE_HEADING('[3/7] Checking Database Configuration'))

        db_config = getattr(settings, 'DATABASES', {}).get('default', {})
        db_engine = db_config.get('ENGINE', '')

        self.stdout.write(f'  Engine: {db_engine}')
        self.stdout.write(f'  Name: {db_config.get("NAME", "N/A")}')
        self.stdout.write(f'  Host: {db_config.get("HOST", "N/A")}')

        try:
            connection.ensure_connection()
            self.stdout.write(f'  {self.style.SUCCESS("✓")} Database connection: OK')
        except Exception as e:
            self.errors.append(f'Database connection failed: {str(e)}')
            self.stdout.write(f'  {self.style.ERROR("✗")} Database connection: FAILED - {str(e)}')

        self.stdout.write('')

    def _check_storage_directories(self):
        self.stdout.write(self.style.MIGRATE_HEADING('[4/7] Checking Storage Directories'))

        storage_configs = [
            ('STATIC_ROOT', getattr(settings, 'STATIC_ROOT', None), 'Static files directory'),
            ('MEDIA_ROOT', getattr(settings, 'MEDIA_ROOT', None), 'Media files directory'),
        ]

        default_file_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', '')
        if 'AzureStorage' in default_file_storage:
            self.info.append('Using Azure Blob Storage for media files')
            self.stdout.write(f'  {self.style.SUCCESS("✓")} DEFAULT_FILE_STORAGE: Azure Blob Storage')

            required_azure_vars = ['AZ_STORAGE_ACCOUNT_NAME', 'AZ_STORAGE_CONTAINER', 'AZ_STORAGE_KEY']
            for var in required_azure_vars:
                if not os.environ.get(var):
                    self.errors.append(f'{var} is required for Azure storage')
                    self.stdout.write(f'  {self.style.ERROR("✗")} {var}: MISSING')
                else:
                    self.stdout.write(f'  {self.style.SUCCESS("✓")} {var}: SET')
        elif 'S3' in default_file_storage or 'boto' in default_file_storage:
            self.info.append('Using S3-compatible storage for media files')
            self.stdout.write(f'  {self.style.SUCCESS("✓")} DEFAULT_FILE_STORAGE: S3/DO Spaces')

            required_aws_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
            for var in required_aws_vars:
                if not os.environ.get(var):
                    self.errors.append(f'{var} is required for S3 storage')
                    self.stdout.write(f'  {self.style.ERROR("✗")} {var}: MISSING')
                else:
                    self.stdout.write(f'  {self.style.SUCCESS("✓")} {var}: SET')
        else:
            self.stdout.write(f'  Using local filesystem storage')

        for name, path, description in storage_configs:
            if path is None:
                self.warnings.append(f'{name} is not configured')
                self.stdout.write(f'  {self.style.WARNING("△")} {name}: Not configured')
                continue

            path_obj = Path(path)
            if not path_obj.is_absolute():
                path_obj = self.base_dir / path_obj

            exists = path_obj.exists()
            is_dir = path_obj.is_dir() if exists else False
            is_writable = os.access(path_obj, os.W_OK) if exists else False

            status_parts = []
            if exists:
                status_parts.append('exists')
            else:
                status_parts.append('MISSING')

            if exists and is_dir:
                status_parts.append('is directory')
            elif exists:
                status_parts.append('NOT a directory')

            if exists and is_writable:
                status_parts.append('writable')
            elif exists:
                status_parts.append('NOT writable')

            status_str = ', '.join(status_parts)

            if not exists:
                self.warnings.append(
                    f'{description} ({path_obj}) does not exist. '
                    f'Create it or run collectstatic.'
                )
                self.stdout.write(f'  {self.style.WARNING("△")} {name}: {path_obj} - {status_str}')
            elif not is_dir:
                self.errors.append(f'{name} ({path_obj}) exists but is not a directory')
                self.stdout.write(f'  {self.style.ERROR("✗")} {name}: {path_obj} - {status_str}')
            elif not is_writable:
                self.errors.append(f'{name} ({path_obj}) is not writable by current user')
                self.stdout.write(f'  {self.style.ERROR("✗")} {name}: {path_obj} - {status_str}')
            else:
                self.stdout.write(f'  {self.style.SUCCESS("✓")} {name}: {path_obj} - {status_str}')

        self.stdout.write('')

    def _check_oauth_configuration(self):
        self.stdout.write(self.style.MIGRATE_HEADING('[5/7] Checking OAuth Configuration'))

        djoser_config = getattr(settings, 'DJOSER', {})
        redirect_uris = djoser_config.get('SOCIAL_AUTH_ALLOWED_REDIRECT_URIS', [])

        if not redirect_uris:
            self.warnings.append('No OAuth redirect URIs configured in DJOSER.SOCIAL_AUTH_ALLOWED_REDIRECT_URIS')
            self.stdout.write(f'  {self.style.WARNING("△")} SOCIAL_AUTH_ALLOWED_REDIRECT_URIS: Empty')
        else:
            self.stdout.write(f'  Allowed OAuth redirect URIs:')
            for uri in redirect_uris:
                parsed = urlparse(uri)
                is_valid = all([parsed.scheme, parsed.netloc])
                has_localhost = 'localhost' in parsed.netloc or '127.0.0.1' in parsed.netloc

                if not is_valid:
                    self.errors.append(f'Invalid OAuth redirect URI: {uri}')
                    self.stdout.write(f'    {self.style.ERROR("✗")} {uri} (invalid format)')
                elif has_localhost and getattr(settings, 'ENVIRONMENT', '') == 'production':
                    self.warnings.append(f'Production OAuth redirect URI contains localhost: {uri}')
                    self.stdout.write(f'    {self.style.WARNING("△")} {uri} (contains localhost)')
                else:
                    self.stdout.write(f'    {self.style.SUCCESS("✓")} {uri}')

        google_key = getattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', None)
        google_secret = getattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', None)

        if google_key and google_secret:
            self.stdout.write(f'  {self.style.SUCCESS("✓")} Google OAuth2 credentials configured')
        elif google_key or google_secret:
            self.warnings.append('Google OAuth2 is partially configured (key or secret missing)')
            self.stdout.write(f'  {self.style.WARNING("△")} Google OAuth2: Partially configured')
        else:
            self.info.append('Google OAuth2 is not configured')
            self.stdout.write(f'  {self.style.WARNING("△")} Google OAuth2: Not configured')

        self.stdout.write('')

    def _check_cors_configuration(self, env):
        self.stdout.write(self.style.MIGRATE_HEADING('[6/7] Checking CORS Configuration'))

        cors_allow_all = getattr(settings, 'CORS_ORIGIN_ALLOW_ALL', False)

        if cors_allow_all and env == 'production':
            self.errors.append(
                'CORS_ORIGIN_ALLOW_ALL is True in production. '
                'Use CORS_ALLOWED_ORIGINS instead.'
            )
            self.stdout.write(f'  {self.style.ERROR("✗")} CORS_ORIGIN_ALLOW_ALL: True (DANGEROUS in production)')
        elif cors_allow_all:
            self.warnings.append('CORS_ORIGIN_ALLOW_ALL is True - restrict origins in production')
            self.stdout.write(f'  {self.style.WARNING("△")} CORS_ORIGIN_ALLOW_ALL: True (development mode)')
        else:
            allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            self.stdout.write(f'  {self.style.SUCCESS("✓")} CORS_ORIGIN_ALLOW_ALL: False')
            self.stdout.write(f'  CORS_ALLOWED_ORIGINS: {allowed_origins}')

        self.stdout.write('')

    def _check_jwt_configuration(self):
        self.stdout.write(self.style.MIGRATE_HEADING('[7/7] Checking JWT Configuration'))

        simple_jwt = getattr(settings, 'SIMPLE_JWT', {})
        access_lifetime = simple_jwt.get('ACCESS_TOKEN_LIFETIME', 'N/A')
        refresh_lifetime = simple_jwt.get('REFRESH_TOKEN_LIFETIME', 'N/A')

        self.stdout.write(f'  Access token lifetime: {access_lifetime}')
        self.stdout.write(f'  Refresh token lifetime: {refresh_lifetime}')

        auth_header_types = simple_jwt.get('AUTH_HEADER_TYPES', [])
        if 'JWT' in auth_header_types:
            self.stdout.write(f'  {self.style.SUCCESS("✓")} Auth header type: JWT')
        else:
            self.warnings.append(f'JWT auth header type not set to "JWT" - check SIMPLE_JWT.AUTH_HEADER_TYPES')
            self.stdout.write(f'  {self.style.WARNING("△")} Auth header types: {auth_header_types}')

        self.stdout.write('')

    def _check_email_configuration(self, env):
        self.stdout.write(self.style.MIGRATE_HEADING('[Extra] Checking Email Configuration'))

        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        self.stdout.write(f'  Email backend: {email_backend}')

        if env == 'production':
            email_host = getattr(settings, 'EMAIL_HOST', None)
            email_port = getattr(settings, 'EMAIL_PORT', None)
            email_use_tls = getattr(settings, 'EMAIL_USE_TLS', False)

            if not all([email_host, email_port]):
                self.errors.append('Email host/port not configured for production')
                self.stdout.write(f'  {self.style.ERROR("✗")} Email host/port configuration incomplete')
            else:
                self.stdout.write(f'  Host: {email_host}:{email_port}')
                self.stdout.write(f'  TLS: {email_use_tls}')
                self.stdout.write(f'  {self.style.SUCCESS("✓")} Email configuration complete')

        self.stdout.write('')

    def _print_results(self):
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('Summary'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))

        if self.info:
            self.stdout.write(f'\n{self.style.HTTP_INFO("Info:")}')
            for msg in self.info:
                self.stdout.write(f'  ℹ  {msg}')

        if self.warnings:
            self.stdout.write(f'\n{self.style.WARNING(f"Warnings ({len(self.warnings)}):")}')
            for msg in self.warnings:
                self.stdout.write(f'  △  {msg}')

        if self.errors:
            self.stdout.write(f'\n{self.style.ERROR(f"Errors ({len(self.errors)}):")}')
            for msg in self.errors:
                self.stdout.write(f'  ✗  {msg}')

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(f'Total: {len(self.info)} info, {len(self.warnings)} warnings, {len(self.errors)} errors')
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
