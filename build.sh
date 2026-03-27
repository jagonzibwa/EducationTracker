#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# Create superuser from environment variables (only if it doesn't already exist)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py createsuperuser --noinput || true
    # Set superuser's role to admin so they can access all data
    python manage.py shell -c "
from django.contrib.auth.models import User
import os
u = User.objects.filter(username=os.environ['DJANGO_SUPERUSER_USERNAME']).first()
if u and hasattr(u, 'profile'):
    u.profile.role = 'admin'
    u.profile.save()
    print(f'Set {u.username} role to admin')
" || true
fi

# Seed the database with test data.
# Uses get_or_create for users/classes/students (always safe to re-run).
# Attendance and grade records are only created once — if they already
# exist the command skips them, so redeploying without a DB wipe is safe.
#
# To force a full reseed on Render: delete the PostgreSQL database, let
# Render recreate it, then trigger a manual deploy.
python manage.py seed_data || true
