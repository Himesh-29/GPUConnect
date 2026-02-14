#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create custom migrations directory if it doesn't exist
mkdir -p custom_migrations/sites
touch custom_migrations/__init__.py
touch custom_migrations/sites/__init__.py

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate
