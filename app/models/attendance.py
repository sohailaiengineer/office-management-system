from datetime import datetime, date, time
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin, utc_now

class Shift(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'shifts'

    name = db.Column(db.String(100), unique=True, nullable=False)
    start_time = db.Column(db.Time, nullable=False, default=time(9, 0))
    end_time = db.Column(db.Time, nullable=False, default=time(17, 0))
    grace_minutes = db.Column(db.Integer, default=15, nullable=False)
    half_day_hours = db.Column(db.Numeric(4, 2), default=4.00, nullable=False)
    is_night_shift = db.Column(db.Boolean, default=False, nullable=False)

    assignments = db.relationship('ShiftAssignment', back_populates='shift', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Shift {self.name}>"


class ShiftAssignment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'shift_assignments'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    employee = db.relationship('Employee', backref='shift_assignments', foreign_keys=[employee_id])
    shift = db.relationship('Shift', back_populates='assignments')


class Attendance(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'attendance'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    working_hours = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)
    late_minutes = db.Column(db.Integer, default=0, nullable=False)
    early_leaving_minutes = db.Column(db.Integer, default=0, nullable=False)
    attendance_status = db.Column(db.String(30), default='Present', nullable=False) # Present, Late, Absent, Half-Day, On-Leave

    employee = db.relationship('Employee', backref='attendances', foreign_keys=[employee_id])
    logs = db.relationship('AttendanceLog', back_populates='attendance', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Attendance Emp:{self.employee_id} {self.date} {self.attendance_status}>"


class AttendanceLog(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'attendance_logs'

    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id', ondelete='CASCADE'), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    log_time = db.Column(db.DateTime, default=utc_now, nullable=False)
    device_ip = db.Column(db.String(45), nullable=True)
    punch_type = db.Column(db.String(10), nullable=False) # IN / OUT

    attendance = db.relationship('Attendance', back_populates='logs')
    employee = db.relationship('Employee', foreign_keys=[employee_id])


class Holiday(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'holidays'

    name = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, default=1, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Holiday {self.name}>"
