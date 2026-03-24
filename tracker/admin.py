"""
tracker/admin.py - Django Admin Configuration for Tracker Models

Registers all tracker models (SchoolClass, Student, AttendanceRecord,
SMSNotification) with Django's admin interface at /admin/. This provides
a backup management interface and is useful for debugging and data inspection.
"""

from django.contrib import admin
from .models import SchoolClass, Student, AttendanceRecord, GradeRecord, SMSNotification


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    """Admin config for SchoolClass - shows class name and assigned teacher."""
    list_display = ['name', 'teacher']     # Columns in the list view
    list_filter = ['teacher']              # Filter sidebar by teacher


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin config for Student - shows student details with search and filter."""
    list_display = ['first_name', 'last_name', 'school_class', 'parent_name', 'parent_phone']
    list_filter = ['school_class']                   # Filter by class
    search_fields = ['first_name', 'last_name']      # Search by student name


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """
    Admin config for AttendanceRecord.

    Includes date_hierarchy for easy date-based navigation and shows
    whether each record is a correction (audit trail visibility).
    """
    list_display = ['student', 'date', 'status', 'recorded_by', 'is_correction', 'created_at']
    list_filter = ['status', 'date', 'is_correction']               # Filter by status/date/correction
    search_fields = ['student__first_name', 'student__last_name']    # Search by student name
    date_hierarchy = 'date'                                          # Date drill-down navigation


@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'score', 'term', 'recorded_by', 'is_correction', 'created_at']
    list_filter = ['term', 'subject', 'is_correction']
    search_fields = ['student__first_name', 'student__last_name', 'subject']


@admin.register(SMSNotification)
class SMSNotificationAdmin(admin.ModelAdmin):
    """Admin config for SMSNotification - shows notification details and status."""
    list_display = ['student', 'parent_phone', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']                                        # Filter by status/date
    search_fields = ['student__first_name', 'student__last_name', 'parent_phone']  # Search
