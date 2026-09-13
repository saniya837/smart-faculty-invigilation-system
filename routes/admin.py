import io
import csv
from datetime import datetime, date, time
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.security import generate_password_hash

from models import db, Department, Faculty, ExaminationHall, Exam, Assignment, User, Notification
from routes.auth import role_required
from controllers import (
    validate_timetable_upload,
    validate_assignment_conflict,
    auto_allocate_duties,
    generate_excel_report,
    generate_pdf_report,
    sync_faculty_duty_counts
)
from openpyxl import load_workbook

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Apply role check to all endpoints in this blueprint
@admin_bp.before_request
@role_required('admin')
def before_request():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    total_faculty = Faculty.query.count()
    total_exams = Exam.query.count()
    
    today = date.today()
    todays_exams_count = Exam.query.filter_by(date=today).count()
    
    # Assignments stats
    total_assignments = Assignment.query.count()
    pending_assignments = Assignment.query.filter_by(faculty_id=None).count() # Shortages / Alerts
    completed_assignments = Assignment.query.join(Exam).filter(Exam.date < today, Assignment.faculty_id != None).count()
    
    # Chart Data 1: Faculty Workload Distribution (Duties assigned per faculty)
    faculties = Faculty.query.all()
    faculty_names = [f.name for f in faculties]
    faculty_duties = [f.total_assigned_duties for f in faculties]
    
    # Chart Data 2: Faculty Utilization Distribution (Binned duties)
    utilization_bins = {
        '0 Duties': 0,
        '1-2 Duties': 0,
        '3-4 Duties': 0,
        '5+ Duties': 0
    }
    for f in faculties:
        d = f.total_assigned_duties
        if d == 0:
            utilization_bins['0 Duties'] += 1
        elif 1 <= d <= 2:
            utilization_bins['1-2 Duties'] += 1
        elif 3 <= d <= 4:
            utilization_bins['3-4 Duties'] += 1
        else:
            utilization_bins['5+ Duties'] += 1
            
    utilization_labels = list(utilization_bins.keys())
    utilization_values = list(utilization_bins.values())

    return render_template(
        'admin/dashboard.html',
        total_faculty=total_faculty,
        total_exams=total_exams,
        todays_exams_count=todays_exams_count,
        pending_assignments=pending_assignments,
        completed_assignments=completed_assignments,
        faculty_names=faculty_names,
        faculty_duties=faculty_duties,
        utilization_labels=utilization_labels,
        utilization_values=utilization_values
    )

# -----------------------------------------------------------------------------
# DEPARTMENTS CRUD
# -----------------------------------------------------------------------------
@admin_bp.route('/departments', methods=['GET', 'POST'])
def departments():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash("Department name cannot be empty.", "error")
        else:
            existing = Department.query.filter_by(name=name).first()
            if existing:
                flash(f"Department '{name}' already exists.", "error")
            else:
                dept = Department(name=name)
                db.session.add(dept)
                db.session.commit()
                flash("Department added successfully.", "success")
                return redirect(url_for('admin.departments'))
                
    depts = Department.query.all()
    return render_template('admin/departments.html', departments=depts)

@admin_bp.route('/departments/delete/<int:id>', methods=['POST'])
def delete_department(id):
    dept = Department.query.get_or_404(id)
    db.session.delete(dept)
    db.session.commit()
    flash(f"Department '{dept.name}' deleted successfully.", "success")
    return redirect(url_for('admin.departments'))


