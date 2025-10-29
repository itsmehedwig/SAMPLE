# Library Management System

## Overview
A professional, fully responsive Django-based library management system designed for educational institutions. The system manages student verification, book cataloging, borrowing/returning transactions, and automated email notifications.

## Current State
The application is fully functional with the following features implemented:
- Student registration with ID verification and email confirmation
- Admin dashboard for managing books, students, and transactions
- POS kiosk interface for borrowing and returning books
- Automated transaction code generation and eInvoice system
- Email notifications for borrowing, returning, and reminders
- Fully responsive design with Tailwind CSS

## Recent Changes
- October 20, 2025: Refactored transaction system to group multiple books into single transactions
  - **Modified Transaction model**: Removed direct book ForeignKey to support multiple books per transaction
  - **Created TransactionItem model**: New model to link multiple books to one transaction
  - **Updated POS borrow flow**: Creates one transaction with multiple books instead of separate transactions per book
  - **Updated admin approval**: Approves/rejects all books in a transaction together
  - **Updated POS return flow**: Returns all books in a transaction as a batch
  - **Updated all views and templates**: Modified student dashboard, admin dashboard, POS success pages, and pending transactions to display grouped books
  - **Changed login page design**: Updated background from gradient to solid white
  - **Configured database**: Switched from MySQL to SQLite for simplified local development
  - **Result**: When a student borrows 7 books, the system now creates 1 transaction instead of 7 separate transactions

- October 19, 2025: Added admin approval for book borrowing and CSV import for books
  - **Implemented book borrowing approval workflow**: POS creates pending borrowing requests that admins must approve
  - **Fixed inventory management**: Book inventory only decreases when admin approves, not when POS creates request
  - **Added CSV import for books**: Admins can now bulk import books from CSV files
  - **Improved mobile responsiveness**: Added hamburger menu for mobile devices, made all pages responsive

- October 19, 2025: Removed email verification, implemented admin approval system
  - **Removed email verification system**: Students no longer need to verify email addresses
  - **Implemented admin approval workflow**: Admins now approve/reject student registrations
  - **Added is_approved field**: Student model now tracks admin approval status
  - **Removed email notifications**: Eliminated all email sending from borrowing/returning transactions
  - **Updated Manage Students page**: Shows pending registrations at the top for quick approval
  - **Created pending students page**: Dedicated page to review all pending registrations
  - **Enhanced admin dashboard**: Shows count of pending registrations requiring attention
  - **Updated POS system**: Checks for approved students instead of email verification

- October 19, 2025: Fixed Python compatibility and email service configuration
  - **Fixed Python 3.13 compatibility issue**: Installed Python 3.11 to resolve Django 5.2.7 incompatibility with Python 3.13's removal of the `cgi` module
  - **Fixed email service**: Corrected EMAIL_HOST_USER and EMAIL_HOST_PASSWORD configuration to properly use environment variables instead of hardcoded values
  - **Fixed student registration flow**: Added database transaction handling to prevent UNIQUE constraint errors when email sending fails
  - **Improved error handling**: Registration now uses atomic transactions and get_or_create() to handle duplicate users gracefully
  - **Added .gitignore**: Created comprehensive .gitignore file for Python/Django projects
  - **Verified server functionality**: Django development server running successfully on port 5000 with no errors

- October 19, 2025: Enhanced CRUD functionality and fixed deployment issues
  - Added complete book management: Add, Edit, and Delete books with confirmation
  - Implemented full student CRUD operations: Add, Edit, and Delete students
  - Updated Manage Books interface with delete functionality
  - Updated Manage Students interface with add, edit, and delete actions
  - Created dedicated templates for all CRUD operations with CSRF protection
  - Enhanced student search functionality in student dashboard (already present)
  - Verified CSRF token implementation across all POST forms
  - Confirmed WSGI configuration is properly set for production deployment
  - Set up Django development server workflow on port 5000

- October 19, 2025: Initial development completed
  - Set up Django project with custom user authentication
  - Created database models for User, Student, Book, Transaction, VerificationCode
  - Implemented CSV import functionality for students
  - Built student registration workflow with email verification
  - Created admin, student, and POS dashboards
  - Implemented borrowing and returning workflows
  - Added email notification system
  - Created management command for automated email reminders

## Project Architecture

### Technology Stack
- **Backend**: Django 5.2.7, Python 3.11
- **Database**: SQLite (development)
- **Frontend**: Tailwind CSS (CDN), Alpine.js, Font Awesome
- **Forms**: Django Crispy Forms with Tailwind styling
- **Image Processing**: Pillow

### Directory Structure
```
library_system/          # Main Django project
library/                 # Main application
  ├── models.py         # Database models
  ├── views.py          # View logic
  ├── forms.py          # Form definitions
  ├── urls.py           # URL routing
  ├── admin.py          # Django admin configuration
  ├── templates/        # HTML templates
  ├── static/           # Static files (CSS, JS, images)
  └── management/       # Custom management commands
      └── commands/
          └── send_reminders.py  # Email reminder command
media/                   # User-uploaded files
  ├── profile_photos/   # Student profile photos
  └── logos/            # System logos
```

