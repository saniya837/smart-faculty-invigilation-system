# Smart Faculty Invigilation Allotment System

Automates and optimizes the examination invigilation allotment process. The system ensures fair, conflict-free allocation of duties to faculty members, provides real-time tracking, in-app notification flags, dynamic duty exchange trades, and report exports.

## Core Features
1. **Automated Allocation**: Rule-based constraint satisfaction engine that balances faculty workloads while checking date availability and time block overlaps.
2. **Conflict Prevention**: Pre-allocator verification checks for same-day schedule collisions, department preferences, and maximum allowed duty thresholds.
3. **Admin Dashboard**: Visual counters for faculty profiles and exams, combined with Chart.js charts showing workload distributions and faculty utilization bins.
4. **Faculty Dashboard**: Personalized upcoming duties lists, read/unread notifications center, and an interactive grid-view calendar.
5. **Duty Exchange System**: Lets faculty request swap handovers with colleagues. The system automatically validates constraints before approving the trade.
6. **Timetable Uploader**: Drag-and-drop file uploader for CSV and Excel files, featuring line-by-line validation to block duplicate exams or invalid halls.
7. **Report Center**: Custom query filters to generate and stream stylized Excel sheets or print-ready landscape PDF files.

---

## Folder Structure
```
SmartFacultyInvigilation/
│── app.py                   # Flask entry point and db auto-seeding
│── config.py                # System settings and db URI toggle
│── requirements.txt         # Package dependencies
│── database.sql             # MySQL schema script for manual configuration
│── sample_timetable.csv     # Sample upload file
│
├── models/                  # Database Models (SQLAlchemy ORM)
│    ├── __init__.py
│    ├── db.py
│    ├── user.py
│    ├── faculty.py
│    ├── department.py
│    ├── hall.py
│    ├── exam.py
│    ├── assignment.py
│    ├── notification.py
│    └── exchange_request.py
│
├── controllers/             # Business Logic & Algorithms
│    ├── __init__.py
│    ├── validators.py       # Live conflict checks & parser validators
│    ├── allocation.py       # Automated allocation solver engine
│    └── report_generator.py # Excel (openpyxl) & PDF (reportlab) builders
│
├── routes/                  # HTTP Route Controllers
│    ├── __init__.py
│    ├── auth.py             # Auth sessions and role guards
│    ├── admin.py            # Administrative controls
│    └── faculty.py          # Faculty dash controls
│
├── static/                  # Static Assets
│    ├── css/
│    │    └── style.css      # Custom dark/light design system stylesheet
│    └── js/
│         └── main.js        # Interactive handlers, AJAX, & calendar grid
│
├── templates/               # Jinja2 HTML Layouts
│    ├── base.html
│    ├── login.html
│    ├── admin/
│    │    ├── dashboard.html
│    │    ├── faculty.html
│    │    ├── departments.html
│    │    ├── halls.html
│    │    ├── upload.html
│    │    ├── allocation.html
│    │    ├── assignments.html
│    │    └── reports.html
│    └── faculty/
│         └── dashboard.html
│
├── uploads/                 # Location for temporary file parses
└── reports/                 # Local directory for generated documents
```

---

## Setup Instructions

### 1. Install Dependencies
Run the following pip command:
```bash
pip install -r requirements.txt
```

### 2. Configure Database
By default, the application runs on **SQLite** to execute immediately without any database setup (it creates `invigilation.db` in the project root folder and seeds it automatically).

To switch to **MySQL**:
1. Open `config.py`.
2. Set `DB_TYPE = 'mysql'`.
3. Update `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, and `MYSQL_DB` with your local MySQL parameters.
4. Run your MySQL server. The Flask app will automatically create the tables and seed mock data on launch. (Optionally, use `database.sql` to inspect or manually load tables).

### 3. Run the Server
Start the Flask development server:
```bash
python app.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

---

## Default Seed Accounts
The system is pre-seeded with the following credentials:

### Administrator
* **Username**: `admin`
* **Password**: `admin123`

### Faculty (10 Mock Accounts)
* **Passwords**: All faculty accounts use password `password123`
* **Usernames**:
  * `turing` (Dr. Alan Turing - Computer Science)
  * `hopper` (Dr. Grace Hopper - Computer Science)
  * `shannon` (Prof. Claude Shannon - Electronics)
  * `lovelace` (Dr. Ada Lovelace - Computer Science)
  * `feynman` (Prof. Richard Feynman - Electronics)
  * `tesla` (Dr. Nikola Tesla - Mechanical)
  * `curie` (Prof. Marie Curie - Electronics)
  * `einstein` (Dr. Albert Einstein - Mechanical)
  * `braun` (Prof. Wernher von Braun - Civil)
  * `darwin` (Dr. Charles Darwin - Civil)

---

## Allocation Algorithm Rules
The core engine satisfies the following constraints:
* **Rule 1 (No Overlaps)**: Faculty members cannot be assigned to overlapping examinations on the same date.
* **Rule 2 (Availability check)**: Faculty are skipped if the exam date falls inside their `unavailable_dates` list.
* **Rule 3 (Workload Balance)**: Workloads are kept balanced. The scheduler sorts candidates based on their current assignments to minimize disparity.
* **Rule 4 (Department Preferences)**: If prioritized, the scheduler attempts to match the faculty member's department to the subject's department.
* **Rule 5 (Max Duties limit)**: Faculty cannot exceed their `max_duties` threshold.
* **Rule 6 (Required Invigilators met)**: Every exam venue receives the exact count of invigilators requested.
* **Rule 7 (Alert shortages)**: If no faculty members are eligible, a placeholder assignment is generated and flagged as `'Alert-Unassigned'` to warn the admin.