# -----------------------------------------------------------------------------
# EXAMINATION HALLS CRUD
# -----------------------------------------------------------------------------
@admin_bp.route('/halls', methods=['GET', 'POST'])
def halls():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        capacity_raw = request.form.get('capacity', '').strip()
        
        errs = []
        if not name:
            errs.append("Hall name cannot be empty.")
        if not capacity_raw:
            errs.append("Capacity is required.")
        else:
            try:
                capacity = int(capacity_raw)
                if capacity <= 0:
                    errs.append("Capacity must be positive.")
            except ValueError:
                errs.append("Capacity must be an integer.")
                
        if errs:
            for e in errs:
                flash(e, "error")
        else:
            existing = ExaminationHall.query.filter_by(name=name).first()
            if existing:
                flash(f"Hall '{name}' already exists.", "error")
            else:
                hall = ExaminationHall(name=name, capacity=capacity)
                db.session.add(hall)
                db.session.commit()
                flash("Examination Hall added successfully.", "success")
                return redirect(url_for('admin.halls'))
                
    halls_list = ExaminationHall.query.all()
    return render_template('admin/halls.html', halls=halls_list)

@admin_bp.route('/halls/delete/<int:id>', methods=['POST'])
def delete_hall(id):
    hall = ExaminationHall.query.get_or_404(id)
    db.session.delete(hall)
    db.session.commit()
    flash(f"Hall '{hall.name}' deleted successfully.", "success")
    return redirect(url_for('admin.halls'))


