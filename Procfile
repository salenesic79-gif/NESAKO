web: python manage.py collectstatic --noinput && gunicorn NESAKO.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 3 --timeout 120 --log-file -
