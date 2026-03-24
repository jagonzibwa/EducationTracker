"""
accounts/admin.py - Django Admin Configuration for Accounts

Registers the UserProfile model with Django's admin interface (/admin/)
so administrators can view and manage user profiles and roles.
"""

from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for UserProfile.

    Customizes the admin list view:
        - list_display: Columns shown in the table (username, role)
        - list_filter: Sidebar filter to filter by role
        - search_fields: Enables searching by username or name
    """
    list_display = ['user', 'role']                                        # Table columns
    list_filter = ['role']                                                 # Sidebar filter
    search_fields = ['user__username', 'user__first_name', 'user__last_name']  # Search bar
