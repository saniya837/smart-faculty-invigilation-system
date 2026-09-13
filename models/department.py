from models.db import db


class Department(db.Model):

    __tablename__ = "departments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    faculty = db.relationship(
        "Faculty",
        backref="department",
        lazy=True
    )

    exams = db.relationship(
        "Exam",
        backref="department",
        lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }