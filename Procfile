<<<<<<< HEAD
web: gunicorn NESAKO.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120

=======
web: gunicorn NESAKO.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --log-file -

# Run migrations and collect static files on each deploy
>>>>>>> b7c7236b126d5c9afc7a99e152d9053bfcd36382
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
