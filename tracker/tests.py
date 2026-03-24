"""
tracker/tests.py - Unit Tests for the Education Tracker App

Comprehensive test suite covering models, services, views, and forms
for the core attendance tracking functionality. Tests are organized
into logical groups:

    MODEL TESTS (11 tests):
        SchoolClassModelTest   - Class creation, teacher assignment, unique names
        StudentModelTest       - Student creation, class relationship, cascade delete
        AttendanceRecordModelTest - Record creation, correction/audit trail
        SMSNotificationModelTest  - Notification creation and storage

    SERVICE TESTS (5 tests):
        SendMockSMSTest - Mock SMS service: record creation, message content, phone

    VIEW TESTS (25 tests):
        DashboardViewTest        - Role-based dashboard rendering
        ClassViewsTest           - Admin CRUD operations for classes
        StudentViewsTest         - Student listing, role-based access, search
        AttendanceRecordViewTest - Bulk recording, SMS trigger on absence
        AttendanceEditViewTest   - Correction record creation (audit trail)
        AttendanceListViewTest   - List display and status filtering
        ReportViewTest           - Statistics and percentage calculations
        NotificationLogViewTest  - Admin-only access to SMS log

    FORM TESTS (4 tests):
        SchoolClassFormTest - Form validation for class names
        StudentFormTest     - Form validation for student data

Run tests with:
    python manage.py test tracker
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from .models import SchoolClass, Student, AttendanceRecord, SMSNotification
from .services import send_mock_sms


# 
# Test Data Helper Mixin
# 
class TestDataMixin:
    """
    Mixin that provides common test data used across multiple test classes.

    Creates a standard set of test objects:
        - admin_user:    User with 'admin' role
        - teacher_user:  User with 'teacher' role
        - school_class:  SchoolClass assigned to teacher_user (Primary 5A)
        - other_class:   SchoolClass with no teacher assigned (Primary 6B)
        - student1:      Student 'Amina Nakamya' in school_class
        - student2:      Student 'Brian Mugisha' in school_class

    Usage: Call self.create_test_data() in each test class's setUp() method.
    """

    def create_test_data(self):
        """Create standard test fixtures used across multiple test classes."""

        # - Create an admin user -
        self.admin_user = User.objects.create_user(
            username='admin', password='admin123',
            first_name='Admin', last_name='User'
        )
        # Update the auto-created profile role from default 'teacher' to 'admin'
        self.admin_user.profile.role = 'admin'
        self.admin_user.profile.save()

        # - Create a teacher user -
        self.teacher_user = User.objects.create_user(
            username='teacher', password='teacher123',
            first_name='Jane', last_name='Nakato'
        )
        # Profile role defaults to 'teacher' via signal, set explicitly for clarity
        self.teacher_user.profile.role = 'teacher'
        self.teacher_user.profile.save()

        # - Create a school class assigned to the teacher -
        self.school_class = SchoolClass.objects.create(
            name='Primary 5A', teacher=self.teacher_user
        )

        # - Create a second class with no teacher assigned -
        # Used to test that teachers only see their own classes' data
        self.other_class = SchoolClass.objects.create(name='Primary 6B')

        # - Create two students in the teacher's class -
        self.student1 = Student.objects.create(
            first_name='Amina', last_name='Nakamya',
            school_class=self.school_class,
            parent_name='Sarah Nakamya', parent_phone='+256700100001'
        )
        self.student2 = Student.objects.create(
            first_name='Brian', last_name='Mugisha',
            school_class=self.school_class,
            parent_name='David Mugisha', parent_phone='+256700100002'
        )


# 
# MODEL TESTS
# 
class SchoolClassModelTest(TestCase):
    """Test the SchoolClass model for creation, relationships, and constraints."""

    def test_create_class(self):
        """A school class can be created with just a name (teacher is optional)."""
        cls = SchoolClass.objects.create(name='Grade 5A')
        self.assertEqual(str(cls), 'Grade 5A')
        self.assertIsNone(cls.teacher)  # Teacher is optional (null=True, blank=True)

    def test_class_with_teacher(self):
        """A class can be assigned to a teacher via the ForeignKey relationship."""
        teacher = User.objects.create_user(username='teacher', password='pass')
        cls = SchoolClass.objects.create(name='Grade 5A', teacher=teacher)
        self.assertEqual(cls.teacher, teacher)

    def test_unique_class_name(self):
        """
        Class names must be unique (enforced by unique=True on the name field).

        Creating two classes with the same name should raise a database error.
        """
        SchoolClass.objects.create(name='Grade 5A')
        with self.assertRaises(Exception):
            SchoolClass.objects.create(name='Grade 5A')


class StudentModelTest(TestCase, TestDataMixin):
    """Test the Student model for creation, relationships, and cascading."""

    def setUp(self):
        """Create standard test data fixtures."""
        self.create_test_data()

    def test_create_student(self):
        """Student __str__() should return 'first_name last_name'."""
        self.assertEqual(str(self.student1), 'Amina Nakamya')

    def test_student_belongs_to_class(self):
        """Student should have a ForeignKey reference to their school class."""
        self.assertEqual(self.student1.school_class, self.school_class)

    def test_students_in_class(self):
        """
        A class should provide reverse access to its students via related_name.

        The 'students' related_name is set on Student.school_class ForeignKey.
        """
        students = self.school_class.students.all()
        self.assertEqual(students.count(), 2)

    def test_cascade_delete(self):
        """
        Deleting a class should cascade-delete all its students.

        The on_delete=CASCADE on Student.school_class ensures referential integrity.
        """
        self.school_class.delete()
        self.assertEqual(Student.objects.count(), 0)


class AttendanceRecordModelTest(TestCase, TestDataMixin):
    """Test the AttendanceRecord model, including the correction/audit trail."""

    def setUp(self):
        """Create test data and store today's date for attendance records."""
        self.create_test_data()
        self.today = timezone.now().date()

    def test_create_attendance_record(self):
        """An attendance record can be created with student, date, status, and recorder."""
        record = AttendanceRecord.objects.create(
            student=self.student1,
            date=self.today,
            status='present',
            recorded_by=self.teacher_user,
        )
        self.assertEqual(record.status, 'present')
        self.assertFalse(record.is_correction)  # New records are not corrections

    def test_correction_record(self):
        """
        A correction record should link back to the original via the 'corrects' FK.

        This implements the immutable audit trail required by SRS NFR-4:
        - The original record remains unchanged
        - A new correction record supersedes it
        - The original's 'corrections' reverse relation points to the correction
        """
        # Create the original record
        original = AttendanceRecord.objects.create(
            student=self.student1,
            date=self.today,
            status='present',
            recorded_by=self.teacher_user,
        )
        # Create a correction that changes 'present' -> 'absent'
        correction = AttendanceRecord.objects.create(
            student=self.student1,
            date=self.today,
            status='absent',
            recorded_by=self.teacher_user,
            is_correction=True,
            corrects=original,
        )
        self.assertTrue(correction.is_correction)
        self.assertEqual(correction.corrects, original)
        # Verify the reverse relation: original.corrections -> [correction]
        self.assertEqual(original.corrections.first(), correction)

    def test_str_representation(self):
        """String representation should include student name and status."""
        record = AttendanceRecord.objects.create(
            student=self.student1,
            date=self.today,
            status='absent',
            recorded_by=self.teacher_user,
        )
        self.assertIn('Amina', str(record))
        self.assertIn('absent', str(record))