# -----------------------------------------------------------------------------
# FACULTY CRUD
# -----------------------------------------------------------------------------
@admin_bp.route('/faculty', methods=['GET', 'POST'])
def faculty():
    depts = Department.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        dept_id = request.form.get('department_id')
        designation = request.form.get('designation', '').strip()
        max_duties_raw = request.form.get('max_duties', '5')
        unavailable_dates = request.form.get('unavailable_dates', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validation
        errs = []
        if not name or not email or not phone or not dept_id or not designation:
            errs.append("All profile fields are required.")
        if not username or not password:
            errs.append("Username and password are required to create a login account.")
            
        try:
            max_duties = int(max_duties_raw)
            if max_duties < 0:
                errs.append("Max duties cannot be negative.")
        except ValueError:
            errs.append("Max duties must be an integer.")
            
        # Unique checks
        if Faculty.query.filter_by(email=email).first():
            errs.append(f"Faculty with email '{email}' already exists.")
        if User.query.filter_by(username=username).first():
            errs.append(f"Username '{username}' is already taken.")
            
        if errs:
            for e in errs:
                flash(e, "error")
        else:
            # Create Faculty
            fac = Faculty(
                name=name,
                email=email,
                phone=phone,
                department_id=int(dept_id),
                designation=designation,
                max_duties=max_duties,
                unavailable_dates=unavailable_dates,
                total_assigned_duties=0
            )
            db.session.add(fac)
            db.session.flush() # Populate fac.id
            
            # Create User Account
            user = User(
                username=username,
                role='faculty',
                faculty_id=fac.id
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash("Faculty member and login user created successfully.", "success")
            return redirect(url_for('admin.faculty'))
            
    # GET list
    search_q = request.args.get('search', '').strip()
    dept_filter = request.args.get('department_id', '')
    
    query = Faculty.query
    if search_q:
        query = query.filter(Faculty.name.like(f"%{search_q}%") | Faculty.email.like(f"%{search_q}%"))
    if dept_filter:
        query = query.filter_by(department_id=int(dept_filter))
        
    faculty_list = query.all()
    return render_template('admin/faculty.html', faculty_list=faculty_list, departments=depts)

@admin_bp.route('/faculty/edit/<int:id>', methods=['POST'])
def edit_faculty(id):
    fac = Faculty.query.get_or_404(id)
    
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    dept_id = request.form.get('department_id')
    designation = request.form.get('designation', '').strip()
    max_duties_raw = request.form.get('max_duties')
    unavailable_dates = request.form.get('unavailable_dates', '').strip()
    
    errs = []
    if not name or not email or not phone or not dept_id or not designation:
        errs.append("All fields are required.")
        
    try:
        max_duties = int(max_duties_raw)
        if max_duties < 0:
            errs.append("Max duties cannot be negative.")
    except ValueError:
        errs.append("Max duties must be an integer.")
        
    # Check email duplicate
    dup_email = Faculty.query.filter(Faculty.email == email, Faculty.id != id).first()
    if dup_email:
        errs.append(f"Email '{email}' is already in use by another faculty.")
        
    if errs:
        for e in errs:
            flash(e, "error")
    else:
        fac.name = name
        fac.email = email
        fac.phone = phone
        fac.department_id = int(dept_id)
        fac.designation = designation
        fac.max_duties = max_duties
        fac.unavailable_dates = unavailable_dates
        db.session.commit()
        flash("Faculty profile updated successfully.", "success")
        
    return redirect(url_for('admin.faculty'))

@admin_bp.route('/faculty/delete/<int:id>', methods=['POST'])
def delete_faculty(id):
    fac = Faculty.query.get_or_404(id)
    # This cascade deletes User too
    db.session.delete(fac)
    db.session.commit()
    sync_faculty_duty_counts() # Recount remaining in case
    flash("Faculty member deleted successfully.", "success")
    return redirect(url_for('admin.faculty'))


# -----------------------------------------------------------------------------
# TIMETABLE UPLOAD
# -----------------------------------------------------------------------------
@admin_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('timetable_file')
        if not file or file.filename == '':
            flash("No file selected.", "error")
            return render_template('admin/upload.html')
            
        filename = file.filename.lower()
        rows = []
        try:
            if filename.endswith('.csv'):
                # Read CSV
                stream = io.StringIO(file.stream.read().decode("utf-8"), newline="")
                reader = csv.DictReader(stream)
                # Strip spaces from keys
                reader.fieldnames = [f.strip() for f in reader.fieldnames] if reader.fieldnames else []
                for r in reader:
                    # Strip spaces from values
                    stripped_row = {k: v.strip() for k, v in r.items() if k is not None}
                    rows.append(stripped_row)
                    
            elif filename.endswith('.xlsx'):
                # Read Excel
                wb = load_workbook(file)
                ws = wb.active
                excel_rows = list(ws.rows)
                if not excel_rows:
                    flash("Excel sheet is empty.", "error")
                    return render_template('admin/upload.html')
                    
                headers = [str(cell.value).strip() if cell.value is not None else "" for cell in excel_rows[0]]
                for r in excel_rows[1:]:
                    row_dict = {}
                    for idx, cell in enumerate(r):
                        if idx < len(headers) and headers[idx]:
                            val = cell.value
                            if val is not None:
                                if isinstance(val, datetime):
                                    val = val.strftime('%Y-%m-%d')
                                elif isinstance(val, time):
                                    val = val.strftime('%H:%M')
                                row_dict[headers[idx]] = str(val).strip()
                            else:
                                row_dict[headers[idx]] = ""
                    if any(row_dict.values()): # Only append non-empty rows
                        rows.append(row_dict)
            else:
                flash("Unsupported file format. Please upload CSV or XLSX.", "error")
                return render_template('admin/upload.html')
                
        except Exception as e:
            flash(f"Error reading file: {str(e)}", "error")
            return render_template('admin/upload.html')
            
        if not rows:
            flash("No data rows found in the uploaded file.", "error")
            return render_template('admin/upload.html')
            
        # Validate data
        valid_exams, parse_errors = validate_timetable_upload(rows)
        
        if parse_errors:
            # We fail the entire batch to preserve database integrity
            return render_template('admin/upload.html', errors=parse_errors)
            
        # Save validated exams to the database
        try:
            inserted_count = 0
            for ex_data in valid_exams:
                exam = Exam(
                    subject=ex_data['subject'],
                    date=ex_data['date'],
                    start_time=ex_data['start_time'],
                    end_time=ex_data['end_time'],
                    hall_id=ex_data['hall_id'],
                    department_id=ex_data['department_id'],
                    required_invigilators=ex_data['required_invigilators']
                )
                db.session.add(exam)
                inserted_count += 1
            db.session.commit()
            
            flash(f"Timetable uploaded successfully! {inserted_count} exams imported.", "success")
            return redirect(url_for('admin.upload'))
        except Exception as e:
            db.session.rollback()
            flash(f"Database error while saving exams: {str(e)}", "error")
            
    return render_template('admin/upload.html')


# -----------------------------------------------------------------------------
# AUTOMATIC ALLOCATION
# -----------------------------------------------------------------------------
@admin_bp.route('/allocation', methods=['GET', 'POST'])
def allocation():
    summary = None
    if request.method == 'POST':
        clear_existing = request.form.get('clear_existing') == 'true'
        try:
            summary = auto_allocate_duties(clear_existing=clear_existing)
            flash("Automatic Allocation generation completed successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error during allocation: {str(e)}", "error")
            
    return render_template('admin/allocation.html', summary=summary)


# -----------------------------------------------------------------------------
# ASSIGNMENTS LIST & MANUAL EDITING
# -----------------------------------------------------------------------------
@admin_bp.route('/assignments', methods=['GET'])
def assignments():
    faculties = Faculty.query.all()
    halls_list = ExaminationHall.query.all()
    
    # Filters
    search_fac = request.args.get('faculty_name', '').strip()
    search_dept = request.args.get('department_name', '').strip()
    search_subj = request.args.get('subject', '').strip()
    search_hall = request.args.get('hall_name', '').strip()
    search_date = request.args.get('date', '').strip()
    
    query = Assignment.query.join(Exam)
    
    if search_fac:
        query = query.join(Faculty).filter(Faculty.name.like(f"%{search_fac}%"))
    if search_dept:
        # Check either exam's subject department or faculty's department
        query = query.join(Department, Exam.department_id == Department.id).filter(Department.name.like(f"%{search_dept}%"))
    if search_subj:
        query = query.filter(Exam.subject.like(f"%{search_subj}%"))
    if search_hall:
        query = query.join(ExaminationHall).filter(ExaminationHall.name.like(f"%{search_hall}%"))
    if search_date:
        try:
            d_val = datetime.strptime(search_date, '%Y-%m-%d').date()
            query = query.filter(Exam.date == d_val)
        except ValueError:
            pass
            
    assignments_list = query.all()
    
    return render_template(
        'admin/assignments.html',
        assignments=assignments_list,
        faculties=faculties,
        halls=halls_list
    )

@admin_bp.route('/assignments/validate-edit', methods=['POST'])
def api_validate_edit():
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    new_faculty_id = data.get('faculty_id')
    
    if new_faculty_id == 'unassigned' or new_faculty_id == '' or new_faculty_id is None:
        new_fac_id = None
    else:
        new_fac_id = int(new_faculty_id)
        
    validation_res = validate_assignment_conflict(assignment_id, new_fac_id)
    return jsonify(validation_res)

@admin_bp.route('/assignments/edit/<int:id>', methods=['POST'])
def edit_assignment(id):
    asg = Assignment.query.get_or_404(id)
    old_faculty_id = asg.faculty_id
    
    faculty_id_raw = request.form.get('faculty_id', '').strip()
    if faculty_id_raw == 'unassigned' or faculty_id_raw == '':
        new_faculty_id = None
    else:
        new_faculty_id = int(faculty_id_raw)
        
    # Re-validate on submission to block hard errors
    val_res = validate_assignment_conflict(id, new_faculty_id)
    if not val_res['valid']:
        for err in val_res['errors']:
            flash(f"Constraint Blocked: {err}", "error")
        return redirect(url_for('admin.assignments'))
        
    # Update Assignment
    asg.faculty_id = new_faculty_id
    if new_faculty_id is None:
        asg.status = 'Alert-Unassigned'
    else:
        asg.status = 'Assigned'
        
    # Commit changes
    db.session.commit()
    
    # Sync count
    sync_faculty_duty_counts()
    
    # Handle notifications
    exam = asg.exam
    if old_faculty_id and old_faculty_id != new_faculty_id:
        # Notify old faculty
        notif_msg = (
            f"Your invigilation duty for '{exam.subject}' on "
            f"{exam.date.strftime('%Y-%m-%d')} has been cancelled."
        )
        notif = Notification(faculty_id=old_faculty_id, message=notif_msg)
        db.session.add(notif)
        
    if new_faculty_id and old_faculty_id != new_faculty_id:
        # Notify new faculty
        notif_msg = (
            f"You have been assigned to invigilate the exam '{exam.subject}' "
            f"on {exam.date.strftime('%Y-%m-%d')} from {exam.start_time.strftime('%H:%M')} to "
            f"{exam.end_time.strftime('%H:%M')} in {exam.hall.name}."
        )
        notif = Notification(faculty_id=new_faculty_id, message=notif_msg)
        db.session.add(notif)
        
    db.session.commit()
    
    flash("Assignment updated and duty counts synchronized.", "success")
    return redirect(url_for('admin.assignments'))


# -----------------------------------------------------------------------------
# REPORTS DOWNLOAD PANEL
# -----------------------------------------------------------------------------
@admin_bp.route('/reports')
def reports():
    faculties = Faculty.query.all()
    departments = Department.query.all()
    halls_list = ExaminationHall.query.all()
    return render_template(
        'admin/reports.html',
        faculties=faculties,
        departments=departments,
        halls=halls_list
    )

@admin_bp.route('/reports/download')
def download_report():
    report_type = request.args.get('type', 'general') # faculty, department, hall, date, general
    format_type = request.args.get('format', 'excel') # excel or pdf
    
    # Load dataset based on type
    query = Assignment.query.join(Exam)
    
    title_suffix = "All Invigilation Duties"
    
    if report_type == 'faculty':
        fac_id = request.args.get('faculty_id')
        if fac_id:
            query = query.filter(Assignment.faculty_id == int(fac_id))
            fac = Faculty.query.get(fac_id)
            title_suffix = f"Duties for {fac.name if fac else 'Faculty'}"
    elif report_type == 'department':
        dept_id = request.args.get('department_id')
        if dept_id:
            query = query.join(Faculty).filter(Faculty.department_id == int(dept_id))
            dept = Department.query.get(dept_id)
            title_suffix = f"Duties in {dept.name if dept else 'Department'}"
    elif report_type == 'hall':
        hall_id = request.args.get('hall_id')
        if hall_id:
            query = query.filter(Exam.hall_id == int(hall_id))
            hall = ExaminationHall.query.get(hall_id)
            title_suffix = f"Duties in {hall.name if hall else 'Hall'}"
    elif report_type == 'date':
        date_str = request.args.get('date')
        if date_str:
            try:
                d_val = datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter(Exam.date == d_val)
                title_suffix = f"Duties on {date_str}"
            except ValueError:
                pass
                
    assignments_list = query.all()
    
    # Prepare rows and headers
    headers = ["Exam Date", "Time Slot", "Subject", "Hall Location", "Invigilator Name", "Faculty Department", "Status"]
    
    data_rows = []
    for asg in assignments_list:
        exam = asg.exam
        fac = asg.faculty
        date_str = exam.date.strftime('%Y-%m-%d')
        time_str = f"{exam.start_time.strftime('%H:%M')} - {exam.end_time.strftime('%H:%M')}"
        fac_name = fac.name if fac else "Unassigned (Alert)"
        fac_dept = fac.department.name if fac and fac.department else "N/A"
        
        data_rows.append([
            date_str,
            time_str,
            exam.subject,
            exam.hall.name,
            fac_name,
            fac_dept,
            asg.status
        ])
        
    title = f"Invigilation Report - {title_suffix}"
    
    if format_type == 'pdf':
        buffer = generate_pdf_report(data_rows, headers, title)
        filename = f"invigilation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        mimetype = "application/pdf"
    else:
        buffer = generate_excel_report(data_rows, headers, title)
        filename = f"invigilation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )
