from datetime import datetime, time
from models import Faculty, Exam, Assignment, ExaminationHall, Department, db

def parse_time_str(time_str):
    """Utility to parse various time formats like HH:MM, HH:MM:SS, or HH:MM AM/PM."""
    for fmt in ('%H:%M:%S', '%H:%M', '%I:%M %p', '%I:%M%p'):
        try:
            return datetime.strptime(time_str.strip(), fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: {time_str}")

def parse_date_str(date_str):
    """Utility to parse various date formats."""
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")

def check_time_overlap(start1, end1, start2, end2):
    """Returns True if two time intervals overlap."""
    return (start1 < end2) and (start2 < end1)

def validate_timetable_upload(rows):
    """
    Validates a list of dictionaries representing exam timetable rows.
    Each row expects: Subject, Date, Start Time, End Time, Hall Name, Department, Required Invigilators.
    Returns: (valid_exams_data, error_messages)
    """
    valid_exams_data = []
    errors = []
    
    # Pre-fetch halls and departments to optimize queries
    all_halls = {h.name.lower().strip(): h for h in ExaminationHall.query.all()}
    all_depts = {d.name.lower().strip(): d for d in Department.query.all()}
    
    # Keep track of exams within the uploaded file to detect duplicates inside the file itself
    uploaded_exams = [] # list of dicts: {'date', 'start_time', 'end_time', 'hall_name', 'subject'}

    for idx, row in enumerate(rows, start=2): # Start at 2 assuming row 1 is header
        subject = row.get('Subject', '').strip()
        date_raw = row.get('Date', '').strip()
        start_time_raw = row.get('Start Time', '').strip()
        end_time_raw = row.get('End Time', '').strip()
        hall_name = row.get('Hall Name', '').strip()
        dept_name = row.get('Department', '').strip()
        req_inv_raw = row.get('Required Invigilators', '1').strip()
        
        row_errs = []
        
        if not subject:
            row_errs.append("Subject is required.")
        if not date_raw:
            row_errs.append("Date is required.")
        if not start_time_raw:
            row_errs.append("Start Time is required.")
        if not end_time_raw:
            row_errs.append("End Time is required.")
        if not hall_name:
            row_errs.append("Hall Name is required.")
        if not dept_name:
            row_errs.append("Department is required.")
            
        if row_errs:
            errors.append(f"Row {idx}: {', '.join(row_errs)}")
            continue
            
        # Parse formats
        try:
            date_val = parse_date_str(date_raw)
        except ValueError as e:
            row_errs.append(str(e))
        
        try:
            start_val = parse_time_str(start_time_raw)
        except ValueError as e:
            row_errs.append(str(e))
            
        try:
            end_val = parse_time_str(end_time_raw)
        except ValueError as e:
            row_errs.append(str(e))
            
        if 'start_val' in locals() and 'end_val' in locals() and start_val >= end_val:
            row_errs.append("Start Time must be before End Time.")
            
        try:
            req_inv = int(req_inv_raw)
            if req_inv <= 0:
                row_errs.append("Required Invigilators must be greater than 0.")
        except ValueError:
            row_errs.append("Required Invigilators must be an integer.")
            
        # Check database relations
        hall = all_halls.get(hall_name.lower())
        if not hall:
            row_errs.append(f"Examination Hall '{hall_name}' does not exist in the database.")
            
        dept = all_depts.get(dept_name.lower())
        if not dept:
            row_errs.append(f"Department '{dept_name}' does not exist in the database.")
            
        if row_errs:
            errors.append(f"Row {idx}: {', '.join(row_errs)}")
            continue
            
        # Check overlaps inside the uploaded file itself
        file_overlap = False
        for ue in uploaded_exams:
            if ue['date'] == date_val and ue['hall_name'].lower() == hall_name.lower():
                if check_time_overlap(start_val, end_val, ue['start_time'], ue['end_time']):
                    row_errs.append(f"Overlaps with another exam in the same hall in this upload: '{ue['subject']}' ({ue['start_time']}-{ue['end_time']})")
                    file_overlap = True
                    break
        
        # Check overlaps in the database
        if not file_overlap:
            db_overlaps = Exam.query.filter_by(date=date_val, hall_id=hall.id).all()
            for db_ex in db_overlaps:
                if check_time_overlap(start_val, end_val, db_ex.start_time, db_ex.end_time):
                    row_errs.append(f"Overlaps with an existing exam in the database: '{db_ex.subject}' ({db_ex.start_time.strftime('%H:%M')}-{db_ex.end_time.strftime('%H:%M')})")
                    break
                    
        if row_errs:
            errors.append(f"Row {idx}: {', '.join(row_errs)}")
            continue
            
        # Valid row, register it
        uploaded_exams.append({
            'date': date_val,
            'start_time': start_val,
            'end_time': end_val,
            'hall_name': hall_name,
            'subject': subject
        })
        
        valid_exams_data.append({
            'subject': subject,
            'date': date_val,
            'start_time': start_val,
            'end_time': end_val,
            'hall_id': hall.id,
            'department_id': dept.id,
            'required_invigilators': req_inv
        })
        
    return valid_exams_data, errors

def validate_assignment_conflict(assignment_id, new_faculty_id, new_exam_id=None):
    """
    Validates if a manual reassignment conflicts with rules.
    If new_faculty_id is None, it's an unassignment request, which is always valid.
    """
    if new_faculty_id is None:
        return {'valid': True, 'warnings': [], 'errors': []}

    warnings = []
    errors = []
    
    faculty = Faculty.query.get(new_faculty_id)
    if not faculty:
        return {'valid': False, 'errors': ['Faculty member not found.']}
        
    # Get the target exam
    if new_exam_id:
        exam = Exam.query.get(new_exam_id)
    else:
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return {'valid': False, 'errors': ['Assignment not found.']}
        exam = Exam.query.get(assignment.exam_id)
        
    if not exam:
        return {'valid': False, 'errors': ['Exam not found.']}
        
    # Rule 2: Check Availability
    if not faculty.is_available_on(exam.date):
        errors.append(f"{faculty.name} is marked as unavailable on {exam.date.strftime('%Y-%m-%d')}.")
        
    # Rule 5: Check Max Duties
    # Get total assigned duties, ignoring the current assignment if we are modifying it for this faculty member
    current_fac_assignment = Assignment.query.filter_by(id=assignment_id).first() if assignment_id else None
    current_duties = faculty.total_assigned_duties
    
    # If the faculty was already assigned to this exact assignment, we don't count it as a new duty
    if current_fac_assignment and current_fac_assignment.faculty_id == faculty.id:
        # Same faculty, no change in duties count
        pass
    else:
        if current_duties >= faculty.max_duties:
            errors.append(f"{faculty.name} has reached the maximum allowed duties ({faculty.max_duties}).")
            
    # Rule 1: Check Overlapping Duties
    # Get all active assignments of this faculty on the same date (excluding the current assignment we are replacing)
    query = Assignment.query.join(Exam).filter(
        Exam.date == exam.date,
        Assignment.faculty_id == faculty.id
    )
    if assignment_id:
        query = query.filter(Assignment.id != assignment_id)
        
    other_assignments = query.all()
    for o_asg in other_assignments:
        if check_time_overlap(exam.start_time, exam.end_time, o_asg.exam.start_time, o_asg.exam.end_time):
            errors.append(
                f"{faculty.name} is already assigned to overlapping exam '{o_asg.exam.subject}' "
                f"({o_asg.exam.start_time.strftime('%H:%M')}-{o_asg.exam.end_time.strftime('%H:%M')}) in {o_asg.exam.hall.name}."
            )
            
    # Rule 4: Check Department preferences
    if faculty.department_id != exam.department_id:
        warnings.append(
            f"Department mismatch: {faculty.name} is from '{faculty.department.name}' "
            f"but this exam belongs to '{exam.department.name}'."
        )
        
    return {
        'valid': len(errors) == 0,
        'warnings': warnings,
        'errors': errors
    }
