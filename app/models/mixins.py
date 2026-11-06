from datetime import datetime, timezone
from app.extensions import db

def utc_now():
    """Returns naive UTC datetime object compatible with Python 3.12+ and MySQL DATETIME."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class AuditSoftDeleteMixin:
    """
    Standard enterprise audit and soft-delete mixin.
    Provides primary key, creation/update tracking, status, and soft-delete capabilities.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(30), default='Active', nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    def soft_delete(self, user_id=None):
        """Soft-deletes the record by setting is_deleted=True and logging timestamp/actor."""
        self.is_deleted = True
        self.deleted_at = utc_now()
        self.deleted_by = user_id
        db.session.add(self)

    def restore(self, user_id=None):
        """Restores a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.updated_at = utc_now()
        self.updated_by = user_id
        db.session.add(self)

    @classmethod
    def active_query(cls):
        """Convenience query filter returning only non-deleted records."""
        return cls.query.filter_by(is_deleted=False)

    @classmethod
    def get_active(cls, record_id):
        """Find non-deleted record by ID."""
        return cls.query.filter_by(id=record_id, is_deleted=False).first()

    @classmethod
    def get_active_or_404(cls, record_id):
        """Find non-deleted record by ID or trigger 404."""
        return cls.query.filter_by(id=record_id, is_deleted=False).first_or_404()

    @classmethod
    def trash_query(cls):
        """Convenience query filter returning only soft-deleted records."""
        return cls.query.filter_by(is_deleted=True)
