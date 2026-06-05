import os
import uuid
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible


MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}


def validate_file(file):
    if file.size > MAX_FILE_SIZE:
        raise ValueError(f'File size exceeds the maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB')

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'File extension {ext} is not allowed. Allowed extensions: {", ".join(ALLOWED_EXTENSIONS)}')

    return True


def generate_filename(original_name, prefix=''):
    ext = os.path.splitext(original_name)[1].lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]

    if prefix:
        prefix = prefix.rstrip('/') + '/'

    filename = f'{prefix}{timestamp}_{unique_id}{ext}'
    return filename


def get_media_url(file_path):
    if not file_path:
        return ''

    if hasattr(default_storage, 'url'):
        try:
            return default_storage.url(file_path)
        except Exception:
            pass

    if settings.MEDIA_URL.startswith(('http://', 'https://')):
        return f'{settings.MEDIA_URL.rstrip("/")}/{file_path.lstrip("/")}'

    return f'{settings.MEDIA_URL.rstrip("/")}/{file_path.lstrip("/")}'


def save_uploaded_file(file, subfolder=''):
    validate_file(file)

    relative_path = generate_filename(file.name, subfolder)

    if subfolder:
        subfolder_path = os.path.join(settings.MEDIA_ROOT, subfolder)
        os.makedirs(subfolder_path, exist_ok=True)

    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    with open(full_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    url = get_media_url(relative_path)

    return {
        'path': relative_path,
        'url': url,
        'name': os.path.basename(relative_path),
        'size': file.size,
    }


def delete_file(file_path):
    if not file_path:
        return False

    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
        return True

    return False


@deconstructible
class UploadToPath:
    def __init__(self, subfolder=''):
        self.subfolder = subfolder

    def __call__(self, instance, filename):
        return generate_filename(filename, self.subfolder)


upload_to_products = UploadToPath('products')
upload_to_categories = UploadToPath('categories')
