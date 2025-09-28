web: gunicorn NESAKO.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --log-file -

# Run migrations and collect static files on each deploy
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
