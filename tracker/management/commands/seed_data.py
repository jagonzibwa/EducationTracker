"""
tracker/management/commands/seed_data.py - Database Seed Data Command

A Django management command that populates the database with realistic test
data for development and demonstration purposes. Creates sample users,
school classes, and students with Ugandan names and phone numbers.

Usage:
    python manage.py seed_data

What it creates:
    Users:
        - admin1 / admin123   (Administrator role)
        - teacher1 / teacher123 (Teacher role - Jane Nakato)
        - teacher2 / teacher123 (Teacher role - John Okello)

    Classes:
        - Primary 5A (assigned to teacher1)
        - Primary 6B (assigned to teacher1)
        - Primary 7A (assigned to teacher2)

    Students:
        - 12 students with Ugandan names distributed across the 3 classes
        - Each student has a parent name and Uganda-format phone number (+256...)

Notes:
    - Uses get_or_create() to safely re-run without creating duplicates
    - UserProfile objects are automatically created via Django signals
      (see accounts/signals.py), so we just update the role after creation
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import SchoolClass, Student


class Command(BaseCommand):
    """Django management command to seed the database with test data."""

    # Help text shown when running: python manage.py help seed_data
    help = 'Seed the database with test data for Education Tracker'

    def handle(self, *args, **options):
        """
        Main command logic — creates users, classes, and students.

        Uses get_or_create() for idempotency: running the command multiple
        times will not create duplicate records.
        """

        # 
        # Create Admin User
        # 
        # get_or_create returns (object, was_created_bool)
        admin_user, created = User.objects.get_or_create(
            username='admin1',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@school.ug',
            }
        )
        if created:
            # Set password (hashed) — can't be done in get_or_create defaults
            admin_user.set_password('admin123')
            admin_user.save()
            # Update the auto-created profile's role from default 'teacher' to 'admin'
            admin_user.profile.role = 'admin'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin1 / admin123'))
        else:
            self.stdout.write('Admin user already exists.')

        # 
        # Create First Teacher User
        # 
        teacher_user, created = User.objects.get_or_create(
            username='teacher1',
            defaults={
                'first_name': 'Jane',
                'last_name': 'Nakato',
                'email': 'jane@school.ug',
            }
        )
        if created:
            teacher_user.set_password('teacher123')
            teacher_user.save()
            # Role defaults to 'teacher' via signal, but set explicitly for clarity
            teacher_user.profile.role = 'teacher'
            teacher_user.profile.save()
            self.stdout.write(self.style.SUCCESS('Created teacher user: teacher1 / teacher123'))
        else:
            self.stdout.write('Teacher user already exists.')

        # 
        # Create Second Teacher User
        # 
        teacher2, created = User.objects.get_or_create(
            username='teacher2',
            defaults={
                'first_name': 'John',
                'last_name': 'Okello',
                'email': 'john@school.ug',
            }
        )
        if created:
            teacher2.set_password('teacher123')
            teacher2.save()
            teacher2.profile.role = 'teacher'
            teacher2.profile.save()
            self.stdout.write(self.style.SUCCESS('Created teacher user: teacher2 / teacher123'))

        # 
        # Create School Classes
        # 
        # Each class is assigned to a teacher via the 'teacher' ForeignKey
        p5, _ = SchoolClass.objects.get_or_create(
            name='Primary 5A', defaults={'teacher': teacher_user}
        )
        p6, _ = SchoolClass.objects.get_or_create(
            name='Primary 6B', defaults={'teacher': teacher_user}
        )
        p7, _ = SchoolClass.objects.get_or_create(
            name='Primary 7A', defaults={'teacher': teacher2}
        )
        self.stdout.write(self.style.SUCCESS('Created 3 school classes'))

        # 
        # Create Students
        # 
        # Student data: (first_name, last_name, class, parent_name, phone)
        # All names are common Ugandan names; phone numbers use Uganda's +256 format
        students_data = [
            # Primary 5A students (5 students)
            ('Amina', 'Nakamya', p5, 'Sarah Nakamya', '+256700100001'),
            ('Brian', 'Mugisha', p5, 'David Mugisha', '+256700100002'),
            ('Claire', 'Atim', p5, 'Grace Atim', '+256700100003'),
            ('Daniel', 'Ouma', p5, 'Peter Ouma', '+256700100004'),
            ('Esther', 'Namutebi', p5, 'Joseph Namutebi', '+256700100005'),
            # Primary 6B students (4 students)
            ('Francis', 'Kibuuka', p6, 'Mary Kibuuka', '+256700100006'),
            ('Gloria', 'Nassali', p6, 'Robert Nassali', '+256700100007'),
            ('Henry', 'Ssempala', p6, 'Agnes Ssempala', '+256700100008'),
            ('Irene', 'Achieng', p6, 'James Achieng', '+256700100009'),
            # Primary 7A students (3 students)
            ('James', 'Tumusiime', p7, 'Rose Tumusiime', '+256700100010'),
            ('Kate', 'Amongi', p7, 'Charles Amongi', '+256700100011'),
            ('Liam', 'Byaruhanga', p7, 'Florence Byaruhanga', '+256700100012'),
        ]

        created_count = 0
        for first, last, cls, parent, phone in students_data:
            # get_or_create uses first_name + last_name + school_class as lookup
            _, created = Student.objects.get_or_create(
                first_name=first,
                last_name=last,
                school_class=cls,
                defaults={'parent_name': parent, 'parent_phone': phone}
            )
            if created:
                created_count += 1

        # 
        # Print Summary
        # 
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} students'))
        self.stdout.write(self.style.SUCCESS('Seed data complete!'))
        self.stdout.write('')
        self.stdout.write('Test accounts:')
        self.stdout.write('  Admin:   admin1 / admin123')
        self.stdout.write('  Teacher: teacher1 / teacher123')
        self.stdout.write('  Teacher: teacher2 / teacher123')
