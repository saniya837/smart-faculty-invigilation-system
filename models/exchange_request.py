from models.db import db
from datetime import datetime


class ExchangeRequest(db.Model):
    __tablename__ = "exchange_requests"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False
    )
    target_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="CASCADE"),
        nullable=False
    )
    request_reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    target_faculty = db.relationship(
        "Faculty",
        foreign_keys=[target_faculty_id]
    )

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "target_faculty_id": self.target_faculty_id,
            "request_reason": self.request_reason,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.created_at else None
        }