class SMSNotificationModelTest(TestCase, TestDataMixin):
    """Test the SMSNotification model for record creation and data integrity."""

    def setUp(self):
        """Create standard test data fixtures."""
        self.create_test_data()

    def test_create_notification(self):
        """An SMS notification can be created with all required fields."""
        notif = SMSNotification.objects.create(
            student=self.student1,
            parent_phone=self.student1.parent_phone,
            message='Test message',
            status='simulated',
        )
        self.assertEqual(notif.status, 'simulated')
        self.assertEqual(notif.parent_phone, '+256700100001')


# 
# SERVICE TESTS
# 
class SendMockSMSTest(TestCase, TestDataMixin):
    """
    Test the send_mock_sms() service function.

    This function simulates sending SMS notifications to parents by creating
    SMSNotification records in the database instead of calling an actual
    SMS API (like Africa's Talking).
    """

    def setUp(self):
        """Create standard test data fixtures."""
        self.create_test_data()

    def test_creates_notification(self):
        """send_mock_sms() should create and return an SMSNotification record."""
        notif = send_mock_sms(self.student1, reason="absent")
        self.assertIsInstance(notif, SMSNotification)
        self.assertEqual(notif.student, self.student1)
        self.assertEqual(notif.status, 'simulated')

    def test_notification_contains_student_name(self):
        """The SMS message body should include the student's full name."""
        notif = send_mock_sms(self.student1, reason="absent")
        self.assertIn('Amina', notif.message)
        self.assertIn('Nakamya', notif.message)

    def test_notification_contains_parent_name(self):
        """The SMS message body should address the parent by name."""
        notif = send_mock_sms(self.student1, reason="absent")
        self.assertIn('Sarah Nakamya', notif.message)

    def test_notification_uses_parent_phone(self):
        """The notification should store the parent's phone number for delivery."""
        notif = send_mock_sms(self.student1)
        self.assertEqual(notif.parent_phone, '+256700100001')

    def test_notification_count_increases(self):
        """Each call to send_mock_sms() should create a separate notification record."""
        self.assertEqual(SMSNotification.objects.count(), 0)
        send_mock_sms(self.student1)
        send_mock_sms(self.student2)
        self.assertEqual(SMSNotification.objects.count(), 2)


