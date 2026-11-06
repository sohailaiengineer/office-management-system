from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin, utc_now

class User(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'users'

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    avatar = db.Column(db.String(255), nullable=True, default='default-avatar.png')
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    user_roles = db.relationship('UserRole', back_populates='user', cascade='all, delete-orphan', foreign_keys='UserRole.user_id')
    employee = db.relationship('Employee', back_populates='user', uselist=False, foreign_keys='Employee.user_id')
    login_history = db.relationship('LoginHistory', back_populates='user', cascade='all, delete-orphan', foreign_keys='LoginHistory.user_id')
    sessions = db.relationship('UserSession', back_populates='user', cascade='all, delete-orphan', foreign_keys='UserSession.user_id')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(ur.role.name.lower() == role_name.lower() for ur in self.user_roles if ur.role and not ur.is_deleted)

    @property
    def role_names(self):
        return [ur.role.display_name for ur in self.user_roles if ur.role and not ur.is_deleted]

    @property
    def primary_role(self):
        roles = [ur.role.name for ur in self.user_roles if ur.role and not ur.is_deleted]
        if 'super_admin' in roles:
            return 'Super Admin'
        elif 'hr_manager' in roles:
            return 'HR Manager'
        elif 'dept_manager' in roles:
            return 'Department Manager'
        elif 'employee' in roles:
            return 'Employee'
        return 'User'

    def __repr__(self):
        return f"<User {self.username}>"


class Role(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'roles'

    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_system = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    user_roles = db.relationship('UserRole', back_populates='role', cascade='all, delete-orphan')
    role_permissions = db.relationship('RolePermission', back_populates='role', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'permissions'

    code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    module = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    role_permissions = db.relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Permission {self.code}>"


class UserRole(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'user_roles'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    user = db.relationship('User', back_populates='user_roles', foreign_keys=[user_id])
    role = db.relationship('Role', back_populates='user_roles', foreign_keys=[role_id])


class RolePermission(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'role_permissions'

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)

    role = db.relationship('Role', back_populates='role_permissions')
    permission = db.relationship('Permission', back_populates='role_permissions')


class UserSession(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'user_sessions'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', back_populates='sessions', foreign_keys=[user_id])


class LoginHistory(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'login_history'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), nullable=False)  # Success / Failed
    failure_reason = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', back_populates='login_history', foreign_keys=[user_id])


class PasswordResetToken(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'password_reset_tokens'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])
