"""
tracker/urls.py - Core Application URL Configuration

Maps URL paths to tracker views. These are included in the root URL config
at the '' (root) prefix, so all paths here are top-level.

URL Structure:
    /                           -> Dashboard (role-dependent content)
    /classes/                   -> Class CRUD (admin only)
    /students/                  -> Student CRUD (admin creates, teachers view)
    /attendance/                -> Attendance list, recording, and editing
    /reports/                   -> Attendance statistics and reports
    /notifications/             -> SMS notification log (admin only)
"""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard - landing page after login, shows role-appropriate summary
    path('', views.dashboard_view, name='dashboard'),

    # ----- Class Management (Admin only) -----
    path('classes/', views.class_list_view, name='class_list'),                    # List all classes
    path('classes/create/', views.class_create_view, name='class_create'),         # Create new class
    path('classes/<int:pk>/edit/', views.class_edit_view, name='class_edit'),      # Edit existing class
    path('classes/<int:pk>/delete/', views.class_delete_view, name='class_delete'),# Delete a class

    # ----- Student Management -----
    path('students/', views.student_list_view, name='student_list'),               # List students
    path('students/create/', views.student_create_view, name='student_create'),    # Add new student
    path('students/<int:pk>/edit/', views.student_edit_view, name='student_edit'), # Edit student
    path('students/<int:pk>/delete/', views.student_delete_view, name='student_delete'),  # Delete

    # ----- Attendance -----
    path('attendance/', views.attendance_list_view, name='attendance_list'),       # View attendance log
    path('attendance/record/', views.attendance_record_view, name='attendance_record'),  # Record attendance
    path('attendance/<int:pk>/edit/', views.attendance_edit_view, name='attendance_edit'),# Edit/correct

    # ----- Reports -----
    path('reports/', views.report_view, name='report'),                           # Attendance reports

    # ----- Grades -----
    path('grades/', views.grade_list_view, name='grade_list'),                    # View grade log
    path('grades/record/', views.grade_record_view, name='grade_record'),         # Record grades
    path('grades/<int:pk>/edit/', views.grade_edit_view, name='grade_edit'),      # Edit/correct grade
    path('grades/reports/', views.grade_report_view, name='grade_report'),        # Grade reports

    # ----- Parent Portal -----
    path('parent/attendance/', views.parent_attendance_view, name='parent_attendance'),
    path('parent/grades/', views.parent_grades_view, name='parent_grades'),

    # ----- SMS Notification Log (Admin only) -----
    path('notifications/', views.notification_log_view, name='notification_log'), # View sent SMS log
]