# 
# VIEW TESTS
# 
class DashboardViewTest(TestCase, TestDataMixin):
    """Test the dashboard view for authentication and role-based content."""

    def setUp(self):
        """Set up test client and create standard test data."""
        self.client = Client()
        self.create_test_data()

    def test_requires_login(self):
        """Dashboard should redirect unauthenticated users to the login page."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_loads(self):
        """
        Admin dashboard should display system-wide statistics.

        Checks for the 'Total Students' label which only appears on the
        admin version of the dashboard.
        """
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Students')

    def test_teacher_dashboard_loads(self):
        """
        Teacher dashboard should display their assigned classes.

        Checks for the 'My Classes' label which only appears on the
        teacher version of the dashboard.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Classes')


class ClassViewsTest(TestCase, TestDataMixin):
    """Test class CRUD views (admin-only access)."""

    def setUp(self):
        """Set up test client and create standard test data."""
        self.client = Client()
        self.create_test_data()

    def test_class_list_admin_access(self):
        """Admin should be able to view the class list with all classes displayed."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('class_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Primary 5A')

    def test_class_list_teacher_denied(self):
        """
        Teachers should be denied access to the class list.

        The @role_required(['admin']) decorator redirects non-admin users
        to the dashboard.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('class_list'))
        self.assertEqual(response.status_code, 302)  # Redirected to dashboard

    def test_create_class(self):
        """Admin should be able to create a new class via POST."""
        self.client.login(username='admin', password='admin123')
        response = self.client.post(reverse('class_create'), {
            'name': 'Primary 7C',
        })
        self.assertEqual(response.status_code, 302)  # Redirect to class list
        self.assertTrue(SchoolClass.objects.filter(name='Primary 7C').exists())

    def test_edit_class(self):
        """Admin should be able to edit an existing class's name."""
        self.client.login(username='admin', password='admin123')
        response = self.client.post(
            reverse('class_edit', args=[self.school_class.pk]),
            {'name': 'Primary 5B'}
        )
        self.assertEqual(response.status_code, 302)
        # Verify the name was actually changed in the database
        self.school_class.refresh_from_db()
        self.assertEqual(self.school_class.name, 'Primary 5B')

    def test_delete_class(self):
        """Admin should be able to delete a class via POST."""
        self.client.login(username='admin', password='admin123')
        response = self.client.post(reverse('class_delete', args=[self.other_class.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SchoolClass.objects.filter(name='Primary 6B').exists())


class StudentViewsTest(TestCase, TestDataMixin):
    """Test student listing and CRUD views with role-based access control."""

    def setUp(self):
        """Set up test client and create standard test data."""
        self.client = Client()
        self.create_test_data()

    def test_student_list_loads(self):
        """Authenticated users (any role) should see the student list page."""
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_sees_own_students_only(self):
        """
        Teachers should only see students enrolled in their assigned classes.

        Students in other classes (not assigned to this teacher) should
        be filtered out by the view's queryset.
        """
        # Add a student to the unassigned class (not teacher's class)
        Student.objects.create(
            first_name='Other', last_name='Student',
            school_class=self.other_class,
            parent_name='Parent', parent_phone='+256700000000'
        )
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('student_list'))
        self.assertContains(response, 'Amina')         # In teacher's class
        self.assertNotContains(response, 'Other')       # Not in teacher's class

    def test_admin_sees_all_students(self):
        """Admin should see students across ALL classes, not just assigned ones."""
        Student.objects.create(
            first_name='Other', last_name='Student',
            school_class=self.other_class,
            parent_name='Parent', parent_phone='+256700000000'
        )
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('student_list'))
        self.assertContains(response, 'Amina')   # From teacher's class
        self.assertContains(response, 'Other')    # From unassigned class

    def test_create_student_admin(self):
        """Admin should be able to add a new student via POST."""
        self.client.login(username='admin', password='admin123')
        response = self.client.post(reverse('student_create'), {
            'first_name': 'Claire',
            'last_name': 'Atim',
            'school_class': self.school_class.pk,
            'parent_name': 'Grace Atim',
            'parent_phone': '+256700100003',
        })
        self.assertEqual(response.status_code, 302)  # Redirect to student list
        self.assertTrue(Student.objects.filter(first_name='Claire').exists())

    def test_create_student_teacher_denied(self):
        """
        Teachers should NOT be able to create students.

        The @role_required(['admin']) decorator redirects teachers to the
        dashboard, and the student should not be created.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.post(reverse('student_create'), {
            'first_name': 'Denied',
            'last_name': 'Student',
            'school_class': self.school_class.pk,
            'parent_name': 'Parent',
            'parent_phone': '+256700000000',
        })
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        self.assertFalse(Student.objects.filter(first_name='Denied').exists())

    def test_search_students(self):
        """
        Student list should support name-based search via query parameter.

        The ?search= parameter filters by first_name or last_name using
        case-insensitive contains (icontains).
        """
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('student_list') + '?search=Amina')
        self.assertContains(response, 'Amina')       # Matches search
        self.assertNotContains(response, 'Brian')     # Doesn't match search


class AttendanceRecordViewTest(TestCase, TestDataMixin):
    """Test the bulk attendance recording view."""

    def setUp(self):
        """Set up test client, test data, and today's date string."""
        self.client = Client()
        self.create_test_data()
        self.today = timezone.now().date().isoformat()

    def test_attendance_form_loads(self):
        """Attendance recording form should load successfully for teachers."""
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('attendance_record'))
        self.assertEqual(response.status_code, 200)

    def test_load_students_for_class(self):
        """
        Selecting a class and date should display all students in that class.

        The class_id and date query parameters trigger the view to load
        students and render radio buttons for each one.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(
            reverse('attendance_record') + f'?class_id={self.school_class.pk}&date={self.today}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amina')
        self.assertContains(response, 'Brian')

    def test_submit_attendance(self):
        """
        Submitting the attendance form should create AttendanceRecord objects.

        One record per student with the selected status.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.post(reverse('attendance_record'), {
            'class_id': self.school_class.pk,
            'date': self.today,
            f'status_{self.student1.pk}': 'present',
            f'status_{self.student2.pk}': 'absent',
        })
        self.assertEqual(response.status_code, 302)  # Redirect to attendance list
        self.assertEqual(AttendanceRecord.objects.count(), 2)

    def test_absent_triggers_sms(self):
        """
        Marking a student as absent should trigger a mock SMS notification.

        Only absent students should generate SMS; present/late students should not.
        """
        self.client.login(username='teacher', password='teacher123')
        self.client.post(reverse('attendance_record'), {
            'class_id': self.school_class.pk,
            'date': self.today,
            f'status_{self.student1.pk}': 'present',   # No SMS for present
            f'status_{self.student2.pk}': 'absent',     # SMS triggered for absent
        })
        # Only student2 was absent, so exactly 1 SMS should be created
        self.assertEqual(SMSNotification.objects.count(), 1)
        notif = SMSNotification.objects.first()
        self.assertEqual(notif.student, self.student2)

    def test_present_does_not_trigger_sms(self):
        """Marking ALL students as present should NOT create any SMS notifications."""
        self.client.login(username='teacher', password='teacher123')
        self.client.post(reverse('attendance_record'), {
            'class_id': self.school_class.pk,
            'date': self.today,
            f'status_{self.student1.pk}': 'present',
            f'status_{self.student2.pk}': 'present',
        })
        self.assertEqual(SMSNotification.objects.count(), 0)


