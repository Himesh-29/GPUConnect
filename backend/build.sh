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

# Create superuser from env vars (skip if already exists)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi

# Configure the Sites framework (required for django-allauth)
python manage.py shell -c "
from django.contrib.sites.models import Site
import os
domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')
Site.objects.update_or_create(id=1, defaults={'domain': domain, 'name': 'GPU Connect'})
print(f'Site configured: {domain}')
"
