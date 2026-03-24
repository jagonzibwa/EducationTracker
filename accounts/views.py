"""
accounts/views.py - Authentication Views

Handles user registration and profile display.
Login and logout are handled by Django's built-in views (configured in urls.py).

Views:
    register_view: Handles new user registration (GET shows form, POST creates user)
    profile_view:  Displays the logged-in user's profile information
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import RegistrationForm, AdminUserCreateForm, AdminUserEditForm
from .decorators import role_required


def register_view(request):
    """Handle user registration for all account types."""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.role = form.cleaned_data['role']
            user.profile.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    """Display the logged-in user's profile information."""
    return render(request, 'accounts/profile.html')


# =========================================================================
# User Management Views (Admin Only)
# =========================================================================
@login_required
@role_required(['admin', 'sysadmin'])
def user_list_view(request):
    """Display all users in the system with their roles and status."""
    users = User.objects.select_related('profile').order_by('username')
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(profile__role=role_filter)
    return render(request, 'accounts/user_list.html', {
        'users': users,
        'role_filter': role_filter,
    })


@login_required
@role_required(['admin', 'sysadmin'])
def user_create_view(request):
    """Admin view to create a new user account."""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.role = form.cleaned_data['role']
            user.profile.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('user_list')
    else:
        form = AdminUserCreateForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
@role_required(['admin', 'sysadmin'])
def user_edit_view(request, pk):
    """Admin view to edit an existing user account."""
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            target_user.profile.role = form.cleaned_data['role']
            target_user.profile.save()
            messages.success(request, f'User "{target_user.username}" updated successfully.')
            return redirect('user_list')
    else:
        form = AdminUserEditForm(instance=target_user, initial={
            'role': target_user.profile.role,
        })
    return render(request, 'accounts/user_form.html', {
        'form': form, 'title': f'Edit User: {target_user.username}',
        'target_user': target_user,
    })


@login_required
@role_required(['admin', 'sysadmin'])
def user_deactivate_view(request, pk):
    """Admin view to deactivate a user account (soft delete)."""
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if target_user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
        else:
            target_user.is_active = not target_user.is_active
            target_user.save()
            action = 'activated' if target_user.is_active else 'deactivated'
            messages.success(request, f'User "{target_user.username}" {action} successfully.')
        return redirect('user_list')
    return redirect('user_list')
