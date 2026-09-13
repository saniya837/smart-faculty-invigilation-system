from models.db import db

class Assignment(db.Model):
    __tablename__ = 'assignments'
    __table_args__ = (
        db.UniqueConstraint('faculty_id', 'exam_id', name='unique_faculty_exam'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Assigned') # 'Assigned', 'Pending Exchange', 'Exchanged', 'Cancelled', 'Alert-Unassigned'
    
    # Relationships
    exchange_requests = db.relationship('ExchangeRequest', backref='assignment', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.name if self.faculty else 'Unassigned (Alert)',
            'faculty_email': self.faculty.email if self.faculty else '',
            'faculty_dept': self.faculty.department.name if self.faculty and self.faculty.department else '',
            'exam_id': self.exam_id,
            'subject': self.exam.subject if self.exam else '',
            'date': self.exam.date.strftime('%Y-%m-%d') if self.exam else '',
            'start_time': self.exam.start_time.strftime('%H:%M') if self.exam else '',
            'end_time': self.exam.end_time.strftime('%H:%M') if self.exam else '',
            'hall_name': self.exam.hall.name if self.exam and self.exam.hall else '',
            'status': self.status
        }
