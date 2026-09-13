from models import db, Faculty, Exam, Assignment, Department, Notification, User
from controllers.validators import check_time_overlap
from config import Config


def sync_faculty_duty_counts():
    """Recalculates and updates duty counts for actual faculty users only."""

    faculties = Faculty.query.join(User).filter(
        User.role == 'faculty'
    ).all()

    for faculty in faculties:
        count = Assignment.query.filter(
            Assignment.faculty_id == faculty.id,
            Assignment.status != 'Cancelled'
        ).count()

        faculty.total_assigned_duties = count

    db.session.commit()


def auto_allocate_duties(clear_existing=True):
    """
    Runs the automated invigilation allotment algorithm.

    Rules:
    1. Prevent overlapping duties
    2. Check faculty unavailable dates
    3. Balance workload
    4. Prefer same department when configured
    5. Respect maximum duties
    6. Fill all available slots
    7. Generate alert if no faculty is available
    """

    summary = {
        'total_slots': 0,
        'assigned_count': 0,
        'alert_count': 0,
        'cleared': clear_existing,
        'logs': []
    }

    # ---------------------------------------------------------
    # STEP 1: Clear old assignments if Fresh Generation selected
    # ---------------------------------------------------------

    if clear_existing:

        Assignment.query.delete()

        # Reset workload counters
        Faculty.query.update({
            Faculty.total_assigned_duties: 0
        })

        db.session.commit()

        summary['logs'].append(
            "Cleared all existing assignments and reset workload counters."
        )

    else:

        sync_faculty_duty_counts()

        summary['logs'].append(
            "Synchronized existing workload counters with current database assignments."
        )

    # ---------------------------------------------------------
    # STEP 2: Get all exams
    # ---------------------------------------------------------

    exams = Exam.query.order_by(
        Exam.date.asc(),
        Exam.start_time.asc()
    ).all()

    # ---------------------------------------------------------
    # STEP 3: IMPORTANT
    # Get ONLY actual faculty users.
    #
    # Administrator is also stored in the Faculty table,
    # so Faculty.query.all() would incorrectly include Administrator.
    # ---------------------------------------------------------

    faculties = Faculty.query.join(User).filter(
        User.role == 'faculty'
    ).all()

    # Configuration
    prioritize_balance = Config.RULE_PRIORITIZE_BALANCE

    # ---------------------------------------------------------
    # STEP 4: Process every exam
    # ---------------------------------------------------------

    for exam in exams:

        # Get assignments already made for this exam
        existing_assignments = Assignment.query.filter_by(
            exam_id=exam.id
        ).all()

        assigned_slots = len([
            a for a in existing_assignments
            if a.faculty_id is not None
            and a.status != 'Cancelled'
        ])

        slots_needed = exam.required_invigilators - assigned_slots

        summary['total_slots'] += exam.required_invigilators

        summary['assigned_count'] += assigned_slots

        # If enough faculty are already assigned
        if slots_needed <= 0:
            continue

        # -----------------------------------------------------
        # STEP 5: Fill required invigilator slots
        # -----------------------------------------------------

        for slot in range(slots_needed):

            eligible_candidates = []

            # -------------------------------------------------
            # Check every faculty member
            # -------------------------------------------------

            for faculty in faculties:

                # ---------------------------------------------
                # Rule 5: Maximum duties
                # ---------------------------------------------

                if faculty.total_assigned_duties >= faculty.max_duties:
                    continue

                # ---------------------------------------------
                # Rule 2: Unavailable date
                # ---------------------------------------------

                if not faculty.is_available_on(exam.date):
                    continue

                # ---------------------------------------------
                # Rule 1: Time overlap
                # ---------------------------------------------

                faculty_assignments = Assignment.query.join(
                    Exam
                ).filter(
                    Assignment.faculty_id == faculty.id,
                    Assignment.status != 'Cancelled',
                    Exam.date == exam.date
                ).all()

                clash = False

                for fa in faculty_assignments:

                    if check_time_overlap(
                        exam.start_time,
                        exam.end_time,
                        fa.exam.start_time,
                        fa.exam.end_time
                    ):
                        clash = True
                        break

                if clash:
                    continue

                # ---------------------------------------------
                # Faculty passed all checks
                # ---------------------------------------------

                eligible_candidates.append(faculty)

            # -------------------------------------------------
            # STEP 6: No faculty available
            # -------------------------------------------------

            if not eligible_candidates:

                alert_assignment = Assignment(
                    faculty_id=None,
                    exam_id=exam.id,
                    status='Alert-Unassigned'
                )

                db.session.add(alert_assignment)

                db.session.commit()

                summary['alert_count'] += 1

                summary['logs'].append(
                    f"ALERT: No eligible faculty available for "
                    f"'{exam.subject}' on "
                    f"{exam.date.strftime('%Y-%m-%d')} "
                    f"({exam.start_time.strftime('%H:%M')}-"
                    f"{exam.end_time.strftime('%H:%M')}) "
                    f"in {exam.hall.name}."
                )

                continue

            # -------------------------------------------------
            # STEP 7: Select best faculty
            # -------------------------------------------------

            if prioritize_balance:

                # First balance workload
                # Then prefer same department
                # Then lower faculty ID

                eligible_candidates.sort(
                    key=lambda f: (
                        f.total_assigned_duties,
                        0 if f.department_id == exam.department_id else 1,
                        f.id
                    )
                )

            else:

                # First prefer same department
                # Then balance workload
                # Then lower faculty ID

                eligible_candidates.sort(
                    key=lambda f: (
                        0 if f.department_id == exam.department_id else 1,
                        f.total_assigned_duties,
                        f.id
                    )
                )

            # -------------------------------------------------
            # STEP 8: Assign selected faculty
            # -------------------------------------------------

            selected = eligible_candidates[0]

            assignment = Assignment(
                faculty_id=selected.id,
                exam_id=exam.id,
                status='Assigned'
            )

            db.session.add(assignment)

            # Increase workload
            selected.total_assigned_duties += 1

            db.session.commit()

            # -------------------------------------------------
            # STEP 9: Send notification
            # -------------------------------------------------

            notif_msg = (
                f"You have been assigned to invigilate the exam "
                f"'{exam.subject}' on "
                f"{exam.date.strftime('%Y-%m-%d')} from "
                f"{exam.start_time.strftime('%H:%M')} to "
                f"{exam.end_time.strftime('%H:%M')} in "
                f"{exam.hall.name}."
            )

            notif = Notification(
                faculty_id=selected.id,
                message=notif_msg,
                is_read=False
            )

            db.session.add(notif)

            db.session.commit()

            # Update summary
            summary['assigned_count'] += 1

            summary['logs'].append(
                f"Assigned {selected.name} to "
                f"'{exam.subject}' on "
                f"{exam.date.strftime('%Y-%m-%d')}."
            )

    # ---------------------------------------------------------
    # STEP 10: Final message
    # ---------------------------------------------------------

    summary['logs'].append(
        f"Allocation completed. "
        f"Assigned {summary['assigned_count']} duties "
        f"with {summary['alert_count']} alert shortages."
    )

    return summary