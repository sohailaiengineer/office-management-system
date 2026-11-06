from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class Client(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'clients'

    company_name = db.Column(db.String(150), nullable=False, index=True)
    client_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    industry = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), default='USA', nullable=False)

    contacts = db.relationship('ClientContact', back_populates='client', cascade='all, delete-orphan')
    client_projects = db.relationship('ClientProject', back_populates='client', cascade='all, delete-orphan')
    interactions = db.relationship('ClientInteraction', back_populates='client', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Client {self.company_name} ({self.client_code})>"


class ClientContact(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'client_contacts'

    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)

    client = db.relationship('Client', back_populates='contacts')


class ClientProject(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'client_projects'

    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    contract_value = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    contract_date = db.Column(db.Date, default=date.today, nullable=False)

    client = db.relationship('Client', back_populates='client_projects')
    project = db.relationship('Project', foreign_keys=[project_id])


class ClientInteraction(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'client_interactions'

    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False) # Meeting, Call, Email, Demo
    interaction_date = db.Column(db.Date, default=date.today, nullable=False)
    conducted_by_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)
    summary = db.Column(db.Text, nullable=False)
    next_follow_up = db.Column(db.Date, nullable=True)

    client = db.relationship('Client', back_populates='interactions')
    conducted_by = db.relationship('Employee', foreign_keys=[conducted_by_id])
