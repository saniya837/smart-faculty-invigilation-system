from models.db import db

class Faculty(db.Model):
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phone = db.Column(db.String(15), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    designation = db.Column(db.String(50), nullable=False)
    unavailable_dates = db.Column(db.Text, default='') # Comma-separated YYYY-MM-DD
    max_duties = db.Column(db.Integer, nullable=False, default=5)
    total_assigned_duties = db.Column(db.Integer, nullable=False, default=0)
    
    # Relationships
    assignments = db.relationship('Assignment', backref='faculty', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='faculty', cascade='all, delete-orphan')
    user = db.relationship('User', backref='faculty', uselist=False, cascade='all, delete-orphan')

    def get_unavailable_dates_list(self):
        if not self.unavailable_dates:
            return []
        return [d.strip() for d in self.unavailable_dates.split(',') if d.strip()]

    def is_available_on(self, date_val):
        # date_val can be datetime.date or string YYYY-MM-DD
        date_str = str(date_val)
        return date_str not in self.get_unavailable_dates_list()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else '',
            'designation': self.designation,
            'unavailable_dates': self.get_unavailable_dates_list(),
            'max_duties': self.max_duties,
            'total_assigned_duties': self.total_assigned_duties
        }
