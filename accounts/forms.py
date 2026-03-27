"""
accounts/forms.py - User Forms

Defines forms for user registration and admin user management.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
from tracker.models import Student

# Reusable Tailwind CSS classes for form input styling
TAILWIND_INPUT_CLASS = (
    'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
)


class RegistrationForm(UserCreationForm):
    """
    Custom registration form for new user sign-up.

    Only allows self-registration as Teacher or Administrator (per SRS FR 1.1, FR 1.2).
    Parent and System Administrator accounts are created by admins via User Management.
    """

    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
    ]

    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class AdminUserCreateForm(UserCreationForm):
    """Form for admins to create new user accounts."""

    ROLE_CHOICES = UserProfile.ROLE_CHOICES

    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class AdminUserEditForm(forms.ModelForm):
    """Form for admins to edit existing user accounts."""

    ROLE_CHOICES = UserProfile.ROLE_CHOICES

    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)
    is_active = forms.BooleanField(required=False, label='Active',
                                   help_text='Uncheck to deactivate this user account.')
    children = forms.ModelMultipleChoiceField(
        queryset=Student.objects.select_related('school_class').order_by(
            'school_class__name', 'last_name', 'first_name'
        ),
        required=False,
        label='Linked Students (children)',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
