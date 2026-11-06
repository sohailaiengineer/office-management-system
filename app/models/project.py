from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class Project(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'projects'

    name = db.Column(db.String(150), nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='SET NULL'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)
    start_date = db.Column(db.Date, default=date.today, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    budget = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False) # 0 to 100%
    priority = db.Column(db.String(30), default='Medium', nullable=False) # Low, Medium, High, Urgent
    project_status = db.Column(db.String(30), default='Planning', nullable=False) # Planning, In-Progress, On-Hold, Completed, Cancelled
    description = db.Column(db.Text, nullable=True)

    client = db.relationship('Client', backref='projects')
    department = db.relationship('Department', backref='projects')
    lead = db.relationship('Employee', foreign_keys=[lead_id])
    members = db.relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='project', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Project {self.name} ({self.code})>"


class ProjectMember(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'project_members'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    project_role = db.Column(db.String(80), default='Developer', nullable=False)
    assigned_date = db.Column(db.Date, default=date.today, nullable=False)

    project = db.relationship('Project', back_populates='members')
    employee = db.relationship('Employee', foreign_keys=[employee_id])


class Task(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'tasks'

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(30), default='Medium', nullable=False) # Low, Medium, High, Urgent
    task_status = db.Column(db.String(30), default='To-Do', nullable=False) # To-Do, In-Progress, Review, Completed
    estimated_hours = db.Column(db.Numeric(6, 2), default=0.00, nullable=False)
    actual_hours = db.Column(db.Numeric(6, 2), default=0.00, nullable=False)
    start_date = db.Column(db.Date, default=date.today, nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    completion_percentage = db.Column(db.Integer, default=0, nullable=False)
    created_by_emp_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)

    project = db.relationship('Project', back_populates='tasks')
    created_by_emp = db.relationship('Employee', foreign_keys=[created_by_emp_id])
    assignments = db.relationship('TaskAssignment', back_populates='task', cascade='all, delete-orphan')
    comments = db.relationship('TaskComment', back_populates='task', cascade='all, delete-orphan')
    attachments = db.relationship('TaskAttachment', back_populates='task', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Task {self.title} - {self.task_status}>"


class TaskAssignment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'task_assignments'

    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    assigned_date = db.Column(db.Date, default=date.today, nullable=False)

    task = db.relationship('Task', back_populates='assignments')
    employee = db.relationship('Employee', backref='task_assignments', foreign_keys=[employee_id])


class TaskComment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'task_comments'

    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    comment = db.Column(db.Text, nullable=False)

    task = db.relationship('Task', back_populates='comments')
    user = db.relationship('User', foreign_keys=[user_id])


class TaskAttachment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'task_attachments'

    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(150), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    task = db.relationship('Task', back_populates='attachments')
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])
