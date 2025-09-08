#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# First, upgrade pip using the correct Python module syntax to ensure we have the latest version
python -m pip install --upgrade pip

# Install all dependencies from requirements.txt using the correct Python module syntax
python -m pip install -r requirements.txt

# Run Django's collectstatic command to gather all static files
python manage.py collectstatic --no-input

# Run database migrations to create tables in the production database
python manage.py migrate