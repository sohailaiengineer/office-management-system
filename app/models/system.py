from datetime import datetime
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin, utc_now

class AuditLog(db.Model):
    """
    Enterprise immutable audit log entity.
    Tracks every create, update, delete, restore, and security action with JSON diffs.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False, index=True) # CREATE, UPDATE, DELETE, RESTORE, LOGIN, LOGOUT
    table_name = db.Column(db.String(100), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.Text, nullable=True) # JSON payload
    new_values = db.Column(db.Text, nullable=True) # JSON payload
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.table_name}:{self.record_id}>"


class SystemSetting(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'system_settings'

    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default='General', nullable=False) # General, Company, Attendance, Payroll
    description = db.Column(db.String(255), nullable=True)
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<SystemSetting {self.setting_key}>"


class ApprovalWorkflow(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'approval_workflows'

    module_name = db.Column(db.String(50), nullable=False) # Leave, Expense, Asset, Project
    workflow_name = db.Column(db.String(100), nullable=False)
    step_number = db.Column(db.Integer, default=1, nullable=False)
    approver_role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='SET NULL'), nullable=True)
    approver_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_mandatory = db.Column(db.Boolean, default=True, nullable=False)

    approver_role = db.relationship('Role')
    approver_user = db.relationship('User', foreign_keys=[approver_user_id])


class ApprovalHistory(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'approval_history'

    workflow_id = db.Column(db.Integer, db.ForeignKey('approval_workflows.id', ondelete='SET NULL'), nullable=True)
    module_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(30), nullable=False) # Approved, Rejected, Forwarded
    comments = db.Column(db.Text, nullable=True)
    action_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    workflow = db.relationship('ApprovalWorkflow')
    approver = db.relationship('User', foreign_keys=[approver_id])
