from datetime import date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    session
)

from models import (
    db,
    Faculty,
    Exam,
    Assignment,
    Notification,
    ExchangeRequest
)

from routes.auth import role_required

from controllers import (
    validate_assignment_conflict,
    sync_faculty_duty_counts,
    generate_excel_report,
    generate_pdf_report
)


faculty_bp = Blueprint(
    'faculty',
    __name__,
    url_prefix='/faculty'
)


# Protect all faculty routes
@faculty_bp.before_request
@role_required('faculty')
def before_request():
    pass


# -----------------------------
# Faculty Dashboard
# -----------------------------

@faculty_bp.route('/dashboard')
def dashboard():

    faculty_id = session.get('faculty_id')

    faculty = Faculty.query.get_or_404(faculty_id)

    today = date.today()

    assignments = (
        Assignment.query
        .join(Exam)
        .filter(
            Assignment.faculty_id == faculty_id,
            Assignment.status != 'Cancelled'
        )
        .order_by(
            Exam.date.asc(),
            Exam.start_time.asc()
        )
        .all()
    )


    upcoming_duties = [
        a for a in assignments
        if a.exam.date >= today
    ]

    completed_duties = [
        a for a in assignments
        if a.exam.date < today
    ]


    notifications = (
        Notification.query
        .filter_by(faculty_id=faculty_id)
        .order_by(Notification.created_at.desc())
        .limit(15)
        .all()
    )


    received_requests = (
        ExchangeRequest.query
        .filter_by(
            target_faculty_id=faculty_id,
            status='Pending'
        )
        .all()
    )


    sent_requests = (
        ExchangeRequest.query
        .join(Assignment)
        .filter(
            Assignment.faculty_id == faculty_id
        )
        .order_by(
            ExchangeRequest.created_at.desc()
        )
        .all()
    )


    other_faculties = (
        Faculty.query
        .filter(
            Faculty.id != faculty_id
        )
        .all()
    )


    calendar_events = []

    for assignment in assignments:

        exam = assignment.exam

        calendar_events.append({

            "title":
                f"{exam.subject} ({exam.hall.name})",

            "start":
                f"{exam.date}T{exam.start_time}",

            "end":
                f"{exam.date}T{exam.end_time}",

            "status":
                assignment.status
        })


    return render_template(
        "faculty/dashboard.html",
        faculty=faculty,
        upcoming_duties=upcoming_duties,
        completed_duties=completed_duties,
        notifications=notifications,
        received_requests=received_requests,
        sent_requests=sent_requests,
        other_faculties=other_faculties,
        calendar_events=calendar_events
    )



# -----------------------------
# Mark Notification Read
# -----------------------------

@faculty_bp.route(
    '/notifications/read/<int:id>',
    methods=['POST']
)
def mark_notification_read(id):

    faculty_id = session.get('faculty_id')

    notification = (
        Notification.query
        .filter_by(
            id=id,
            faculty_id=faculty_id
        )
        .first_or_404()
    )

    notification.is_read = True

    db.session.commit()

    return jsonify({
        "success": True
    })



# -----------------------------
# Request Duty Exchange
# -----------------------------

@faculty_bp.route(
    '/exchange/request',
    methods=['POST']
)
def request_exchange():

    faculty_id = session.get('faculty_id')


    assignment_id = request.form.get(
        'assignment_id'
    )

    target_faculty_id = request.form.get(
        'target_faculty_id'
    )

    reason = request.form.get(
        'reason',
        ''
    ).strip()



    if not assignment_id or not target_faculty_id:

        flash(
            "All fields are required.",
            "error"
        )

        return redirect(
            url_for('faculty.dashboard')
        )



    assignment = Assignment.query.get_or_404(
        int(assignment_id)
    )


    if assignment.faculty_id != faculty_id:

        flash(
            "Unauthorized request.",
            "error"
        )

        return redirect(
            url_for('faculty.dashboard')
        )



    existing = (
        ExchangeRequest.query
        .filter_by(
            assignment_id=assignment.id,
            status='Pending'
        )
        .first()
    )


    if existing:

        flash(
            "Exchange already requested.",
            "error"
        )

        return redirect(
            url_for('faculty.dashboard')
        )



    request_obj = ExchangeRequest(

        assignment_id=assignment.id,

        target_faculty_id=int(target_faculty_id),

        request_reason=reason,

        status="Pending"
    )


    db.session.add(request_obj)



    target = Faculty.query.get(
        int(target_faculty_id)
    )


    notification = Notification(

        faculty_id=target.id,

        message=
        f"{assignment.faculty.name} requested duty exchange for "
        f"{assignment.exam.subject} on {assignment.exam.date}"
    )


    db.session.add(notification)

    db.session.commit()



    flash(
        "Exchange request sent.",
        "success"
    )


    return redirect(
        url_for('faculty.dashboard')
    )



# -----------------------------
# Approve / Reject Exchange
# -----------------------------

@faculty_bp.route(
    '/exchange/respond/<int:id>',
    methods=['POST']
)
def respond_exchange(id):

    faculty_id = session.get('faculty_id')


    exchange = ExchangeRequest.query.get_or_404(id)



    if exchange.target_faculty_id != faculty_id:

        flash(
            "Unauthorized.",
            "error"
        )

        return redirect(
            url_for('faculty.dashboard')
        )



    action = request.form.get(
        "action"
    )


    assignment = exchange.assignment

    requester = assignment.faculty

    responder = exchange.target_faculty



    if action == "reject":

        exchange.status = "Rejected"


        db.session.commit()


        flash(
            "Exchange rejected.",
            "success"
        )



    elif action == "approve":


        result = validate_assignment_conflict(
            assignment.id,
            responder.id
        )


        if not result["valid"]:

            flash(
                ", ".join(result["errors"]),
                "error"
            )

            return redirect(
                url_for('faculty.dashboard')
            )



        assignment.faculty_id = responder.id

        assignment.status = "Exchanged"

        exchange.status = "Approved"


        db.session.commit()


        sync_faculty_duty_counts()


        flash(
            "Exchange approved.",
            "success"
        )



    return redirect(
        url_for('faculty.dashboard')
    )



# -----------------------------
# Download Schedule
# -----------------------------

@faculty_bp.route(
    '/schedule/download'
)
def download_schedule():

    faculty_id = session.get('faculty_id')


    faculty = Faculty.query.get_or_404(
        faculty_id
    )


    format_type = request.args.get(
        "format",
        "excel"
    )


    assignments = (
        Assignment.query
        .join(Exam)
        .filter(
            Assignment.faculty_id == faculty_id
        )
        .order_by(
            Exam.date
        )
        .all()
    )



    headers = [
        "Date",
        "Time",
        "Subject",
        "Hall",
        "Status"
    ]



    rows = []

    for a in assignments:

        rows.append([

            str(a.exam.date),

            f"{a.exam.start_time}-{a.exam.end_time}",

            a.exam.subject,

            a.exam.hall.name,

            a.status

        ])



    title = (
        f"Invigilation Schedule - {faculty.name}"
    )



    if format_type == "pdf":

        file = generate_pdf_report(
            rows,
            headers,
            title
        )

        filename = "schedule.pdf"

        mimetype = "application/pdf"



    else:

        file = generate_excel_report(
            rows,
            headers,
            title
        )

        filename = "schedule.xlsx"

        mimetype = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )



    return send_file(

        file,

        as_attachment=True,

        download_name=filename,

        mimetype=mimetype
    )