from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class AssetCategory(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'asset_categories'

    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    assets = db.relationship('Asset', back_populates='category')

    def __repr__(self):
        return f"<AssetCategory {self.name}>"


class Asset(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'assets'

    category_id = db.Column(db.Integer, db.ForeignKey('asset_categories.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False, index=True)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False, index=True)
    serial_number = db.Column(db.String(100), unique=True, nullable=True)
    purchase_date = db.Column(db.Date, nullable=False, default=date.today)
    purchase_cost = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    warranty_expiry = db.Column(db.Date, nullable=True)
    condition = db.Column(db.String(30), default='New', nullable=False) # New, Good, Fair, Damaged
    asset_status = db.Column(db.String(30), default='Available', nullable=False) # Available, Assigned, Under-Maintenance, Disposed

    category = db.relationship('AssetCategory', back_populates='assets')
    assignments = db.relationship('AssetAssignment', back_populates='asset', cascade='all, delete-orphan')
    maintenances = db.relationship('AssetMaintenance', back_populates='asset', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Asset {self.name} ({self.asset_tag})>"


class AssetAssignment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'asset_assignments'

    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    assigned_date = db.Column(db.Date, default=date.today, nullable=False)
    returned_date = db.Column(db.Date, nullable=True)
    condition_at_assign = db.Column(db.String(30), default='Good', nullable=False)
    condition_at_return = db.Column(db.String(30), nullable=True)

    asset = db.relationship('Asset', back_populates='assignments')
    employee = db.relationship('Employee', backref='assigned_assets', foreign_keys=[employee_id])


class AssetMaintenance(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'asset_maintenance'

    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    maintenance_type = db.Column(db.String(100), nullable=False) # Repair, Servicing, Upgrade
    cost = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    service_date = db.Column(db.Date, default=date.today, nullable=False)
    vendor = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    maintenance_status = db.Column(db.String(30), default='Completed', nullable=False) # Scheduled, In-Progress, Completed

    asset = db.relationship('Asset', back_populates='maintenances')


class AssetRequest(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'asset_requests'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('asset_categories.id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(30), default='Medium', nullable=False) # Low, Medium, High
    request_status = db.Column(db.String(30), default='Pending', nullable=False) # Pending, Approved, Rejected, Fulfilled
    approved_by_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)

    employee = db.relationship('Employee', foreign_keys=[employee_id])
    category = db.relationship('AssetCategory')
    approved_by = db.relationship('Employee', foreign_keys=[approved_by_id])
