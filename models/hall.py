from models.db import db


class ExaminationHall(db.Model):

    __tablename__ = "examination_halls"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )


    capacity = db.Column(
        db.Integer,
        nullable=False
    )


    exams = db.relationship(
        "Exam",
        backref="hall",
        lazy=True
    )