### Key Models
1. **User**: Custom user model with types (student, admin, pos)
2. **Student**: Student information with CSV import support and admin approval status
3. **Book**: Book catalog with availability tracking and CSV import support
4. **Transaction**: Borrowing/returning records with transaction codes and admin approval workflow (groups multiple books)
5. **TransactionItem**: Links individual books to a transaction (allows one transaction to contain multiple books)
6. **VerificationCode**: Email verification for student registration (deprecated)

### User Types and Access
1. **Admin** (Username: admin_deejay, Password: Dj*0100010001001010)
   - Import students and books from CSV
   - Manage books (add, edit, delete, import)
   - Manage students (approve/reject, add, edit, delete)
   - Approve/reject book borrowing requests
   - Create POS accounts
   - View all transactions
   - Update admin settings

2. **Student** (Login with Student ID and password)
   - Browse book catalog
   - View borrowed books and due dates
   - View borrowing history
   - Update profile (photo, phone, email, password)

3. **POS Kiosk** (Created by admin)
   - Process book borrowing
   - Process book returns
   - Generate transaction codes and eInvoices
   - Send confirmation emails

## Features

### Student Registration Workflow
1. Student enters Student ID for verification
2. System checks if ID exists in imported student database
3. Student completes registration with:
   - Phone number
   - Email address
   - Profile photo
   - Password
4. Account is created as inactive and pending admin approval
5. Admin reviews and approves/rejects the registration
6. Upon approval, student can login and use the system

### CSV Import Formats

**Students CSV Format:**
```
student_id,last_name,first_name,middle_name,course,year,section
```

**Books CSV Format:**
```
isbn,title,author,category,publisher,year_published,copies_total,description
```
Required fields: isbn, title, author, category
Optional fields: publisher, year_published, copies_total (defaults to 1), description

**Important**: CSV import creates student records in the database but does NOT create user accounts. Students imported via CSV must:
1. Visit the student registration page
2. Enter their Student ID for verification
3. Complete the registration form with:
   - Profile photo
   - Phone number
   - Email address
   - Password
4. Verify their email with the confirmation code

This two-step process ensures:
- All students have verified email addresses
- Students set their own passwords securely
- Profile photos are collected for identification
- Contact information is up-to-date

### Transaction Code Format
Auto-generated format: `{SCHOOL_CODE}{LAST_5_ISBN_DIGITS}{TIMESTAMP}`
Example: `ISU1234520251019174500`

### Admin Approval Systems

**Student Registration Approval:**
- Students register and accounts are created as inactive
- Admins can view pending registrations in:
  - Dedicated "Pending Students" page
  - Top section of "Manage Students" page
- Admins can approve or reject registrations:
  - **Approve**: Activates user account, student can login
  - **Reject**: Deletes user account, student must re-register
- POS system only works with approved students

**Book Borrowing Approval:**
- POS creates book borrowing requests (pending status)
- Book inventory is NOT reduced when request is created
- Admins can view pending borrowing requests in:
  - Dedicated "Pending Book Borrowing" page
  - Admin dashboard shows count of pending requests
- Admins can approve or reject borrowing requests:
  - **Approve**: Book inventory is reduced, student can receive the book
  - **Reject**: Request is cancelled, no inventory change
- Only approved transactions appear in student's borrowed books list

### Management Commands
```bash
# Send automated email reminders
python manage.py send_reminders
```

**Scheduling Email Reminders:**

To automate the email reminder system, you can use one of the following methods:

1. **Linux Cron (Recommended for production)**:
   ```bash
   # Edit crontab
   crontab -e
   
   # Add this line to run daily at 9 AM
   0 9 * * * cd /path/to/project && python manage.py send_reminders
   ```

2. **Manual Execution**:
   Run the command manually or as needed:
   ```bash
   python manage.py send_reminders
   ```

3. **For Production**: Consider using:
   - Django-Q or Celery for task scheduling
   - Heroku Scheduler (if deployed on Heroku)
   - System cron jobs (Linux/Unix systems)

## User Preferences
None specified yet.

## Configuration

### Email Settings (Optional)
Email functionality has been removed from the core workflow:
- Student registration no longer requires email verification
- Book borrowing/returning no longer sends email notifications
- System uses admin approval instead of email verification

The email reminder command is still available but optional:
```bash
python manage.py send_reminders
```

### Running the Application
```bash
python manage.py runserver 0.0.0.0:5000
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating Admin User
```bash
python manage.py createsuperuser
```

## Default Credentials
- **Admin**: admin_deejay / Dj*0100010001001010

## Next Phase Features (Future Enhancements)
- Overdue tracking with fine calculation system
- Book reservation and waitlist functionality
- Overdue email notifications with escalating reminders
- Transaction history export and reporting
- Barcode/QR code scanning for faster ISBN entry
- Production email configuration (SMTP/SendGrid)
- Advanced analytics and reporting dashboard
