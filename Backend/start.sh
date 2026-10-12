#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py seed_demo
exec gunicorn comission_project.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 2 --timeout 120 --access-logfile -
