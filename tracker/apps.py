"""
tracker/apps.py - Education Tracker App Configuration

Configures the 'tracker' Django application which contains the core
domain logic: students, classes, attendance records, and SMS notifications.
"""

from django.apps import AppConfig


class TrackerConfig(AppConfig):
    """Configuration class for the tracker app."""

    # Use BigAutoField for auto-generated primary keys
    default_auto_field = 'django.db.models.BigAutoField'

    # App name must match the directory name
    name = 'tracker'
