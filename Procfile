web: sh -c "if command -v python >/dev/null 2>&1; then PY=python; else PY=python3; fi; \n  $PY manage.py collectstatic --noinput && \n  $PY -m gunicorn wsgi:application --bind 0.0.0.0:${PORT:-8080}"
