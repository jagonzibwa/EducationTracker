# Education Tracker

A web-based school management system built with Django for tracking student attendance, grades, and parent communication via SMS notifications.

## Features

- **User Authentication** — Registration and login with role-based access control
- **Role-Based Access** — Four user roles: Administrator, Teacher, Parent, System Administrator
- **Attendance Tracking** — Record daily attendance (present/absent/late) per class with immutable audit trail
- **Grade Management** — Record and track student grades by subject and term with correction history
- **Parent Portal** — Read-only dashboard for parents to view their children's attendance and grades
- **SMS Notifications** — Automated absence alerts to parents via Africa's Talking API
- **User Management** — Admins can create, edit, and deactivate user accounts
- **Reports** — Attendance statistics and grade reports with filtering by class, date range, subject, and term
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
├── accounts/               # User auth, registration, profile, user management
│   ├── models.py           # UserProfile (roles, parent-child linking)
│   ├── views.py            # Login, register, profile, CRUD user views
│   ├── forms.py            # Registration and admin user forms
│   └── templates/accounts/ # Login, register, profile, user management templates
├── tracker/                # Core app: attendance, grades, SMS, reports
│   ├── models.py           # SchoolClass, Student, AttendanceRecord, GradeRecord, SMSNotification
│   ├── views.py            # Dashboard, attendance, grades, reports, parent portal
│   ├── services.py         # SMS sending (Africa's Talking integration)
│   └── templates/tracker/  # Dashboard, attendance, grade, report templates
├── education_tracker/      # Django project settings
│   ├── settings.py         # Configuration (DB, auth, sessions, SMS)
│   ├── urls.py             # Root URL routing
│   └── wsgi.py             # WSGI entry point
├── templates/              # Shared templates (base.html, navbar.html)
├── static/                 # Static assets
├── manage.py               # Django management command
└── requirements.txt        # Python dependencies
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

5. **Create a superuser (optional, for Django admin access):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Seed sample data (optional):**
   ```bash
   python manage.py seed_data
   ```

7. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

8. **Open in browser:** http://localhost:8000

## Default Test Accounts

| Username  | Password   | Role          |
|-----------|------------|---------------|
| admin1    | admin123   | Administrator |
| teacher1  | teacher123 | Teacher       |
| teacher2  | teacher123 | Teacher       |
| parent1   | parent123  | Parent        |

## User Roles

| Role                 | Capabilities                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| **Administrator**    | Manage classes, students, users. View all attendance/grades/reports/SMS log. Record attendance and grades. |
| **Teacher**          | Record attendance and grades for assigned classes. View reports.             |
| **Parent**           | View own children's attendance and grades (read-only). Receive SMS alerts.  |
| **System Administrator** | Same as Administrator. Intended for system maintenance and security tasks. |

## SMS Configuration (Africa's Talking)

SMS notifications are sent automatically when a student is marked absent. By default, SMS is simulated (logged to the database only).

To enable real SMS delivery:

1. Create an account at [africastalking.com](https://africastalking.com)
2. Get your **Username** and **API Key** from the dashboard
3. Set environment variables before running the server:

   ```bash
   # Windows (Command Prompt)
   set AFRICASTALKING_USERNAME=sandbox
   set AFRICASTALKING_API_KEY=your_api_key_here

   # Windows (PowerShell)
   $env:AFRICASTALKING_USERNAME="sandbox"
   $env:AFRICASTALKING_API_KEY="your_api_key_here"

   # macOS/Linux
   export AFRICASTALKING_USERNAME=sandbox
   export AFRICASTALKING_API_KEY=your_api_key_here
   ```

Use `sandbox` as the username for testing. Switch to your live username and key for production.

## PostgreSQL Configuration (Optional)

By default, the app uses SQLite. To use PostgreSQL:

```bash
# Set these environment variables
set DATABASE_URL=postgres
set DB_NAME=education_tracker
set DB_USER=postgres
set DB_PASSWORD=your_password
set DB_HOST=localhost
set DB_PORT=5432
```

## Deployment (Render)

This project is ready for deployment on [Render](https://render.com):

1. Push your code to GitHub
2. Create a new **Web Service** on Render
3. Connect your GitHub repository
4. Set the following:
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command:** `gunicorn education_tracker.wsgi:application`
5. Add environment variables in Render dashboard:
   - `DJANGO_SECRET_KEY` — a strong random string
   - `AFRICASTALKING_USERNAME` — your AT username (optional)
   - `AFRICASTALKING_API_KEY` — your AT API key (optional)

## Key Design Decisions

- **Immutable Audit Trail:** Attendance and grade records are never modified or deleted. Corrections create new linked records, preserving the original for auditing purposes.
- **Role-Based Navigation:** The navbar and dashboard adapt based on the logged-in user's role, showing only relevant options.
- **SMS Fallback:** The SMS system gracefully degrades to simulation mode when API credentials are not configured, ensuring the app works without external dependencies.
- **Session Security:** 30-minute inactivity timeout with session reset on activity, as specified in the SRS.

## License

This project was developed as an academic assignment for Introduction to Software Engineering.
