"""
accounts/apps.py - Accounts App Configuration

Configures the 'accounts' Django application. The ready() method imports
the signals module so that the post_save signals for automatic UserProfile
creation are registered when Django starts up.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration class for the accounts app."""

    # Use BigAutoField for auto-generated primary keys
    default_auto_field = 'django.db.models.BigAutoField'

    # App name must match the directory name
    name = 'accounts'

    def ready(self):
        """
        Called when the app is ready. Imports the signals module to register
        post_save handlers for automatic UserProfile creation.
        """
        import accounts.signals  # noqa: F401
