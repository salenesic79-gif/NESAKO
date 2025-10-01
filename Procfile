web: bash -lc "python manage.py collectstatic --noinput && gunicorn wsgi:application --bind 0.0.0.0:${PORT:-8080}"
