"""
tracker/models.py - Core Data Models

Defines the five main database models for the Education Tracker system:
    1. SchoolClass - Represents a class/grade (e.g., 'Primary 5A')
    2. Student - A student enrolled in a specific class
    3. AttendanceRecord - A daily attendance entry for one student
    4. GradeRecord - An immutable grade entry for one student
    5. SMSNotification - A log of SMS messages sent to parents

Entity Relationships:
    User 1---* SchoolClass (teacher assignment)
    SchoolClass 1---* Student (enrollment)
    Student 1---* AttendanceRecord (daily attendance)
    Student 1---* GradeRecord (grades)
    Student 1---* SMSNotification (absence alerts)
    AttendanceRecord ---? AttendanceRecord (self-referential for corrections/audit trail)
    GradeRecord ---? GradeRecord (self-referential for corrections/audit trail)
"""

from django.db import models
from django.contrib.auth.models import User


class SchoolClass(models.Model):
    """
    Represents a school class or grade, e.g. 'Primary 5A' or 'Grade 6B'.

    Each class can optionally be assigned to a teacher. If the teacher
    is deleted, the class remains but the teacher field becomes null.

    Attributes:
        name: Unique name of the class (e.g., 'Primary 5A')
        teacher: Optional FK to the User who teaches this class
    """
    # Class name must be unique across the school
    name = models.CharField(max_length=100, unique=True)

    # Teacher assigned to this class; SET_NULL keeps the class if teacher is deleted
    # related_name='assigned_classes' allows: teacher.assigned_classes.all()
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_classes'
    )

    class Meta:
        verbose_name_plural = "School Classes"  # Fix plural in admin panel
        ordering = ['name']                     # Sort alphabetically by default

    def __str__(self):
        """Return the class name, e.g. 'Primary 5A'."""
        return self.name


class Student(models.Model):
    """
    Represents a student enrolled in a specific school class.

    Stores the student's personal info and their parent/guardian contact
    details for SMS notifications when the student is absent.

    Attributes:
        first_name: Student's first name
        last_name: Student's last name
        school_class: FK to the SchoolClass the student belongs to
        parent_name: Name of the student's parent/guardian
        parent_phone: Phone number for SMS notifications (Uganda format)
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # CASCADE means if the class is deleted, all its students are also deleted
    # related_name='students' allows: school_class.students.all()
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name='students'
    )

    # Parent/guardian contact information for SMS notifications
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=20)  # e.g., '+256700100001'

    class Meta:
        ordering = ['last_name', 'first_name']  # Sort alphabetically by surname
        # Prevent duplicate students in the same class
        unique_together = ['first_name', 'last_name', 'school_class']

    def __str__(self):
        """Return the student's full name, e.g. 'Amina Nakamya'."""
        return f"{self.first_name} {self.last_name}"


class AttendanceRecord(models.Model):
    """
    Records a single attendance entry for one student on one date.

    Supports an immutable audit trail: when attendance is edited, a new
    correction record is created that links back to the original via the
    'corrects' field. The original record is never modified or deleted.

    To get the "effective" (latest) record for a student on a date,
    filter for records where corrections__isnull=True (i.e., no newer
    correction exists pointing to this record).

    Attributes:
        student: FK to the Student this record is for
        date: The date of the attendance record
        status: 'present', 'absent', or 'late'
        recorded_by: FK to the User (teacher) who recorded this
        created_at: Timestamp when this record was created
        is_correction: True if this record corrects a previous one
        corrects: FK to the original record this corrects (self-referential)
    """
    # Possible attendance statuses
    STATUS_CHOICES = [
        ('present', 'Present'),  # Student was in class
        ('absent', 'Absent'),    # Student was not in class (triggers SMS)
        ('late', 'Late'),        # Student arrived late
    ]

    # Which student this attendance record is for
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='attendance_records'
    )

    # The date this attendance was recorded for
    date = models.DateField()

    # Attendance status: present, absent, or late
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    # Which teacher/admin recorded this attendance
    # SET_NULL preserves the record even if the teacher account is deleted
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='recorded_attendance'
    )

    # Auto-set timestamp when the record is first created
    created_at = models.DateTimeField(auto_now_add=True)

    # Audit trail fields for immutable attendance logs (SRS NFR-4)
    is_correction = models.BooleanField(default=False)  # True if this is a correction

    # Self-referential FK: points to the original record that this corrects
    # The original record's corrections.all() returns all corrections made to it
    corrects = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='corrections'
    )

    class Meta:
        ordering = ['-date', 'student__last_name']  # Newest first, then by name

    def __str__(self):
        """Return a string like 'Amina Nakamya - 2026-03-04 - present'."""
        return f"{self.student} - {self.date} - {self.status}"


class GradeRecord(models.Model):
    """
    Records a grade entry for one student in one subject.

    Supports an immutable audit trail identical to AttendanceRecord: when a
    grade is edited, a new correction record is created that links back to
    the original via the 'corrects' field. The original is never modified.

    Attributes:
        student: FK to the Student this grade is for
        subject: The subject name (e.g., 'Mathematics')
        score: Numeric score (0-100)
        term: Academic term (Term 1, Term 2, Term 3)
        recorded_by: FK to the User who recorded this grade
        created_at: Timestamp when this record was created
        is_correction: True if this record corrects a previous one
        corrects: FK to the original record this corrects
    """
    TERM_CHOICES = [
        ('term1', 'Term 1'),
        ('term2', 'Term 2'),
        ('term3', 'Term 3'),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='grade_records'
    )
    subject = models.CharField(max_length=100)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='recorded_grades'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Audit trail fields for immutable grade logs (SRS NFR-4)
    is_correction = models.BooleanField(default=False)
    corrects = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='corrections'
    )

    class Meta:
        ordering = ['student__last_name', 'subject']

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.score} ({self.get_term_display()})"


class SMSNotification(models.Model):
    """
    Logs SMS notifications sent to parents.

    When Africa's Talking API credentials are configured, real SMS messages
    are sent. Otherwise, notifications are logged with 'simulated' status.

    Attributes:
        student: FK to the Student whose parent is being notified
        parent_phone: The phone number the SMS was sent to
        message: The full text of the SMS message
        sent_at: Timestamp when the notification was created
        status: 'sent', 'simulated', or 'failed'
    """
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='sms_notifications'
    )
    parent_phone = models.CharField(max_length=20)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20, default='simulated',
        choices=[
            ('sent', 'Sent'),            # Successfully sent via Africa's Talking API
            ('simulated', 'Simulated'),  # Logged to DB only (no API credentials)
            ('failed', 'Failed'),        # SMS API call failed
        ]
    )

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"SMS to {self.parent_phone} for {self.student} at {self.sent_at}"
