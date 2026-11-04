release: python manage.py migrate --noinput && python manage.py ensure_admin
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60 --access-logfile -
