"""
accounts/decorators.py - Role-Based Access Control Decorators

Provides custom decorators for enforcing role-based permissions on views.
Used alongside Django's @login_required to restrict page access based on
the user's role (admin or teacher).

Usage:
    @login_required
    @role_required(['admin'])
    def admin_only_view(request): ...

    @login_required
    @admin_required
    def another_admin_view(request): ...
"""

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def role_required(allowed_roles):
    """
    Decorator factory that restricts view access to users with specific roles.

    Checks if the logged-in user's profile role is in the allowed_roles list.
    If not, shows an error message and redirects to the dashboard.

    Args:
        allowed_roles (list): Role strings that are permitted,
                              e.g. ['admin'], ['teacher'], or ['admin', 'teacher']

    Returns:
        A decorator function that wraps the view.
    """
    def decorator(view_func):
        @wraps(view_func)  # Preserves the original function's name and docstring
        def wrapper(request, *args, **kwargs):
            # Check if user has a profile and their role is in the allowed list
            if hasattr(request.user, 'profile') and request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            # User lacks permission - show error and redirect to dashboard
            messages.error(request, "You do not have permission to access this page.")
            return redirect('dashboard')
        return wrapper
    return decorator


def admin_required(view_func):
    """Shortcut decorator: restricts access to Administrator users only."""
    return role_required(['admin'])(view_func)


def teacher_required(view_func):
    """Shortcut decorator: restricts access to Teacher users only."""
    return role_required(['teacher'])(view_func)
