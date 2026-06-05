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
- Unified media storage service for product and category images

## Technologies

### Backend

- [Django](https://www.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django REST Framework Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
- [Djoser](https://djoser.readthedocs.io/en/latest/)
- [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html)
- [PostgreSQL](https://www.postgresql.org/)
- [django-storages](https://django-storages.readthedocs.io/) with DigitalOcean Spaces S3 support

## Media Storage Configuration

The project uses a unified media storage service with consistent validation, naming, and URL generation. The underlying storage backend is configured through Django's storage system.

### Local Storage (Development)

In development mode, media files are stored locally:

- `MEDIA_ROOT`: `static/images/`
- `MEDIA_URL`: `images/`
- Files are served via Django static file serving in DEBUG mode

### Cloud Storage (Production)

When `ENVIRONMENT=production`, the project switches to S3-compatible cloud storage via `django-storages`. The storage configuration is loaded from `backend/cdn/`.

**Current project defaults (defined in `backend/cdn/conf.py`):**

| Setting | Current Value |
|---------|---------------|
| Storage Backend | `backend.cdn.backends.MediaStorageS3Boto3Storage` |
| Bucket Name | `proshop` |
| Endpoint URL | `https://proshop.nyc3.digitaloceanspaces.com` |
| Cache Control | `max-age=86400` |
| Default ACL | `public-read` |
| Querystring Auth | `False` |

**CDN backend settings (in `backend/cdn/backends.py`):**
- `location = 'images'` — all files prefixed with `images/`
- `file_overwrite = False` — auto-rename to avoid collisions

**Environment variables required for production:**

```bash
# Enable production mode (triggers S3 storage)
ENVIRONMENT=production

# S3/Spaces credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

> **Note**: Bucket name, endpoint, and other storage settings are currently hardcoded in `backend/cdn/conf.py`. To use a different bucket or region, modify that file directly.

### Upload Configuration (Unified via Media Service)

Both product and category image uploads go through the same `save_image_upload()` flow in `base/media_service.py`:

1. **Validation**: File size (≤5MB) and extension check
2. **Naming**: `{timestamp}_{uuid}.{ext}` — `images/` prefix is added by storage backend if needed
3. **Storage**: Saved via Django `default_storage.save()` (works for both local and S3)
4. **Cleanup**: Old image file is deleted before saving new one
5. **URL Generation**: Returned via `default_storage.url()` for CDN compatibility

**Path behavior:**
- **Local storage**: `images/20260605_123456_abc12345.jpg` (service adds prefix)
- **S3 storage**: `20260605_123456_abc12345.jpg` (backend adds `images/` location prefix)
- Result: Both environments store at `images/filename.ext` relative to their root

**Upload constraints:**
- Maximum file size: 5MB
- Allowed extensions: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`
- Backward compatible with existing `images/` path structure

## Usage

### Prerequisites

- [Python 3.6 or higher](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/) (optional) - You can use any other database of your choice

### Installation

I Will be providing a detailed documentation on this soon.

<!--

1. Clone the repository

   ```bash
   git clone https://github.com/justicenyaga/proshop.git && cd proshop
   ```

2. Create a virtual environment

   ```bash
   virtualenv -p python3 venv
   ```

3. Activate the virtual environment

   ```bash
   source venv/bin/activate
   ```

4. Install the dependencies

   ```bash
   pip install -r requirements.txt
   ```

5. Add the environment variables

   #### option 1: create a .env file in the root directory and add the following environment variables

   ```
   SECRET_KEY=your_secret_key
   ```

   #### option 2: export the environment variables in your terminal

   ```bash
   export SECRET_KEY=your_secret_key
   ```

6. Run the migrations

   ```bash
   python manage.py migrate
   ```

7. Load the initial data

   ```bash
   python manage.py loaddata data.json
   ```

8. Create a superuser

   ```bash
   python manage.py createsuperuser
   ```

9. Run the app

   ```bash
   python manage.py runserver
   ```

- Open [http://localhost:8000](http://localhost:8000) on your browser to view the app.

  ```
  use the superuser credentials to login to the admin panel
  ``` -->
