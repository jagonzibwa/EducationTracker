# Education Tracker

A web-based school management system built with Django for tracking student attendance, grades, and parent communication via SMS notifications.

## Features

- **User Authentication** — Registration and login with role-based access control
- **Role-Based Access** — Four user roles: Administrator, Teacher, Parent, System Administrator
- **Attendance Tracking** — Record daily attendance (present/absent/late) per class with immutable audit trail
- **Grade Management** — Record and track student grades by subject and term with correction history
- **Class-Wide Reports** — Attendance and grade reports with filtering by class, date range, subject, term, and individual student
- **Individual Student Reports** — Per-student attendance history, grade breakdown by subject, and combined printable report
- **Parent Portal** — Per-child summary cards linking to full individual reports; admins link students to parent accounts
- **Parent-Child Linking** — Admins assign students to parent accounts via the user edit form
- **SMS Notifications** — Automated absence alerts to parents via Africa's Talking API
- **User Management** — Admins can create, edit, deactivate, and manage user accounts with children count visible at a glance
- **30-Minute Session Timeout** — Auto-logout after inactivity for security

## Tech Stack

- **Backend:** Python 3.13, Django 5.2
- **Frontend:** Tailwind CSS (CDN), Django Templates
- **Database:** SQLite (development) / PostgreSQL (production)
- **SMS Gateway:** Africa's Talking API v2
- **Forms:** django-crispy-forms with Bootstrap 5 template pack

## Project Structure

```
EducationTracker/
├── accounts/                   # User auth, registration, profile, user management
│   ├── models.py               # UserProfile (roles, parent-child M2M linking)
│   ├── views.py                # Login, register, profile, CRUD user views
│   ├── forms.py                # Registration and admin user forms (incl. children field)
│   └── templates/accounts/     # Login, register, profile, user management templates
├── tracker/                    # Core app: attendance, grades, SMS, reports
│   ├── models.py               # SchoolClass, Student, AttendanceRecord, GradeRecord, SMSNotification
│   ├── views.py                # Dashboard, attendance, grades, reports, parent portal, individual student reports
│   ├── services.py             # SMS sending (Africa's Talking integration)
│   ├── management/commands/
│   │   └── seed_data.py        # Populates DB with users, classes, students, attendance, and grades
│   └── templates/tracker/      # All tracker templates including individual student report pages
├── education_tracker/          # Django project settings
│   ├── settings.py             # Configuration (DB, auth, sessions, SMS)
│   ├── urls.py                 # Root URL routing
│   └── wsgi.py                 # WSGI entry point
├── templates/                  # Shared templates (base.html, navbar.html)
├── static/                     # Static assets
├── build.sh                    # Render build script (install, migrate, seed)
├── manage.py                   # Django management entry point
└── requirements.txt            # Python dependencies
```

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jagonzibwa/EducationTracker.git
   cd EducationTracker
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Seed sample data:**
   ```bash
   python manage.py seed_data
   ```
   This creates all test accounts, 3 classes, 12 students, 38 days of attendance records (Term 1 2026), and grade records for Terms 1–3. Safe to re-run — skips records that already exist.

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Open in browser:** http://localhost:8000

## Test Accounts

| Username  | Password   | Role          | Notes                                      |
|-----------|------------|---------------|--------------------------------------------|
| admin1    | admin123   | Administrator |                                            |
| teacher1  | teacher123 | Teacher       | Assigned to Primary 5A and Primary 6B      |
| teacher2  | teacher123 | Teacher       | Assigned to Primary 7A                     |
| parent1   | parent123  | Parent        | Linked to Amina Nakamya and Brian Mugisha  |

## User Roles

| Role                     | Capabilities |
|--------------------------|-------------|
| **Administrator**        | Manage classes, students, and users (including linking students to parents). View all attendance, grades, reports, and SMS log. Record attendance and grades. |
| **Teacher**              | Record attendance and grades for assigned classes. View class-wide and individual student reports. |
| **Parent**               | View per-child attendance and grade summary cards. Click through to full individual reports for each linked child. Read-only. |
| **System Administrator** | Same as Administrator. Intended for system maintenance and security tasks. |

## Reports

### Class-Wide Reports
Available at `/reports/` (attendance) and `/grades/reports/` (grades). Filter by class, date range, subject, and term. A student dropdown lets you narrow the report to a single student, with a link to that student's individual report.

### Individual Student Reports
- `/reports/student/<id>/attendance/` — full day-by-day attendance history with date filter and summary stats
- `/reports/student/<id>/grades/` — grades grouped by subject with term/subject filter and summary stats
- `/reports/student/<id>/print/` — combined printable report (attendance + grades) with `@media print` CSS

Student names in class-wide report tables are clickable links to individual reports. The student list also has per-row Attendance and Grades links.

## SMS Configuration (Africa's Talking)

SMS notifications are sent automatically when a student is marked absent. By default, SMS is simulated (logged to the database only).

## PostgreSQL Configuration

By default the app uses SQLite. To use PostgreSQL, set the `DATABASE_URL` environment variable:

```bash
# macOS/Linux
export DATABASE_URL=postgres://user:password@localhost:5432/education_tracker

# Windows (Command Prompt)
set DATABASE_URL=postgres://user:password@localhost:5432/education_tracker
```

On Render, `DATABASE_URL` is set automatically when a PostgreSQL database is attached to the service.

## Key Design Decisions

- **Immutable Audit Trail:** Attendance and grade records are never modified or deleted. Corrections create new linked records (`corrects` FK), preserving the original for auditing. All queries filter `corrections__isnull=True` to show only the current effective record.
- **Role-Based Navigation:** The navbar and dashboard adapt based on the logged-in user's role, showing only relevant options.
- **Parent-Child Linking:** Parents are linked to students via a ManyToMany field on `UserProfile`. The student's `parent_name` and `parent_phone` fields are separate — used for SMS only — and are not affected by account linking.
- **SMS Fallback:** The SMS system degrades to simulation mode when API credentials are not configured, ensuring the app works without external dependencies.
- **Session Security:** 30-minute inactivity timeout with session reset on activity.

