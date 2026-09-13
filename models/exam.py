from models.db import db


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    hall_id = db.Column(
        db.Integer,
        db.ForeignKey("examination_halls.id", ondelete="CASCADE"),
        nullable=False
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False
    )

    required_invigilators = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    assignments = db.relationship(
        "Assignment",
        backref="exam",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "date": self.date.strftime("%Y-%m-%d"),
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "hall_id": self.hall_id,
            "hall_name": self.hall.name if self.hall else "",
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else "",
            "required_invigilators": self.required_invigilators,
            "assigned_count": len(
                [a for a in self.assignments if a.faculty_id is not None]
            )
        }