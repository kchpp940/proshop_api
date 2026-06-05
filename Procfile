release: bin/check_config.sh --strict && python manage.py check_config && python manage.py migration_guard && python manage.py migrate
web: gunicorn backend.wsgi --log_file -
