"""accounts/decorators.py - Role-based access control decorators."""

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def role_required(allowed_roles):
    """Restrict a view to users whose profile role is in allowed_roles; redirects others to dashboard."""
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
