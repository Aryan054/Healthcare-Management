#!/bin/bash
set -e

pip install -r requirements.txt

python manage.py collectstatic --no-input

# THIS LINE IS ESSENTIAL FOR CREATING DATABASE TABLES
python manage.py migrate