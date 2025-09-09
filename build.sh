#!/bin/bash
set -e
pip install -r requirements.txt
python manage.py collectstatic --no-input

# THIS LINE IS ESSENTIAL
python manage.py makemigrations
python manage.py migrate