from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin, utc_now

class LeaveType(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'leave_types'

    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    max_days_per_year = db.Column(db.Integer, default=15, nullable=False)
    is_paid = db.Column(db.Boolean, default=True, nullable=False)
    carry_forward = db.Column(db.Boolean, default=False, nullable=False)

    requests = db.relationship('LeaveRequest', back_populates='leave_type')
    balances = db.relationship('LeaveBalance', back_populates='leave_type')

    def __repr__(self):
        return f"<LeaveType {self.name}>"


class LeaveBalance(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'leave_balances'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id', ondelete='CASCADE'), nullable=False)
    year = db.Column(db.Integer, default=lambda: utc_now().year, nullable=False)
    total_allocated = db.Column(db.Numeric(5, 1), default=15.0, nullable=False)
    used_days = db.Column(db.Numeric(5, 1), default=0.0, nullable=False)
    pending_days = db.Column(db.Numeric(5, 1), default=0.0, nullable=False)
    remaining_days = db.Column(db.Numeric(5, 1), default=15.0, nullable=False)

    employee = db.relationship('Employee', backref='leave_balances', foreign_keys=[employee_id])
    leave_type = db.relationship('LeaveType', back_populates='balances')


class LeaveRequest(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'leave_requests'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id', ondelete='CASCADE'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Numeric(4, 1), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    approval_status = db.Column(db.String(30), default='Pending', nullable=False) # Pending, Approved, Rejected, Cancelled
    approver_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    employee = db.relationship('Employee', backref='leave_requests', foreign_keys=[employee_id])
    approver = db.relationship('Employee', foreign_keys=[approver_id])
    leave_type = db.relationship('LeaveType', back_populates='requests')
    approvals = db.relationship('LeaveApproval', back_populates='leave_request', cascade='all, delete-orphan')
    attachments = db.relationship('LeaveAttachment', back_populates='leave_request', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<LeaveRequest Emp:{self.employee_id} {self.approval_status}>"


class LeaveApproval(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'leave_approvals'

    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_requests.id', ondelete='CASCADE'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    action = db.Column(db.String(30), nullable=False) # Approved, Rejected
    comments = db.Column(db.Text, nullable=True)
    action_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    leave_request = db.relationship('LeaveRequest', back_populates='approvals')
    approver = db.relationship('Employee', foreign_keys=[approver_id])


class LeaveAttachment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'leave_attachments'

    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_requests.id', ondelete='CASCADE'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(150), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)

    leave_request = db.relationship('LeaveRequest', back_populates='attachments')
