#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Run Django's collectstatic command to gather all static files
python manage.py collectstatic --no-input

# ==========================================================
# --- THIS IS THE CRUCIAL FIX ---
# This command creates all the necessary tables in your new
# Vercel Postgres database.
# ==========================================================
python manage.py migrate