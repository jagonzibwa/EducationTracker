"""
accounts/signals.py - Automatic Profile Creation Signals

Uses Django's signal framework to automatically create and save a UserProfile
whenever a new User object is created. This ensures every user in the system
always has an associated profile with a role.

Workflow:
    1. A new User is created (via registration or admin panel)
    2. Django fires a post_save signal
    3. create_user_profile() catches the signal and creates a UserProfile
    4. save_user_profile() ensures the profile is saved when the user is saved

The signals are connected in accounts/apps.py via the ready() method.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler: Create a UserProfile when a new User is created.

    Args:
        sender: The model class that sent the signal (User)
        instance: The actual User instance that was saved
        created: True if this is a new User, False if updating existing
    """
    if created:
        # Only create a profile for brand-new users, not for updates
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler: Save the UserProfile whenever the User is saved.

    Ensures any changes to the profile are persisted when the
    associated User object is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
