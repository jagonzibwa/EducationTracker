"""
tracker/management/commands/seed_data.py - Database Seed Data Command

A Django management command that populates the database with realistic test
data for development and demonstration purposes. Creates sample users,
school classes, students, attendance records, and grade records.

Usage:
    python manage.py seed_data

What it creates:
    Users:
        - admin1   / admin123    (Administrator role)
        - teacher1 / teacher123  (Teacher - Jane Nakato, teaches P5A and P6B)
        - teacher2 / teacher123  (Teacher - John Okello, teaches P7A)
        - parent1  / parent123   (Parent - linked to Amina Nakamya & Brian Mugisha)

    Classes:
        - Primary 5A (teacher1)
        - Primary 6B (teacher1)
        - Primary 7A (teacher2)

    Students:
        - 12 students distributed across the 3 classes

    Attendance Records (Term 1 2026: Feb 3 – Mar 26):
        - 38 school days × 12 students = 456 records
        - Realistic patterns: most students 85–95% present;
          Daniel Ouma and Henry Ssempala have notably lower attendance
          to exercise the red badge on reports

    Grade Records:
        - Term 2 & 3 2025 (completed): all 4 subjects for all 12 students
        - Term 1 2026 (in progress): Mathematics and English only (midterm)
        - Subjects: Mathematics, English Language, Science, Social Studies

Notes:
    - Uses get_or_create() to safely re-run without creating duplicates
    - Attendance and grade records are skipped if any already exist
      (guarded by a single existence check per record type)
    - UserProfile objects are automatically created via Django signals
      (see accounts/signals.py), so we just update the role after creation
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from tracker.models import SchoolClass, Student, AttendanceRecord, GradeRecord


# 
# Helpers
# 

def _weekdays(start, end):
    """Return a list of all weekday dates between start and end (inclusive)."""
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:   # 0=Mon … 4=Fri
            days.append(d)
        d += timedelta(days=1)
    return days


#
# Calendar constants
#

# Uganda Term 1 2026: starts early February, running through May.
# We seed attendance up to the day before today (Mar 26) so all records
# are in the past and the percentage calculations look sensible.
TERM1_DAYS = _weekdays(date(2026, 2, 3), date(2026, 3, 26))   # 38 school days

SUBJECTS = ['Mathematics', 'English Language', 'Science', 'Social Studies']

# 
# Attendance patterns
# 
# For each student: (set_of_absent_day_indices, set_of_late_day_indices)
# Indices are 0-based into TERM1_DAYS (0 = Feb 3, 37 = Mar 26).
# Days not listed default to 'present'.
#
# Resulting attendance rates (present / total):
#   Amina    33/38 = 87%   Claire  34/38 = 89%   Francis 34/38 = 89%
#   Brian    33/38 = 87%   Daniel  30/38 = 79%   Gloria  35/38 = 92%
#   Esther   32/38 = 84%   Henry   28/38 = 74%   Irene   35/38 = 92%
#   James    33/38 = 87%   Kate    35/38 = 92%   Liam    34/38 = 89%
ATTENDANCE_PATTERNS = {
    ('Amina',   'Nakamya'):    (frozenset([5, 18, 31]),               frozenset([2, 12])),
    ('Brian',   'Mugisha'):    (frozenset([3, 25]),                   frozenset([7, 16, 29])),
    ('Claire',  'Atim'):       (frozenset([8, 22, 36]),               frozenset([1])),
    ('Daniel',  'Ouma'):       (frozenset([0, 10, 20, 30, 35, 37]),  frozenset([5, 15])),
    ('Esther',  'Namutebi'):   (frozenset([4, 12, 20, 28, 36]),      frozenset([8])),
    ('Francis', 'Kibuuka'):    (frozenset([2, 19]),                   frozenset([6, 24])),
    ('Gloria',  'Nassali'):    (frozenset(),                          frozenset([3, 11, 26])),
    ('Henry',   'Ssempala'):   (frozenset([1, 9, 15, 23, 29, 33]),   frozenset([5, 20, 31])),
    ('Irene',   'Achieng'):    (frozenset([6, 21]),                   frozenset([13])),
    ('James',   'Tumusiime'):  (frozenset([2, 14, 26]),               frozenset([7, 19])),
    ('Kate',    'Amongi'):     (frozenset(),                          frozenset([4, 18, 32])),
    ('Liam',    'Byaruhanga'): (frozenset([10, 22, 34]),              frozenset([2])),
}

# 
# Grade data
# 
# Each student has a base score; subject and term offsets shift it.
# Scores are clamped to [0, 100].
BASE_SCORES = {
    ('Amina',   'Nakamya'):    72,
    ('Brian',   'Mugisha'):    68,
    ('Claire',  'Atim'):       81,
    ('Daniel',  'Ouma'):       55,   # struggling - exercises red badge in reports
    ('Esther',  'Namutebi'):   76,
    ('Francis', 'Kibuuka'):    83,
    ('Gloria',  'Nassali'):    91,   # top student
    ('Henry',   'Ssempala'):   61,
    ('Irene',   'Achieng'):    79,
    ('James',   'Tumusiime'):  85,
    ('Kate',    'Amongi'):     88,
    ('Liam',    'Byaruhanga'): 77,
}

SUBJECT_OFFSETS = {
    'Mathematics':      -5,
    'English Language': +3,
    'Science':          -2,
    'Social Studies':   +2,
}

# term2/term3 = previous year (completed); term1 = current year (in progress)
TERM_OFFSETS = {
    'term2': -4,   # Term 2 2025 — oldest, slightly lower scores
    'term3':  0,   # Term 3 2025 — baseline
    'term1': +4,   # Term 1 2026 — improvement trend
}

# Midterm: only these subjects have been assessed in Term 1 2026 so far
TERM1_SUBJECTS = {'Mathematics', 'English Language'}


#
# Command
#

class Command(BaseCommand):
    help = 'Seed the database with test data for Education Tracker'

    def handle(self, *args, **options):

        # 
        # Users                                                                #
        # 

        admin_user, created = User.objects.get_or_create(
            username='admin1',
            defaults={'first_name': 'Admin', 'last_name': 'User', 'email': 'admin@school.ug'},
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            admin_user.profile.role = 'admin'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin1 / admin123'))
        else:
            self.stdout.write('Admin user already exists.')

        teacher1, created = User.objects.get_or_create(
            username='teacher1',
            defaults={'first_name': 'Jane', 'last_name': 'Nakato', 'email': 'jane@school.ug'},
        )
        if created:
            teacher1.set_password('teacher123')
            teacher1.save()
            teacher1.profile.role = 'teacher'
            teacher1.profile.save()
            self.stdout.write(self.style.SUCCESS('Created teacher user: teacher1 / teacher123'))
        else:
            self.stdout.write('Teacher1 user already exists.')

        teacher2, created = User.objects.get_or_create(
            username='teacher2',
            defaults={'first_name': 'John', 'last_name': 'Okello', 'email': 'john@school.ug'},
        )
        if created:
            teacher2.set_password('teacher123')
            teacher2.save()
            teacher2.profile.role = 'teacher'
            teacher2.profile.save()
            self.stdout.write(self.style.SUCCESS('Created teacher user: teacher2 / teacher123'))
        else:
            self.stdout.write('Teacher2 user already exists.')

        parent1, created = User.objects.get_or_create(
            username='parent1',
            defaults={'first_name': 'Sarah', 'last_name': 'Nakamya', 'email': 'sarah@school.ug'},
        )
        if created:
            parent1.set_password('parent123')
            parent1.save()
            parent1.profile.role = 'parent'
            parent1.profile.save()
            self.stdout.write(self.style.SUCCESS('Created parent user: parent1 / parent123'))
        else:
            self.stdout.write('Parent user already exists.')

        # ------------------------------------------------------------------ #
        # Classes                                                              #
        # ------------------------------------------------------------------ #

        p5, _ = SchoolClass.objects.get_or_create(name='Primary 5A', defaults={'teacher': teacher1})
        p6, _ = SchoolClass.objects.get_or_create(name='Primary 6B', defaults={'teacher': teacher1})
        p7, _ = SchoolClass.objects.get_or_create(name='Primary 7A', defaults={'teacher': teacher2})
        self.stdout.write(self.style.SUCCESS('School classes ready (Primary 5A, 6B, 7A)'))

        # 
        # Students                                                             #
        # 

        students_data = [
            # Primary 5A (teacher1)
            ('Amina',   'Nakamya',    p5, 'Sarah Nakamya',     '+256700100001'),
            ('Brian',   'Mugisha',    p5, 'David Mugisha',     '+256700100002'),
            ('Claire',  'Atim',       p5, 'Grace Atim',        '+256700100003'),
            ('Daniel',  'Ouma',       p5, 'Peter Ouma',        '+256700100004'),
            ('Esther',  'Namutebi',   p5, 'Joseph Namutebi',   '+256700100005'),
            # Primary 6B (teacher1)
            ('Francis', 'Kibuuka',    p6, 'Mary Kibuuka',      '+256700100006'),
            ('Gloria',  'Nassali',    p6, 'Robert Nassali',    '+256700100007'),
            ('Henry',   'Ssempala',   p6, 'Agnes Ssempala',    '+256700100008'),
            ('Irene',   'Achieng',    p6, 'James Achieng',     '+256700100009'),
            # Primary 7A (teacher2)
            ('James',   'Tumusiime',  p7, 'Rose Tumusiime',    '+256700100010'),
            ('Kate',    'Amongi',     p7, 'Charles Amongi',    '+256700100011'),
            ('Liam',    'Byaruhanga', p7, 'Florence Byaruhanga', '+256700100012'),
        ]

        created_count = 0
        for first, last, cls, parent, phone in students_data:
            _, was_created = Student.objects.get_or_create(
                first_name=first, last_name=last, school_class=cls,
                defaults={'parent_name': parent, 'parent_phone': phone},
            )
            if was_created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f'Students ready ({created_count} newly created)'))

        # Link parent1 to their children (Amina and Brian in P5A)
        amina = Student.objects.filter(first_name='Amina', last_name='Nakamya').first()
        brian = Student.objects.filter(first_name='Brian',  last_name='Mugisha').first()
        if amina and brian:
            parent1.profile.children.set([amina, brian])

        # 
        # Attendance Records — Term 1 2026 (38 school days, Feb 3 – Mar 26)  #
        # 

        all_students = Student.objects.select_related('school_class').all()

        if AttendanceRecord.objects.filter(student__in=all_students).exists():
            self.stdout.write('Attendance records already exist, skipping.')
        else:
            att_count = 0
            # Map class name -> recorder so each teacher records their own class
            recorder_map = {
                'Primary 5A': teacher1,
                'Primary 6B': teacher1,
                'Primary 7A': teacher2,
            }

            for student in all_students:
                key = (student.first_name, student.last_name)
                absent_idx, late_idx = ATTENDANCE_PATTERNS.get(key, (frozenset(), frozenset()))
                recorder = recorder_map.get(student.school_class.name, teacher1)

                records = []
                for i, day in enumerate(TERM1_DAYS):
                    if i in absent_idx:
                        status = 'absent'
                    elif i in late_idx:
                        status = 'late'
                    else:
                        status = 'present'
                    records.append(AttendanceRecord(
                        student=student, date=day, status=status, recorded_by=recorder,
                    ))
                AttendanceRecord.objects.bulk_create(records)
                att_count += len(records)

            self.stdout.write(self.style.SUCCESS(
                f'Created {att_count} attendance records '
                f'({len(TERM1_DAYS)} days × {all_students.count()} students)'
            ))

        #
        # Grade Records — Term 2 & 3 2025 (complete) + Term 1 2026 (midterm) #
        #

        if GradeRecord.objects.filter(student__in=all_students).exists():
            self.stdout.write('Grade records already exist, skipping.')
        else:
            grade_count = 0
            recorder_map = {
                'Primary 5A': teacher1,
                'Primary 6B': teacher1,
                'Primary 7A': teacher2,
            }

            records = []
            for student in all_students:
                key = (student.first_name, student.last_name)
                base = BASE_SCORES.get(key, 70)
                recorder = recorder_map.get(student.school_class.name, teacher1)

                for term, term_off in TERM_OFFSETS.items():
                    subjects = TERM1_SUBJECTS if term == 'term1' else set(SUBJECTS)
                    for subject in SUBJECTS:
                        if subject not in subjects:
                            continue
                        score = max(0, min(100,
                            base + SUBJECT_OFFSETS[subject] + term_off
                        ))
                        records.append(GradeRecord(
                            student=student, subject=subject, term=term,
                            score=score, recorded_by=recorder,
                        ))

            GradeRecord.objects.bulk_create(records)
            grade_count = len(records)

            self.stdout.write(self.style.SUCCESS(
                f'Created {grade_count} grade records '
                f'(term2+term3: 4 subjects each; term1: 2 subjects midterm)'
            ))

        #
        # Summary                                                              #
        #

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seed data complete!'))
        self.stdout.write('')
        self.stdout.write('Test accounts:')
        self.stdout.write('  Admin:   admin1   / admin123')
        self.stdout.write('  Teacher: teacher1 / teacher123  (Primary 5A, 6B)')
        self.stdout.write('  Teacher: teacher2 / teacher123  (Primary 7A)')
        self.stdout.write('  Parent:  parent1  / parent123   (Amina Nakamya, Brian Mugisha)')
        self.stdout.write('')
        self.stdout.write('Seeded data summary:')
        self.stdout.write(f'  School days (Term 1 2026): {len(TERM1_DAYS)}  '
                          f'(Feb 3 – Mar 26 2026)')
        self.stdout.write('  Subjects: Mathematics, English Language, Science, Social Studies')
        self.stdout.write('  Terms with grades: Term 2 2025, Term 3 2025, Term 1 2026 (midterm)')