class AttendanceEditViewTest(TestCase, TestDataMixin):
    """Test the attendance edit (correction) view for audit trail compliance."""

    def setUp(self):
        """Set up test client, test data, and create an initial attendance record."""
        self.client = Client()
        self.create_test_data()
        self.today = timezone.now().date()
        # Create an initial 'present' record to test corrections against
        self.record = AttendanceRecord.objects.create(
            student=self.student1,
            date=self.today,
            status='present',
            recorded_by=self.teacher_user,
        )

    def test_edit_page_loads(self):
        """Edit page should load and display the student's current attendance status."""
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('attendance_edit', args=[self.record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amina')

    def test_edit_creates_correction(self):
        """
        Editing attendance should create a NEW correction record, not modify the original.

        This is the key audit trail test (SRS NFR-4):
        - Original record remains unchanged with status='present'
        - New correction record is created with status='absent' and is_correction=True
        - Correction links to the original via the 'corrects' ForeignKey
        """
        self.client.login(username='teacher', password='teacher123')
        self.client.post(reverse('attendance_edit', args=[self.record.pk]), {
            'status': 'absent',
        })
        # Verify original record is UNCHANGED
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, 'present')
        # Verify a correction record was created
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        correction = AttendanceRecord.objects.filter(is_correction=True).first()
        self.assertEqual(correction.status, 'absent')
        self.assertEqual(correction.corrects, self.record)  # Links to original


class AttendanceListViewTest(TestCase, TestDataMixin):
    """Test the attendance list view for display and filtering."""

    def setUp(self):
        """Set up test client, test data, and create a sample attendance record."""
        self.client = Client()
        self.create_test_data()
        self.today = timezone.now().date()
        # Create a 'present' record for Amina
        AttendanceRecord.objects.create(
            student=self.student1, date=self.today,
            status='present', recorded_by=self.teacher_user,
        )

    def test_list_loads(self):
        """Attendance list should load and display existing records."""
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('attendance_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amina')

    def test_filter_by_status(self):
        """
        Filtering by status should only show records matching the filter.

        Since Amina is 'present', filtering for 'absent' should hide her record.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('attendance_list') + '?status=absent')
        self.assertNotContains(response, 'Amina')  # Amina is present, not absent


class ReportViewTest(TestCase, TestDataMixin):
    """Test the attendance report view for statistics and calculations."""

    def setUp(self):
        """Set up test data with mixed attendance records for statistical testing."""
        self.client = Client()
        self.create_test_data()
        self.today = timezone.now().date()
        # Create attendance: student1=present, student2=absent
        # Expected stats: 50% attendance (1 present out of 2 total)
        AttendanceRecord.objects.create(
            student=self.student1, date=self.today,
            status='present', recorded_by=self.teacher_user,
        )
        AttendanceRecord.objects.create(
            student=self.student2, date=self.today,
            status='absent', recorded_by=self.teacher_user,
        )

    def test_report_loads(self):
        """Report page should load successfully with the 'Attendance Reports' heading."""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attendance Reports')

    def test_report_shows_statistics(self):
        """
        Report should display correct attendance percentage.

        With 1 present and 1 absent out of 2 total records,
        the overall attendance percentage should be 50%.
        """
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('report'))
        self.assertContains(response, '50%')  # 1 present / 2 total = 50%


class NotificationLogViewTest(TestCase, TestDataMixin):
    """Test the SMS notification log view (admin-only access)."""

    def setUp(self):
        """Set up test client and create standard test data."""
        self.client = Client()
        self.create_test_data()

    def test_admin_can_access(self):
        """Admin should see the notification log with SMS records displayed."""
        # Create a mock SMS first so there's something to display
        send_mock_sms(self.student1)
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('notification_log'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amina')

    def test_teacher_denied(self):
        """
        Teachers should be denied access to the notification log.

        The @role_required(['admin']) decorator redirects non-admin users
        to the dashboard.
        """
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('notification_log'))
        self.assertEqual(response.status_code, 302)  # Redirected to dashboard


# 
# FORM TESTS
# 
class SchoolClassFormTest(TestCase):
    """Test the SchoolClassForm validation logic."""

    def test_valid_form(self):
        """Form should be valid when provided with a class name."""
        from .forms import SchoolClassForm
        form = SchoolClassForm(data={'name': 'Grade 5A'})
        self.assertTrue(form.is_valid())

    def test_empty_name_invalid(self):
        """Form should be invalid when the class name is empty (required field)."""
        from .forms import SchoolClassForm
        form = SchoolClassForm(data={'name': ''})
        self.assertFalse(form.is_valid())


class StudentFormTest(TestCase, TestDataMixin):
    """Test the StudentForm validation logic."""

    def setUp(self):
        """Create standard test data (needed for school_class FK reference)."""
        self.create_test_data()

    def test_valid_form(self):
        """Form should be valid when all required fields are provided."""
        from .forms import StudentForm
        form = StudentForm(data={
            'first_name': 'Claire',
            'last_name': 'Atim',
            'school_class': self.school_class.pk,
            'parent_name': 'Grace Atim',
            'parent_phone': '+256700100003',
        })
        self.assertTrue(form.is_valid())

    def test_missing_required_field(self):
        """Form should be invalid when required fields are missing."""
        from .forms import StudentForm
        form = StudentForm(data={
            'first_name': 'Claire',
            # Missing: last_name, school_class, parent_name, parent_phone
        })
        self.assertFalse(form.is_valid())
