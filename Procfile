web: gunicorn NESAKO.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120

release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
