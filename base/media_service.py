import os
import uuid
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage


MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}


def normalize_path(path):
    if not path:
        return ''
    return path.strip('/\\')


def get_storage_location():
    location = getattr(default_storage, 'location', None)
    return normalize_path(location)


def is_subfolder_in_location(subfolder, location):
    if not location:
        return False
    if not subfolder:
        return True

    subfolder_norm = normalize_path(subfolder)
    location_norm = normalize_path(location)

    return location_norm.endswith(subfolder_norm) or location_norm == subfolder_norm


def get_effective_subfolder(subfolder):
    storage_loc = get_storage_location()
    if is_subfolder_in_location(subfolder, storage_loc):
        return ''
    return normalize_path(subfolder)


def validate_file(file):
    if file.size > MAX_FILE_SIZE:
        raise ValueError(f'File size exceeds the maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB')

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'File extension {ext} is not allowed. Allowed extensions: {", ".join(ALLOWED_EXTENSIONS)}')

    return True


def generate_filename(original_name, subfolder=''):
    ext = os.path.splitext(original_name)[1].lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]

    effective_subfolder = get_effective_subfolder(subfolder)
    filename = f'{timestamp}_{unique_id}{ext}'

    if effective_subfolder:
        return f'{effective_subfolder}/{filename}'
    return filename


def get_media_url(file_path):
    if not file_path:
        return ''

    norm_path = normalize_path(file_path)

    if hasattr(default_storage, 'url'):
        try:
            return default_storage.url(norm_path)
        except Exception:
            pass

    if settings.MEDIA_URL.startswith(('http://', 'https://')):
        return f'{settings.MEDIA_URL.rstrip("/")}/{norm_path}'

    return f'{settings.MEDIA_URL.rstrip("/")}/{norm_path}'


def save_uploaded_file(file, subfolder=''):
    validate_file(file)

    relative_path = generate_filename(file.name, subfolder)
    saved_path = default_storage.save(relative_path, file)
    url = get_media_url(saved_path)

    return {
        'path': normalize_path(saved_path),
        'url': url,
        'name': os.path.basename(saved_path),
        'size': file.size,
    }


def delete_file(file_path):
    if not file_path:
        return False

    norm_path = normalize_path(file_path)

    try:
        if default_storage.exists(norm_path):
            default_storage.delete(norm_path)
            return True
    except Exception:
        pass

    return False


def save_image_upload(file, subfolder='', old_image_path=None):
    if old_image_path and old_image_path != 'placeholder.png':
        delete_file(old_image_path)

    return save_uploaded_file(file, subfolder)
