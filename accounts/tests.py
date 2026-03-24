"""
accounts/tests.py - Unit Tests for the Accounts App

Tests the user authentication and profile management functionality:

    UserProfileModelTest (4 tests):
        - Automatic profile creation via Django signals
        - Default role assignment ('teacher')
        - Role mutation (changing to 'admin')
        - String representation format

    RegistrationViewTest (6 tests):
        - Registration page accessibility (GET request)
        - Correct template usage
        - Successful user creation with valid data
        - Role assignment during registration
        - Password mismatch rejection
        - Missing required fields rejection

    LoginViewTest (4 tests):
        - Login page accessibility (GET request)
        - Correct template usage
        - Successful authentication and redirect
        - Invalid credentials handling

    ProfileViewTest (2 tests):
        - Authentication requirement (redirects anonymous users)
        - Profile display for authenticated users

Run tests with:
    python manage.py test accounts
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


# =========================================================================
# Model Tests
# =========================================================================
class UserProfileModelTest(TestCase):
    """Test the UserProfile model and its automatic creation via signals."""

    def test_profile_created_automatically(self):
        """
        Verify that creating a User automatically creates a linked UserProfile.

        The post_save signal in accounts/signals.py should fire on User creation
        and create a corresponding UserProfile with a OneToOne relationship.
        """
        user = User.objects.create_user(username='testuser', password='testpass')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_default_role_is_teacher(self):
        """
        New profiles should default to the 'teacher' role.

        This ensures that newly registered users have limited permissions
        until an admin upgrades their role if needed.
        """
        user = User.objects.create_user(username='testuser', password='testpass')
        self.assertEqual(user.profile.role, 'teacher')

    def test_role_can_be_set_to_admin(self):
        """
        Verify that the profile role can be changed to 'admin'.

        Admins have access to additional features like class/student CRUD
        and the SMS notification log.
        """
        user = User.objects.create_user(username='testuser', password='testpass')
        user.profile.role = 'admin'
        user.profile.save()
        # Refresh from the database to confirm persistence
        user.refresh_from_db()
        self.assertEqual(user.profile.role, 'admin')

    def test_str_representation(self):
        """
        String representation should include username and role display name.

        Format: "testuser (Teacher)" — used in admin interface and debugging.
        """
        user = User.objects.create_user(username='testuser', password='testpass')
        self.assertIn('testuser', str(user.profile))
        self.assertIn('Teacher', str(user.profile))


# =========================================================================
# Registration View Tests
# =========================================================================
class RegistrationViewTest(TestCase):
    """Test the user registration view (/accounts/register/)."""

    def setUp(self):
        """Set up the test client and registration URL for all tests."""
        self.client = Client()
        self.register_url = reverse('register')

    def test_register_page_loads(self):
        """Registration page should return HTTP 200 for anonymous users."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_register_page_uses_correct_template(self):
        """Registration view should render the accounts/register.html template."""
        response = self.client.get(self.register_url)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_successful_registration(self):
        """
        Valid registration data should create a user and redirect to login.

        The redirect (302) indicates successful form submission.
        """
        data = {
            'username': 'newteacher',
            'first_name': 'New',
            'last_name': 'Teacher',
            'email': 'new@school.ug',
            'role': 'teacher',
            'password1': 'securepass123',
            'password2': 'securepass123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect to login page
        self.assertTrue(User.objects.filter(username='newteacher').exists())

    def test_registration_sets_role(self):
        """
        Registration should set the selected role on the user's profile.

        The view updates the auto-created profile's role field after
        the User object is saved (see accounts/views.py register_view).
        """
        data = {
            'username': 'newadmin',
            'first_name': 'New',
            'last_name': 'Admin',
            'email': 'admin@school.ug',
            'role': 'admin',
            'password1': 'securepass123',
            'password2': 'securepass123',
        }
        self.client.post(self.register_url, data)
        user = User.objects.get(username='newadmin')
        self.assertEqual(user.profile.role, 'admin')

    def test_registration_password_mismatch(self):
        """
        Mismatched passwords should fail validation and not create a user.

        The form stays on the same page (200) with error messages.
        """
        data = {
            'username': 'baduser',
            'first_name': 'Bad',
            'last_name': 'User',
            'email': 'bad@school.ug',
            'role': 'teacher',
            'password1': 'password123',
            'password2': 'different456',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)  # Stays on registration page
        self.assertFalse(User.objects.filter(username='baduser').exists())

    def test_registration_missing_fields(self):
        """
        Missing required fields (like username) should fail validation.

        The form stays on the same page (200) with field-specific errors.
        """
        data = {
            'username': '',
            'password1': 'securepass123',
            'password2': 'securepass123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)


# =========================================================================
# Login View Tests
# =========================================================================
class LoginViewTest(TestCase):
    """Test the login view (/accounts/login/)."""

    def setUp(self):
        """Set up the test client, login URL, and a test user."""
        self.client = Client()
        self.login_url = reverse('login')
        # Create a user to test login against
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )

    def test_login_page_loads(self):
        """Login page should return HTTP 200 for anonymous users."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_page_uses_correct_template(self):
        """Login view should render the accounts/login.html template."""
        response = self.client.get(self.login_url)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_successful_login(self):
        """
        Valid credentials should authenticate the user and redirect to dashboard.

        LOGIN_REDIRECT_URL is set to '/' in settings.py, which maps to the
        dashboard view.
        """
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')

    def test_invalid_login(self):
        """
        Invalid credentials should not authenticate and should stay on the login page.

        The response code 200 (not 302) means the form was re-rendered with errors.
        """
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)


# =========================================================================
# Profile View Tests
# =========================================================================
class ProfileViewTest(TestCase):
    """Test the profile view (/accounts/profile/)."""

    def setUp(self):
        """Set up the test client, profile URL, and a test user."""
        self.client = Client()
        self.profile_url = reverse('profile')
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            first_name='Test', last_name='User'
        )

    def test_profile_requires_login(self):
        """
        Profile page should redirect unauthenticated users to the login page.

        The @login_required decorator redirects to LOGIN_URL (/accounts/login/).
        """
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_loads_for_authenticated_user(self):
        """
        Authenticated user should see their profile page with their name displayed.

        Verifies both that the page loads (200) and contains the user's name.
        """
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test')
        self.assertContains(response, 'User')
