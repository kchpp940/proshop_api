release: bin/check_config.sh --strict && python manage.py check_config && python manage.py migrate
web: gunicorn backend.wsgi --log-file -
check: bin/check_config.sh --strict && python manage.py check_config --strict
