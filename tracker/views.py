"""
tracker/views.py - Core Application Views

Contains all the view functions for the tracker app, implementing the main
business logic for the Education Tracker system. Views are organized into
five functional areas:

    1. Dashboard        - Role-based landing page with attendance statistics
    2. Class CRUD       - Create, read, update, delete school classes (admin only)
    3. Student CRUD     - Manage student records (admin creates; teachers view)
    4. Attendance       - Record, list, and edit attendance with audit trail
    5. Reports          - Aggregate attendance statistics per student
    6. Notifications    - View SMS notification log (admin only)

Role-based access control:
    - @login_required ensures user is authenticated
    - @role_required(['admin', 'sysadmin']) restricts to admin-only views
    - @role_required(['teacher', 'admin', 'sysadmin']) allows both roles
    - Views without @role_required filter data by role in the queryset

Audit Trail (SRS NFR-4):
    When attendance is edited, the original record is preserved and a new
    'correction' record is created that links back to the original via the
    `corrects` ForeignKey. The `corrections__isnull=True` filter ensures
    only the latest (uncorrected) record is shown in lists and reports.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone

from .models import SchoolClass, Student, AttendanceRecord, GradeRecord, SMSNotification
from .forms import SchoolClassForm, StudentForm, GradeRecordForm
from .services import send_sms
from accounts.decorators import role_required


# 
# Dashboard View
# 
@login_required
def dashboard_view(request):
    """
    Render the main dashboard with role-appropriate content.

    Admin/Sysadmin: system-wide metrics and management tools
    Teacher: their own classes' metrics
    Parent: their children's attendance and grade summaries
    """
    today = timezone.now().date()
    user = request.user
    role = user.profile.role

    if role == 'parent':
        # - Parent Dashboard: children's attendance overview -
        children = user.profile.children.all().select_related('school_class')
        children_data = []
        for child in children:
            recent_attendance = AttendanceRecord.objects.filter(
                student=child, corrections__isnull=True
            ).order_by('-date')[:5]
            total_records = AttendanceRecord.objects.filter(
                student=child, corrections__isnull=True
            ).count()
            present_count = AttendanceRecord.objects.filter(
                student=child, corrections__isnull=True, status='present'
            ).count()
            attendance_pct = round((present_count / total_records * 100) if total_records > 0 else 0)
            recent_grades = GradeRecord.objects.filter(
                student=child, corrections__isnull=True
            ).order_by('-created_at')[:5]
            children_data.append({
                'student': child,
                'recent_attendance': recent_attendance,
                'recent_grades': recent_grades,
                'attendance_pct': attendance_pct,
                'total_records': total_records,
                'present_count': present_count,
            })
        context = {'children_data': children_data}
        return render(request, 'tracker/dashboard_parent.html', context)

    if role in ('admin', 'sysadmin'):
        # - Admin/Sysadmin Dashboard: system-wide overview -
        total_students = Student.objects.count()
        total_classes = SchoolClass.objects.count()
        total_teachers = user.__class__.objects.filter(profile__role='teacher').count()

        today_records = AttendanceRecord.objects.filter(
            date=today, corrections__isnull=True
        )
        today_present = today_records.filter(status='present').count()
        today_absent = today_records.filter(status='absent').count()
        today_late = today_records.filter(status='late').count()
        today_total = today_present + today_absent + today_late

        recent_notifications = SMSNotification.objects.all()[:5]

        context = {
            'total_students': total_students,
            'total_classes': total_classes,
            'total_teachers': total_teachers,
            'today_present': today_present,
            'today_absent': today_absent,
            'today_late': today_late,
            'today_total': today_total,
            'attendance_pct': round((today_present / today_total * 100) if today_total > 0 else 0),
            'recent_notifications': recent_notifications,
        }
    else:
        # - Teacher Dashboard: scoped to assigned classes ---
        my_classes = SchoolClass.objects.filter(teacher=user)
        my_student_count = Student.objects.filter(school_class__teacher=user).count()

        today_records = AttendanceRecord.objects.filter(
            date=today,
            student__school_class__teacher=user,
            corrections__isnull=True,
        )
        today_present = today_records.filter(status='present').count()
        today_absent = today_records.filter(status='absent').count()
        today_late = today_records.filter(status='late').count()
        today_total = today_present + today_absent + today_late

        context = {
            'my_classes': my_classes,
            'my_student_count': my_student_count,
            'today_present': today_present,
            'today_absent': today_absent,
            'today_late': today_late,
            'today_total': today_total,
            'attendance_pct': round((today_present / today_total * 100) if today_total > 0 else 0),
        }

    return render(request, 'tracker/dashboard.html', context)


# 
# Class CRUD Views (Admin Only)
# 
@login_required
@role_required(['admin', 'sysadmin'])
def class_list_view(request):
    """
    Display all school classes with their student counts.

    Uses Django's `annotate()` to add a computed `student_count` field
    to each class, avoiding N+1 queries. Only accessible by admins.
    """
    # Annotate each class with the number of enrolled students
    classes = SchoolClass.objects.annotate(student_count=Count('students'))
    return render(request, 'tracker/class_list.html', {'classes': classes})


@login_required
@role_required(['admin', 'sysadmin'])
def class_create_view(request):
    """
    Handle the creation of a new school class.

    GET:  Display an empty SchoolClassForm
    POST: Validate and save the form, then redirect to the class list

    The form's __init__ filters the teacher dropdown to only show users
    with the 'teacher' role (see forms.py).
    """
    if request.method == 'POST':
        form = SchoolClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class created successfully.')
            return redirect('class_list')
    else:
        form = SchoolClassForm()
    return render(request, 'tracker/class_form.html', {'form': form, 'title': 'Create Class'})


@login_required
@role_required(['admin', 'sysadmin'])
def class_edit_view(request, pk):
    """
    Handle editing an existing school class.

    Args:
        pk: Primary key of the SchoolClass to edit

    GET:  Display the form pre-filled with the class's current data
    POST: Validate and save changes, then redirect to the class list
    """
    school_class = get_object_or_404(SchoolClass, pk=pk)
    if request.method == 'POST':
        # Bind form to POST data and existing instance for update
        form = SchoolClassForm(request.POST, instance=school_class)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class updated successfully.')
            return redirect('class_list')
    else:
        # Pre-populate form with the existing class data
        form = SchoolClassForm(instance=school_class)
    return render(request, 'tracker/class_form.html', {'form': form, 'title': 'Edit Class'})


@login_required
@role_required(['admin', 'sysadmin'])
def class_delete_view(request, pk):
    """
    Handle deletion of a school class.

    Args:
        pk: Primary key of the SchoolClass to delete

    Only processes DELETE on POST request (for CSRF protection).
    Cascades to delete all students enrolled in the class.
    """
    school_class = get_object_or_404(SchoolClass, pk=pk)
    if request.method == 'POST':
        school_class.delete()
        messages.success(request, 'Class deleted successfully.')
        return redirect('class_list')
    # GET requests redirect back to class list (no confirmation page)
    return redirect('class_list')


# 
# Student CRUD Views
# 
@login_required
def student_list_view(request):
    """
    Display a filterable list of students.

    Role-based data access:
        - Admin: sees ALL students across all classes
        - Teacher: sees ONLY students in classes assigned to them

    Supports two query parameters for filtering:
        - search: Filter by student first or last name (case-insensitive)
        - class_id: Filter by school class ID

    Uses select_related('school_class') to avoid N+1 queries when
    displaying the class name for each student.
    """
    if request.user.profile.role in ('admin', 'sysadmin'):
        # Admin sees all students
        students = Student.objects.select_related('school_class')
    else:
        # Teacher sees only students in their assigned classes
        students = Student.objects.filter(
            school_class__teacher=request.user
        ).select_related('school_class')

    # Apply optional name search filter
    search = request.GET.get('search', '')
    if search:
        students = students.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
        )

    # Apply optional class filter
    class_filter = request.GET.get('class_id', '')
    if class_filter:
        students = students.filter(school_class_id=class_filter)

    # Provide all classes for the filter dropdown in the template
    classes = SchoolClass.objects.all()
    return render(request, 'tracker/student_list.html', {
        'students': students,
        'classes': classes,
        'search': search,               # Preserve search term in the form
        'class_filter': class_filter,    # Preserve selected class in the dropdown
    })


@login_required
@role_required(['admin', 'sysadmin'])
def student_create_view(request):
    """
    Handle adding a new student to the system.

    Only accessible by admins. Teachers can view students but cannot
    create, edit, or delete them (as per SRS requirements).

    GET:  Display an empty StudentForm
    POST: Validate and save the form, then redirect to the student list
    """
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully.')
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'tracker/student_form.html', {'form': form, 'title': 'Add Student'})


@login_required
@role_required(['admin', 'sysadmin'])
def student_edit_view(request, pk):
    """
    Handle editing an existing student's details.

    Args:
        pk: Primary key of the Student to edit

    GET:  Display the form pre-filled with the student's current data
    POST: Validate and save changes, then redirect to the student list
    """
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully.')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'tracker/student_form.html', {'form': form, 'title': 'Edit Student'})


@login_required
@role_required(['admin', 'sysadmin'])
def student_delete_view(request, pk):
    """
    Handle deletion of a student record.

    Args:
        pk: Primary key of the Student to delete

    Only processes on POST (CSRF protection). Cascading deletes will
    also remove the student's attendance records and SMS notifications.
    """
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully.')
        return redirect('student_list')
    return redirect('student_list')


# 
# Attendance Recording View
# 
@login_required
@role_required(['teacher', 'admin', 'sysadmin'])
def attendance_record_view(request):
    """
    Handle bulk attendance recording for an entire class at once.

    This is the most complex view in the application. It implements a
    two-step flow:

    Step 1 (GET): Teacher selects a class and date
        - Displays a dropdown of available classes
        - If class_id is provided as a query parameter, loads all students
          in that class and shows radio buttons (present/absent/late) for each
        - Pre-fills radio buttons if attendance was already recorded that day

    Step 2 (POST): Teacher submits the attendance form
        - Iterates through each student in the selected class
        - Creates an AttendanceRecord for each student
        - If a record already exists for that student/date, creates a
          correction record instead (audit trail per SRS NFR-4)
        - Triggers a mock SMS notification for each absent student
        - Redirects to the attendance list with a summary message

    Role-based class filtering:
        - Teachers only see classes assigned to them
        - Admins see all classes
    """
    user = request.user

    # Determine which classes to show based on role
    if user.profile.role == 'teacher':
        classes = SchoolClass.objects.filter(teacher=user)
    else:
        classes = SchoolClass.objects.all()

    if request.method == 'POST':
        # - Process the submitted attendance form -
        class_id = request.POST.get('class_id')
        date_str = request.POST.get('date')
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        students = school_class.students.all()

        recorded_count = 0  # Track how many records were created
        absent_count = 0    # Track how many SMS notifications were sent

        for student in students:
            # Each student's status comes from a radio button named 'status_<id>'
            status = request.POST.get(f'status_{student.id}')
            if status in ['present', 'absent', 'late']:
                # Check if attendance was already recorded for this student/date
                # Only look at uncorrected records (corrections__isnull=True)
                existing = AttendanceRecord.objects.filter(
                    student=student,
                    date=date_str,
                    corrections__isnull=True,
                ).first()

                if existing:
                    # Create a correction record that supersedes the existing one
                    # The original record is preserved for audit purposes
                    AttendanceRecord.objects.create(
                        student=student,
                        date=date_str,
                        status=status,
                        recorded_by=user,
                        is_correction=True,   # Flagged as a correction
                        corrects=existing,    # Links to the original record
                    )
                else:
                    # Create a new attendance record (first entry for this day)
                    AttendanceRecord.objects.create(
                        student=student,
                        date=date_str,
                        status=status,
                        recorded_by=user,
                    )

                recorded_count += 1

                # Send mock SMS notification to parent if student is absent
                if status == 'absent':
                    send_sms(student, reason="absent")
                    absent_count += 1

        # Show a success message with a summary of what was recorded
        messages.success(
            request,
            f'Attendance recorded for {recorded_count} students in {school_class.name}. '
            f'{absent_count} absence notification(s) sent.'
        )
        return redirect('attendance_list')

    # - GET request: display the attendance form -
    class_id = request.GET.get('class_id')
    date_str = request.GET.get('date', timezone.now().date().isoformat())

    context = {
        'classes': classes,
        'selected_class': None,
        'students': None,
        'date': date_str,
        'existing_records': {},  # Map of student_id -> existing record
    }

    if class_id:
        # A class was selected — load students and any existing records
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        students = school_class.students.all()

        # Check for existing (uncorrected) attendance records for this class/date
        # This allows pre-filling radio buttons if attendance was already taken
        existing = AttendanceRecord.objects.filter(
            student__school_class=school_class,
            date=date_str,
            corrections__isnull=True,
        )
        # Build a dict mapping student_id -> record for easy template lookup
        existing_map = {r.student_id: r for r in existing}

        context.update({
            'selected_class': school_class,
            'students': students,
            'existing_records': existing_map,
        })

    return render(request, 'tracker/attendance_form.html', context)


# 
# Attendance List View
# 
@login_required
def attendance_list_view(request):
    """
    Display a filterable log of all attendance records.

    Role-based data access:
        - Admin: sees ALL attendance records
        - Teacher: sees ONLY records for students in their assigned classes

    Only shows the latest (uncorrected) version of each record by filtering
    with `corrections__isnull=True`. Corrected records are hidden but
    preserved in the database for audit purposes.

    Supports filtering by:
        - class_id:  Filter by school class
        - date_from: Start date (inclusive)
        - date_to:   End date (inclusive)
        - status:    Filter by present/absent/late

    Results are capped at 200 records to prevent excessive page load times.
    Uses select_related() to join student, class, and user tables in one query.
    """
    if request.user.profile.role in ('admin', 'sysadmin'):
        # Admin sees all uncorrected records
        records = AttendanceRecord.objects.filter(corrections__isnull=True)
    else:
        # Teacher sees only their students' uncorrected records
        records = AttendanceRecord.objects.filter(
            student__school_class__teacher=request.user,
            corrections__isnull=True,
        )

    # Optimize queries by joining related tables (avoids N+1 problem)
    records = records.select_related('student', 'student__school_class', 'recorded_by')

    # Apply optional filters from query parameters
    class_filter = request.GET.get('class_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    if class_filter:
        records = records.filter(student__school_class_id=class_filter)
    if date_from:
        records = records.filter(date__gte=date_from)  # Greater than or equal
    if date_to:
        records = records.filter(date__lte=date_to)    # Less than or equal
    if status_filter:
        records = records.filter(status=status_filter)

    # Provide all classes for the filter dropdown
    classes = SchoolClass.objects.all()
    return render(request, 'tracker/attendance_list.html', {
        'records': records[:200],        # Cap at 200 records for performance
        'classes': classes,
        'class_filter': class_filter,    # Preserve filter selections in the form
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
    })


# 
# Attendance Edit View (Correction with Audit Trail)
# 
@login_required
@role_required(['teacher', 'admin', 'sysadmin'])
def attendance_edit_view(request, pk):
    """
    Handle editing (correcting) an existing attendance record.

    IMPORTANT: This does NOT modify the original record. Instead, it creates
    a new 'correction' record that supersedes the original. This implements
    the immutable audit trail required by SRS NFR-4.

    Args:
        pk: Primary key of the original AttendanceRecord to correct

    GET:  Display the current record with a dropdown to select the new status
    POST: Create a correction record and redirect to the attendance list

    The correction record:
        - Links to the original via `corrects` ForeignKey
        - Has `is_correction=True`
        - Records the current user as `recorded_by` (who made the change)

    If the new status is 'absent', a mock SMS is sent to the parent.
    """
    original_record = get_object_or_404(AttendanceRecord, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        # Only create a correction if the status actually changed
        if new_status in ['present', 'absent', 'late'] and new_status != original_record.status:
            # Create the correction record (original remains untouched)
            AttendanceRecord.objects.create(
                student=original_record.student,
                date=original_record.date,
                status=new_status,
                recorded_by=request.user,
                is_correction=True,
                corrects=original_record,  # Link to original for audit trail
            )

            # Send SMS if the corrected status is now absent
            if new_status == 'absent':
                send_mock_sms(original_record.student, reason="absent")

            messages.success(
                request,
                f'Attendance corrected for {original_record.student} on {original_record.date}.'
            )
        return redirect('attendance_list')

    return render(request, 'tracker/attendance_edit.html', {'record': original_record})


# 
# Reports View
# 
@login_required
def report_view(request):
    """
    Generate and display attendance statistics and reports.

    Provides two levels of reporting:

    1. Per-Student Summary:
        - Total attendance records per student
        - Breakdown of present, absent, and late counts
        - Attendance percentage (present / total * 100)
        - Uses Django ORM's annotate() with Count + Q for conditional aggregation

    2. Overall Summary:
        - Total records across all (filtered) students
        - Aggregate present/absent/late counts
        - Overall attendance percentage
        - Uses Django ORM's aggregate() for system-wide totals

    Role-based filtering:
        - Admin: sees all students' data
        - Teacher: sees only their assigned students' data

    Supports filtering by:
        - class_id:  Filter by school class
        - date_from: Start date (inclusive)
        - date_to:   End date (inclusive)

    Only includes uncorrected records (corrections__isnull=True) to ensure
    accurate statistics that reflect the most current attendance status.
    """
    # Start with all uncorrected attendance records
    records = AttendanceRecord.objects.filter(corrections__isnull=True)

    # Teachers can only see reports for their own students
    if request.user.profile.role == 'teacher':
        records = records.filter(student__school_class__teacher=request.user)

    # Apply optional date and class filters
    class_filter = request.GET.get('class_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if class_filter:
        records = records.filter(student__school_class_id=class_filter)
    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)

    # - Per-Student Summary -
    # Group records by student, counting total and conditional counts per status
    # Uses Django's conditional aggregation: Count('id', filter=Q(status='x'))
    student_stats = list(records.values(
        'student__id', 'student__first_name', 'student__last_name',
        'student__school_class__name'
    ).annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late')),
    ).order_by('student__last_name', 'student__first_name'))

    # Calculate attendance percentage for each student
    for stat in student_stats:
        if stat['total'] > 0:
            stat['attendance_pct'] = round(stat['present'] / stat['total'] * 100)
        else:
            stat['attendance_pct'] = 0

    # - Overall Summary -
    # Aggregate totals across all filtered records (not grouped by student)
    overall = records.aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late')),
    )

    # Calculate overall attendance percentage
    if overall['total'] and overall['total'] > 0:
        overall['attendance_pct'] = round(overall['present'] / overall['total'] * 100)
    else:
        overall['attendance_pct'] = 0

    # Provide classes for the filter dropdown (scoped by role)
    if request.user.profile.role in ('admin', 'sysadmin'):
        classes = SchoolClass.objects.all()
    else:
        classes = SchoolClass.objects.filter(teacher=request.user)

    return render(request, 'tracker/report.html', {
        'student_stats': student_stats,  # List of per-student statistics
        'overall': overall,              # Aggregate totals across all students
        'classes': classes,              # Classes for the filter dropdown
        'class_filter': class_filter,    # Preserve filter selections
        'date_from': date_from,
        'date_to': date_to,
    })


#
# Printable Attendance Report View
#
@login_required
@role_required(['admin', 'sysadmin', 'teacher'])
def report_print_view(request):
    """
    Generate a printable attendance report that opens in a new window.
    Uses the same filtering logic as report_view but renders a standalone
    print-friendly template without the navbar/footer.
    """
    records = AttendanceRecord.objects.filter(corrections__isnull=True)

    if request.user.profile.role == 'teacher':
        records = records.filter(student__school_class__teacher=request.user)

    class_filter = request.GET.get('class_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    class_name = ''
    if class_filter:
        records = records.filter(student__school_class_id=class_filter)
        try:
            class_name = SchoolClass.objects.get(id=class_filter).name
        except SchoolClass.DoesNotExist:
            pass
    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)

    student_stats = list(records.values(
        'student__id', 'student__first_name', 'student__last_name',
        'student__school_class__name'
    ).annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late')),
    ).order_by('student__last_name', 'student__first_name'))

    for stat in student_stats:
        if stat['total'] > 0:
            stat['attendance_pct'] = round(stat['present'] / stat['total'] * 100)
        else:
            stat['attendance_pct'] = 0

    overall = records.aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late')),
    )

    if overall['total'] and overall['total'] > 0:
        overall['attendance_pct'] = round(overall['present'] / overall['total'] * 100)
    else:
        overall['attendance_pct'] = 0

    return render(request, 'tracker/report_print.html', {
        'student_stats': student_stats,
        'overall': overall,
        'class_name': class_name,
        'date_from': date_from,
        'date_to': date_to,
    })


#
# SMS Notification Log View (Admin Only)
#
@login_required
@role_required(['admin', 'sysadmin'])
def notification_log_view(request):
    """
    Display the SMS notification log for admin review.

    Shows the most recent 100 SMS notifications (simulated), including:
        - Student name and class
        - Parent phone number
        - Message content
        - Timestamp and delivery status

    Uses select_related() to join student and class tables in a single
    query for efficient rendering. Only accessible by admins.
    """
    # Fetch recent notifications with related student/class data pre-loaded
    notifications = SMSNotification.objects.select_related('student', 'student__school_class')[:100]
    return render(request, 'tracker/notification_log.html', {'notifications': notifications})


# 
# Grade Recording Views
# 
@login_required
@role_required(['teacher', 'admin', 'sysadmin'])
def grade_record_view(request):
    """Handle recording grades for students in a class."""
    user = request.user

    if user.profile.role == 'teacher':
        classes = SchoolClass.objects.filter(teacher=user)
    else:
        classes = SchoolClass.objects.all()

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        subject = request.POST.get('subject')
        term = request.POST.get('term')
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        students = school_class.students.all()

        recorded_count = 0
        for student in students:
            score = request.POST.get(f'score_{student.id}')
            if score:
                try:
                    score_val = float(score)
                except ValueError:
                    continue

                existing = GradeRecord.objects.filter(
                    student=student, subject=subject, term=term,
                    corrections__isnull=True,
                ).first()

                if existing:
                    GradeRecord.objects.create(
                        student=student, subject=subject, term=term,
                        score=score_val, recorded_by=user,
                        is_correction=True, corrects=existing,
                    )
                else:
                    GradeRecord.objects.create(
                        student=student, subject=subject, term=term,
                        score=score_val, recorded_by=user,
                    )
                recorded_count += 1

        messages.success(request, f'Grades recorded for {recorded_count} students in {school_class.name}.')
        return redirect('grade_list')

    class_id = request.GET.get('class_id')
    subject = request.GET.get('subject', '')
    term = request.GET.get('term', 'term1')
    context = {
        'classes': classes,
        'selected_class': None,
        'students': None,
        'subject': subject,
        'term': term,
        'existing_grades': {},
        'term_choices': GradeRecord.TERM_CHOICES,
    }

    if class_id and subject:
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        students = school_class.students.all()
        existing = GradeRecord.objects.filter(
            student__school_class=school_class, subject=subject,
            term=term, corrections__isnull=True,
        )
        existing_map = {r.student_id: r for r in existing}
        context.update({
            'selected_class': school_class,
            'students': students,
            'existing_grades': existing_map,
        })

    return render(request, 'tracker/grade_form.html', context)


@login_required
def grade_list_view(request):
    """Display a filterable list of grade records."""
    if request.user.profile.role in ('admin', 'sysadmin'):
        records = GradeRecord.objects.filter(corrections__isnull=True)
    elif request.user.profile.role == 'teacher':
        records = GradeRecord.objects.filter(
            student__school_class__teacher=request.user,
            corrections__isnull=True,
        )
    else:
        # Parent: only see their children's grades
        children_ids = request.user.profile.children.values_list('id', flat=True)
        records = GradeRecord.objects.filter(
            student_id__in=children_ids,
            corrections__isnull=True,
        )

    records = records.select_related('student', 'student__school_class', 'recorded_by')

    class_filter = request.GET.get('class_id', '')
    subject_filter = request.GET.get('subject', '')
    term_filter = request.GET.get('term', '')

    if class_filter:
        records = records.filter(student__school_class_id=class_filter)
    if subject_filter:
        records = records.filter(subject__icontains=subject_filter)
    if term_filter:
        records = records.filter(term=term_filter)

    classes = SchoolClass.objects.all()
    return render(request, 'tracker/grade_list.html', {
        'records': records[:200],
        'classes': classes,
        'class_filter': class_filter,
        'subject_filter': subject_filter,
        'term_filter': term_filter,
        'term_choices': GradeRecord.TERM_CHOICES,
    })


@login_required
@role_required(['teacher', 'admin', 'sysadmin'])
def grade_edit_view(request, pk):
    """Handle correcting an existing grade record (immutable audit trail)."""
    original_record = get_object_or_404(GradeRecord, pk=pk)

    if request.method == 'POST':
        new_score = request.POST.get('score')
        try:
            new_score_val = float(new_score)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid score.')
            return redirect('grade_list')

        if new_score_val != float(original_record.score):
            GradeRecord.objects.create(
                student=original_record.student,
                subject=original_record.subject,
                term=original_record.term,
                score=new_score_val,
                recorded_by=request.user,
                is_correction=True,
                corrects=original_record,
            )
            messages.success(
                request,
                f'Grade corrected for {original_record.student} in {original_record.subject}.'
            )
        return redirect('grade_list')

    return render(request, 'tracker/grade_edit.html', {'record': original_record})


# 
# Grade Reports View
# 
@login_required
def grade_report_view(request):
    """Generate and display grade statistics per student."""
    from django.db.models import Avg, Max, Min

    records = GradeRecord.objects.filter(corrections__isnull=True)

    if request.user.profile.role == 'teacher':
        records = records.filter(student__school_class__teacher=request.user)
    elif request.user.profile.role == 'parent':
        children_ids = request.user.profile.children.values_list('id', flat=True)
        records = records.filter(student_id__in=children_ids)

    class_filter = request.GET.get('class_id', '')
    term_filter = request.GET.get('term', '')
    subject_filter = request.GET.get('subject', '')

    if class_filter:
        records = records.filter(student__school_class_id=class_filter)
    if term_filter:
        records = records.filter(term=term_filter)
    if subject_filter:
        records = records.filter(subject__icontains=subject_filter)

    student_stats = list(records.values(
        'student__id', 'student__first_name', 'student__last_name',
        'student__school_class__name'
    ).annotate(
        avg_score=Avg('score'),
        max_score=Max('score'),
        min_score=Min('score'),
        total_grades=Count('id'),
    ).order_by('student__last_name', 'student__first_name'))

    for stat in student_stats:
        stat['avg_score'] = round(float(stat['avg_score']), 1) if stat['avg_score'] else 0

    overall = records.aggregate(
        avg_score=Avg('score'),
        total_grades=Count('id'),
    )
    if overall['avg_score']:
        overall['avg_score'] = round(float(overall['avg_score']), 1)
    else:
        overall['avg_score'] = 0

    if request.user.profile.role in ('admin', 'sysadmin'):
        classes = SchoolClass.objects.all()
    elif request.user.profile.role == 'teacher':
        classes = SchoolClass.objects.filter(teacher=request.user)
    else:
        classes = SchoolClass.objects.filter(
            students__in=request.user.profile.children.all()
        ).distinct()

    return render(request, 'tracker/grade_report.html', {
        'student_stats': student_stats,
        'overall': overall,
        'classes': classes,
        'class_filter': class_filter,
        'term_filter': term_filter,
        'subject_filter': subject_filter,
        'term_choices': GradeRecord.TERM_CHOICES,
    })


#
# Printable Grade Report View
#
@login_required
@role_required(['admin', 'sysadmin', 'teacher', 'parent'])
def grade_report_print_view(request):
    """
    Generate a printable grade report that opens in a new window.
    Uses the same filtering logic as grade_report_view but renders a standalone
    print-friendly template without the navbar/footer.
    """
    from django.db.models import Avg, Max, Min

    records = GradeRecord.objects.filter(corrections__isnull=True)

    if request.user.profile.role == 'teacher':
        records = records.filter(student__school_class__teacher=request.user)
    elif request.user.profile.role == 'parent':
        children_ids = request.user.profile.children.values_list('id', flat=True)
        records = records.filter(student_id__in=children_ids)

    class_filter = request.GET.get('class_id', '')
    term_filter = request.GET.get('term', '')
    subject_filter = request.GET.get('subject', '')

    class_name = ''
    if class_filter:
        records = records.filter(student__school_class_id=class_filter)
        try:
            class_name = SchoolClass.objects.get(id=class_filter).name
        except SchoolClass.DoesNotExist:
            pass
    if term_filter:
        records = records.filter(term=term_filter)
    if subject_filter:
        records = records.filter(subject__icontains=subject_filter)

    # Resolve term display name
    term_name = ''
    if term_filter:
        term_dict = dict(GradeRecord.TERM_CHOICES)
        term_name = term_dict.get(term_filter, term_filter)

    student_stats = list(records.values(
        'student__id', 'student__first_name', 'student__last_name',
        'student__school_class__name'
    ).annotate(
        avg_score=Avg('score'),
        max_score=Max('score'),
        min_score=Min('score'),
        total_grades=Count('id'),
    ).order_by('student__last_name', 'student__first_name'))

    for stat in student_stats:
        stat['avg_score'] = round(float(stat['avg_score']), 1) if stat['avg_score'] else 0

    overall = records.aggregate(
        avg_score=Avg('score'),
        total_grades=Count('id'),
    )
    if overall['avg_score']:
        overall['avg_score'] = round(float(overall['avg_score']), 1)
    else:
        overall['avg_score'] = 0

    return render(request, 'tracker/grade_report_print.html', {
        'student_stats': student_stats,
        'overall': overall,
        'class_name': class_name,
        'term_name': term_name,
        'subject_filter': subject_filter,
    })


#
# Parent Portal Views
#
@login_required
@role_required(['parent'])
def parent_attendance_view(request):
    """Read-only view for parents to see their children's attendance records."""
    children = request.user.profile.children.all()
    children_ids = children.values_list('id', flat=True)

    records = AttendanceRecord.objects.filter(
        student_id__in=children_ids,
        corrections__isnull=True,
    ).select_related('student', 'student__school_class').order_by('-date')

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)

    return render(request, 'tracker/parent_attendance.html', {
        'records': records[:200],
        'children': children,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
@role_required(['parent'])
def parent_grades_view(request):
    """Read-only view for parents to see their children's grades."""
    children = request.user.profile.children.all()
    children_ids = children.values_list('id', flat=True)

    records = GradeRecord.objects.filter(
        student_id__in=children_ids,
        corrections__isnull=True,
    ).select_related('student', 'student__school_class').order_by('student__last_name', 'subject')

    term_filter = request.GET.get('term', '')
    if term_filter:
        records = records.filter(term=term_filter)

    return render(request, 'tracker/parent_grades.html', {
        'records': records[:200],
        'children': children,
        'term_filter': term_filter,
        'term_choices': GradeRecord.TERM_CHOICES,
    })
