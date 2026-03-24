"""
education_tracker/urls.py - Root URL Configuration

This is the top-level URL router for the entire Django project. It maps
incoming URL paths to the appropriate app-level URL configurations.

URL routing hierarchy:
    /admin/         -> Django's built-in admin interface (for debugging/data inspection)
    /accounts/      -> accounts app (login, logout, registration, profile)
    /               -> tracker app (dashboard, classes, students, attendance, reports)

The tracker app is mounted at the root ('') so its URLs are top-level:
    /               -> Dashboard
    /classes/       -> Class management
    /students/      -> Student management
    /attendance/    -> Attendance recording and listing
    /reports/       -> Attendance reports
    /notifications/ -> SMS notification log

For more information, see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin site - provides a built-in interface for managing all models
    # Access at http://localhost:8000/admin/ (requires superuser or staff account)
    path('admin/', admin.site.urls),

    # Accounts app - handles user authentication and profile management
    # Includes: /accounts/login/, /accounts/logout/, /accounts/register/, /accounts/profile/
    path('accounts/', include('accounts.urls')),

    # Tracker app - core application functionality, mounted at root
    # Includes: /, /classes/, /students/, /attendance/, /reports/, /notifications/
    path('', include('tracker.urls')),
]
