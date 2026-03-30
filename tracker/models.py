"""tracker/models.py - Database models for schools, students, attendance, grades, and SMS logs."""

from django.db import models
from django.contrib.auth.models import User


class SchoolClass(models.Model):
    """A school class with an optional assigned teacher."""
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
        return self.name


class Student(models.Model):
    """A student enrolled in a school class, with parent contact details for SMS."""
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
        return f"{self.first_name} {self.last_name}"


class AttendanceRecord(models.Model):
    """
    A daily attendance entry for one student.

    Edits create a new correction record linked via `corrects` rather than
    modifying the original. Filter `corrections__isnull=True` to get the
    current effective record.
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
        return f"{self.student} - {self.date} - {self.status}"


class GradeRecord(models.Model):
    """Grade entry for one student in one subject; uses the same immutable audit trail as AttendanceRecord."""
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
    """Logs SMS messages sent to parents; status is 'sent', 'simulated', or 'failed'."""
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
