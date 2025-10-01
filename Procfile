web: /app/.venv/bin/python -m django collectstatic --noinput && exec /app/.venv/bin/python -m gunicorn wsgi:application --bind 0.0.0.0:${PORT:-8080}
