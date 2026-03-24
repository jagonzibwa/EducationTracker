"""
Django settings for the Education Tracker project.

This file contains all configuration settings for the Django application,
including database setup, installed apps, authentication, session management,
and static file handling.

Key configuration choices:
    - SQLite database (lightweight, no separate server needed for academic use)
    - Tailwind CSS via CDN (no build tools required)
    - Crispy Forms with Bootstrap5 template pack for styled form rendering
    - 30-minute session timeout for security (SRS NFR-1)
    - Africa/Kampala timezone (target deployment region: Uganda)

For more information on Django settings, see:
    https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path

# Build paths relative to the project root directory
# BASE_DIR points to the EducationTrackerApp/ folder (one level above this file)
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: This secret key is for development only.
# In production, use a strong random key stored in environment variables.
SECRET_KEY = 'django-insecure-2w+*&rivon-4va6=j5dtm4l7sz9g-3$1mx2_vx%trofjb!^*bu'

# SECURITY WARNING: Don't run with debug turned on in production!
# Debug mode provides detailed error pages and disables security features.
DEBUG = True

# Hosts/domains that this Django site can serve.
# Empty in development (allows localhost); must be set in production.
ALLOWED_HOSTS = []

# -------------------------------------------------------------------------
# Application Definition
# -------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',          # Django admin interface at /admin/
    'django.contrib.auth',           # Authentication framework (users, permissions)
    'django.contrib.contenttypes',   # Content type framework (used by auth)
    'django.contrib.sessions',       # Session framework (stores session data server-side)
    'django.contrib.messages',       # Messaging framework (flash messages)
    'django.contrib.staticfiles',    # Static file serving in development

    # Third-party apps
    'crispy_forms',                  # Better form rendering with template packs
    'crispy_bootstrap5',             # Bootstrap 5 template pack for crispy forms

    # Local apps (our custom code)
    'accounts',                      # User authentication, registration, and roles
    'tracker',                       # Core domain: students, classes, attendance, SMS
]

# -------------------------------------------------------------------------
# Middleware Stack
# -------------------------------------------------------------------------
# Middleware runs on every request/response cycle, in order.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',          # Security headers (HSTS, etc.)
    'django.contrib.sessions.middleware.SessionMiddleware',   # Manages sessions across requests
    'django.middleware.common.CommonMiddleware',              # URL rewriting, content-length
    'django.middleware.csrf.CsrfViewMiddleware',              # CSRF protection on POST forms
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Attaches user to request object
    'django.contrib.messages.middleware.MessageMiddleware',   # Flash message support
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # Clickjacking protection
]

# -------------------------------------------------------------------------
# URL Configuration
# -------------------------------------------------------------------------
# Points to the root URL configuration module
ROOT_URLCONF = 'education_tracker.urls'

# -------------------------------------------------------------------------
# Template Configuration
# -------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Look for templates in the project-level 'templates/' directory first
        'DIRS': [BASE_DIR / 'templates'],
        # Also look in each app's 'templates/' subdirectory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',   # Adds 'request' to template context
                'django.contrib.auth.context_processors.auth',  # Adds 'user' and 'perms'
                'django.contrib.messages.context_processors.messages',  # Adds 'messages'
            ],
        },
    },
]

# -------------------------------------------------------------------------
# WSGI Application
# -------------------------------------------------------------------------
WSGI_APPLICATION = 'education_tracker.wsgi.application'

# -------------------------------------------------------------------------
# Database Configuration
# -------------------------------------------------------------------------
# Uses PostgreSQL when DATABASE_URL environment variable is set (production).
# Falls back to SQLite for development (no separate server required).
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'education_tracker'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -------------------------------------------------------------------------
# Password Validation
# -------------------------------------------------------------------------
# Simplified (empty) for academic project to allow simple test passwords.
# In production, enable Django's built-in validators for security.
AUTH_PASSWORD_VALIDATORS = []

# -------------------------------------------------------------------------
# Internationalization
# -------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'

# Set timezone to Uganda (the target deployment region for this application)
TIME_ZONE = 'Africa/Kampala'

# Enable Django's internationalization framework
USE_I18N = True

# Enable timezone-aware datetime objects
USE_TZ = True

# -------------------------------------------------------------------------
# Static Files (CSS, JavaScript, Images)
# -------------------------------------------------------------------------
# URL prefix for static files (used in templates: {% static 'css/custom.css' %})
STATIC_URL = 'static/'

# Additional directories where Django will look for static files
# (in addition to each app's 'static/' subdirectory)
STATICFILES_DIRS = [BASE_DIR / 'static']

# -------------------------------------------------------------------------
# Default Primary Key Field Type
# -------------------------------------------------------------------------
# Use BigAutoField (64-bit integer) for auto-generated primary keys
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------------
# Crispy Forms Configuration
# -------------------------------------------------------------------------
# Use Bootstrap 5 template pack for rendering forms with crispy tags
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# -------------------------------------------------------------------------
# Authentication URLs
# -------------------------------------------------------------------------
# Where to redirect unauthenticated users (used by @login_required)
LOGIN_URL = '/accounts/login/'

# Where to redirect after successful login (the dashboard)
LOGIN_REDIRECT_URL = '/'

# Where to redirect after logout (back to login page)
LOGOUT_REDIRECT_URL = '/accounts/login/'

# -------------------------------------------------------------------------
# Session Configuration (SRS NFR-1: Security)
# -------------------------------------------------------------------------
# Session expires after 30 minutes (1800 seconds) of inactivity
SESSION_COOKIE_AGE = 1800

# Reset the session expiry timer on every request (activity extends session)
SESSION_SAVE_EVERY_REQUEST = True

# Session cookie is deleted when the browser is closed
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# -------------------------------------------------------------------------
# Africa's Talking SMS API Configuration (SRS NFR-6)
# -------------------------------------------------------------------------
# Set these environment variables to enable real SMS sending.
# When not set, SMS notifications are simulated (logged to database only).
AFRICASTALKING_USERNAME = os.environ.get('AFRICASTALKING_USERNAME', None)
AFRICASTALKING_API_KEY = os.environ.get('AFRICASTALKING_API_KEY', None)
