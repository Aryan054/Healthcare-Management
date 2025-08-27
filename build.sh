#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Upgrade pip to the latest version


# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Run Django's collectstatic command to gather all static files
# into the directory specified in settings.py (STATIC_ROOT)
python manage.py collectstatic --no-input

# Apply database migrations (optional, but good for some setups)
# python manage.py migrate
python manage.py migrate