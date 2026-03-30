"""accounts/models.py - UserProfile model extending Django's User with role and parent-child linking."""

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """One-to-one extension of Django's User with a role field and optional parent-child M2M links."""

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
        return f"{self.user.username} ({self.get_role_display()})"
