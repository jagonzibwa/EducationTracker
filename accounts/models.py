"""
accounts/models.py - User Profile Model

Defines the UserProfile model that extends Django's built-in User model
with a role field. Uses a one-to-one relationship (profile pattern) rather
than replacing the User model entirely. The profile is automatically created
via a post_save signal (see signals.py) whenever a new User is created.
"""

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends Django's User model with role-based access control.

    Each user has exactly one profile (OneToOne relationship) that stores
    their role in the system. The role determines what pages they can access
    and what actions they can perform throughout the application.

    Attributes:
        user: One-to-one link to Django's built-in User model
        role: Either 'admin' (Administrator) or 'teacher' (Teacher)
    """

    # Define the available roles in the system
    ROLE_CHOICES = [
        ('admin', 'Administrator'),       # Can manage users, classes, students, view all data
        ('teacher', 'Teacher'),           # Can record attendance and view their own class data
        ('parent', 'Parent'),             # Read-only access to their children's attendance/grades
        ('sysadmin', 'System Administrator'),  # System maintenance, backup, security, upgrades
    ]

    # One-to-one link to Django's User model; CASCADE deletes profile if User is deleted
    # related_name='profile' allows access via user.profile
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Role field - defaults to 'teacher' for new registrations
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='teacher')

    # For parent accounts: link to their children (students)
    children = models.ManyToManyField(
        'tracker.Student', blank=True, related_name='parent_profiles'
    )

    def __str__(self):
        """Return a human-readable string, e.g. 'admin1 (Administrator)'."""
        return f"{self.user.username} ({self.get_role_display()})"
