"""
accounts/urls.py - Authentication URL Configuration

Maps URL paths to authentication views:
    /accounts/login/    -> Login page (Django's built-in LoginView)
    /accounts/logout/   -> Logout action (Django's built-in LogoutView)
    /accounts/register/ -> New user registration (custom view)
    /accounts/profile/  -> User profile display (custom view)
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Login - uses Django's built-in LoginView with our custom template
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),

    # Logout - uses Django's built-in LogoutView; redirects to LOGOUT_REDIRECT_URL in settings
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Profile - displays the logged-in user's information
    path('profile/', views.profile_view, name='profile'),

    # ----- User Management (Admin/Sysadmin only) -----
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:pk>/deactivate/', views.user_deactivate_view, name='user_deactivate'),
]
