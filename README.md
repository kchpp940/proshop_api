# Proshop API

Proshop API is a RESTful API built with Django and Django REST Framework. It is the backend for the [Proshop](https://proshop-eshop.web.app/). Check out the [frontend repository](https://github.com/justicenyaga/proshop) for more details.

The project was inspired by [Dennis Ivanov](https://www.dennisivy.com/) and [Brad Traversy](https://www.traversymedia.com/). I followed their tutorial on udemy [Django with React | An Ecommerce Website](https://www.udemy.com/course/django-with-react-an-ecommerce-website/). I made some changes to the project to make it more interesting and to learn more about Django and React.

The API is hosted on Azure and can be accessed through this [link](https://proshop-eshop.azurewebsites.net/). The link will take you to the API home page which contains the various endpoints. A more detailed documentation will be provided soon.

## Features

The API has most of the features you would expect to find in an ecommerce web application. Some of the features include:

- User authentication
- Product reviews and ratings
- Product search feature
- Making and managing orders
- Admin product management
- Admin user management
- Admin order details page
- PayPal integration

## Technologies

### Backend

- [Django](https://www.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django REST Framework Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
- [Djoser](https://djoser.readthedocs.io/en/latest/)
- [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html)
- [PostgreSQL](https://www.postgresql.org/)

## Usage

### Prerequisites

- [Python 3.6 or higher](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/) (for production)
- SQLite3 (built-in for development)

### Quick Start

1. Clone the repository

   ```bash
   git clone https://github.com/justicenyaga/proshop.git && cd proshop
   ```

2. Create and activate a virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables

   Create a `.env` file in the project root:

   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

   **Required Environment Variables:**

   | Variable | Required | Description | Source |
   |----------|----------|-------------|--------|
   | `SECRET_KEY` | Yes | Django secret key for cryptographic signing | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L29) |
   | `ENVIRONMENT` | No | `development` (default) or `production` | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L18) |
   | `DOMAIN` | Production | Domain for email templates and OAuth redirects | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L191) |
   | `SITE_NAME` | Production | Site name for email templates | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L192) |
   | `EMAIL_HOST_USER` | Production | SMTP email username | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L118) |
   | `EMAIL_HOST_PASSWORD` | Production | SMTP email password | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L119) |
   | `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` | Optional | Google OAuth2 client ID | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L221) |
   | `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET` | Optional | Google OAuth2 client secret | [settings.py](file:///Users/pkcha/proshop_api/backend/settings.py#L222) |

   **Production-only (Azure):**

   | Variable | Required | Description | Source |
   |----------|----------|-------------|--------|
   | `APP_DB_NAME` | Yes | PostgreSQL database name | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L22) |
   | `POSTGRES_ADMIN_USER` | Yes | PostgreSQL admin username | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L23) |
   | `POSTGRES_ADMIN_PASSWORD` | Yes | PostgreSQL admin password | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L24) |
   | `POSTGRES_HOST` | Yes | PostgreSQL host address | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L25) |
   | `AZ_STORAGE_ACCOUNT_NAME` | Yes | Azure storage account name | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L15) |
   | `AZ_STORAGE_CONTAINER` | Yes | Azure storage container name | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L16) |
   | `AZ_STORAGE_KEY` | Yes | Azure storage account key | [azure_settings.py](file:///Users/pkcha/proshop_api/backend/azure_settings.py#L17) |

   **Optional (S3/DO Spaces):**

   | Variable | Required | Description | Source |
   |----------|----------|-------------|--------|
   | `AWS_ACCESS_KEY_ID` | Optional | S3 access key ID | [cdn/conf.py](file:///Users/pkcha/proshop_api/backend/cdn/conf.py#L4) |
   | `AWS_SECRET_ACCESS_KEY` | Optional | S3 secret access key | [cdn/conf.py](file:///Users/pkcha/proshop_api/backend/cdn/conf.py#L5) |

5. **Run configuration check** (recommended before first start)

   Lightweight check (no Django required, runs instantly):
   ```bash
   bin/check_config.sh
   ```

   Full check (requires Django, validates DB connection etc.):
   ```bash
   python manage.py check_config
   ```

   Options:
   ```bash
   # Lightweight check, treat warnings as errors (CI/CD)
   bin/check_config.sh --strict

   # Full check, treat warnings as errors (CI/CD)
   python manage.py check_config --strict

   # Full check, only environment variables
   python manage.py check_config --env-only
   ```

6. Run database migrations

   ```bash
   python manage.py migrate
   ```

7. Load initial data (optional)

   ```bash
   python manage.py loaddata data.json
   ```

8. Create a superuser

   ```bash
   python manage.py createsuperuser
   ```

9. Start the development server

   ```bash
   python manage.py runserver
   ```

   Open [http://localhost:8000](http://localhost:8000) in your browser.

### Development vs Production

**Development (`ENVIRONMENT=development`):**
- Uses SQLite3 database by default
- `DEBUG=True` (warnings shown but not blocked)
- `CORS_ORIGIN_ALLOW_ALL=True` (warnings shown but not blocked)
- Local filesystem storage for media

**Production (`ENVIRONMENT=production`):**
- Requires PostgreSQL database
- `DEBUG=False` enforced (error if True)
- `CORS_ORIGIN_ALLOW_ALL` must be False (error if True)
- Requires Azure Blob Storage configuration
- All optional environment variables become required

### Deployment

Configuration checks run in two passes to catch env var errors **before** Django even starts:

1. **Pass 1 — Lightweight bootstrap** (`bin/check_config.sh --strict`)
   Pure shell, no Django dependency. Catches `SECRET_KEY` missing and storage
   dir permission issues instantly, avoids Django startup crash loop.

2. **Pass 2 — Full validation** (`python manage.py check_config`)
   Requires Django, validates DB connectivity, CORS/JWT/OAuth/email configs.
   Only runs if Pass 1 succeeds.

| Scenario | Command to use |
|----------|----------------|
| **Local bootstrap** (first setup) | `bin/check_config.sh` (fast) or `python manage.py check_config` (full) |
| **CI pipeline** (pre-build check) | `bin/check_config.sh --strict` |
| **Release / deploy** (Procfile) | `bin/check_config.sh --strict && python manage.py check_config && python manage.py migrate` |
| **Web server startup** (Procfile) | `gunicorn backend.wsgi` — **no check**, transient issues don't kill the process |

In [Procfile](file:///Users/pkcha/proshop_api/Procfile):
- `release` — Pass 1 → Pass 2 → migrate (blocks deploy on any error)
- `web` — starts gunicorn directly
- `check` — runs both passes with strict mode on demand

### Configuration Check

| Entry point | Requires Django | What it checks |
|-------------|----------------|----------------|
| [bin/check_config.sh](file:///Users/pkcha/proshop_api/bin/check_config.sh) | No | Env vars, dangerous configs, storage dirs |
| [check_config](file:///Users/pkcha/proshop_api/base/management/commands/check_config.py) | Yes | Env vars, dangerous configs, DB connection, storage dirs, OAuth, CORS, JWT, email |

Full `check_config` checks:
1. **Environment Variables** - Validates all required env vars with their source references
2. **Dangerous Configs** - Blocks `DEBUG=True` and `ALLOWED_HOSTS=['*']` in production
3. **Database Connection** - Attempts to connect to the configured database
4. **Storage Directories** - Checks `STATIC_ROOT` and `MEDIA_ROOT` exist and are writable
5. **OAuth Configuration** - Validates Google OAuth2 credentials and redirect URIs
6. **CORS Configuration** - Checks CORS settings are appropriate for the environment
7. **JWT Configuration** - Validates JWT settings and token lifetimes
8. **Email Configuration** - Checks SMTP settings are complete in production
