#!/bin/bash

# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations (optional, but good for some setups)
# python manage.py migrate