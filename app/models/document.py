from datetime import datetime
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class DocumentCategory(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'document_categories'

    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    documents = db.relationship('Document', back_populates='category')

    def __repr__(self):
        return f"<DocumentCategory {self.name}>"


class Document(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'documents'

    category_id = db.Column(db.Integer, db.ForeignKey('document_categories.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True) # in bytes
    file_type = db.Column(db.String(50), nullable=True) # pdf, docx, etc.
    is_confidential = db.Column(db.Boolean, default=False, nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)

    category = db.relationship('DocumentCategory', back_populates='documents')
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])
    department = db.relationship('Department')
    versions = db.relationship('DocumentVersion', back_populates='document', cascade='all, delete-orphan')
    shares = db.relationship('DocumentShare', back_populates='document', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Document {self.title}>"


class DocumentVersion(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'document_versions'

    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.String(20), default='1.0', nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    change_summary = db.Column(db.String(255), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    document = db.relationship('Document', back_populates='versions')
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])


class DocumentShare(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'document_shares'

    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    shared_with_role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=True)
    permission_level = db.Column(db.String(30), default='View', nullable=False) # View, Download, Edit
    shared_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    document = db.relationship('Document', back_populates='shares')
    shared_with_user = db.relationship('User', foreign_keys=[shared_with_user_id])
    shared_with_role = db.relationship('Role')
    shared_by = db.relationship('User', foreign_keys=[shared_by_id])
