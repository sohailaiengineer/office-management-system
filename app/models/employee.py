from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class Department(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'departments'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)
    parent_department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    budget = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)

    # Relationships
    locations = db.relationship('DepartmentLocation', back_populates='department', cascade='all, delete-orphan')
    designations = db.relationship('Designation', back_populates='department')
    employees = db.relationship('Employee', back_populates='department', foreign_keys='Employee.department_id')
    manager = db.relationship('Employee', foreign_keys=[manager_id])
    sub_departments = db.relationship('Department', backref=db.backref('parent_department', remote_side='Department.id'))

    def __repr__(self):
        return f"<Department {self.name}>"


class DepartmentLocation(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'department_locations'

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    location_name = db.Column(db.String(100), nullable=False)
    floor = db.Column(db.String(50), nullable=True)
    room_number = db.Column(db.String(50), nullable=True)

    department = db.relationship('Department', back_populates='locations')


class Designation(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'designations'

    title = db.Column(db.String(100), nullable=False, index=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    salary_grade = db.Column(db.String(50), nullable=True)
    min_salary = db.Column(db.Numeric(10, 2), default=0.00, nullable=True)
    max_salary = db.Column(db.Numeric(10, 2), default=0.00, nullable=True)

    department = db.relationship('Department', back_populates='designations')
    employees = db.relationship('Employee', back_populates='designation')

    def __repr__(self):
        return f"<Designation {self.title}>"


class Employee(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employees'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    emp_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id', ondelete='SET NULL'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)
    date_of_joining = db.Column(db.Date, nullable=False, default=date.today)
    date_of_exit = db.Column(db.Date, nullable=True)
    employment_type = db.Column(db.String(50), default='Full-Time', nullable=False) # Full-Time, Part-Time, Contract, Intern
    work_shift_id = db.Column(db.Integer, nullable=True) # References shifts.id
    basic_salary = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='employee', foreign_keys=[user_id])
    department = db.relationship('Department', back_populates='employees', foreign_keys=[department_id])
    designation = db.relationship('Designation', back_populates='employees', foreign_keys=[designation_id])
    manager = db.relationship('Employee', remote_side='Employee.id', foreign_keys=[manager_id], backref=db.backref('subordinates', lazy='dynamic'))

    profile = db.relationship('EmployeeProfile', back_populates='employee', uselist=False, cascade='all, delete-orphan')
    contacts = db.relationship('EmployeeContact', back_populates='employee', uselist=False, cascade='all, delete-orphan')
    addresses = db.relationship('EmployeeAddress', back_populates='employee', cascade='all, delete-orphan')
    education = db.relationship('EmployeeEducation', back_populates='employee', cascade='all, delete-orphan')
    experience = db.relationship('EmployeeExperience', back_populates='employee', cascade='all, delete-orphan')
    documents = db.relationship('EmployeeDocument', back_populates='employee', cascade='all, delete-orphan')
    skills = db.relationship('EmployeeSkill', back_populates='employee', cascade='all, delete-orphan')
    emergency_contacts = db.relationship('EmployeeEmergencyContact', back_populates='employee', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return self.user.full_name if self.user else "N/A"

    @property
    def email(self):
        return self.user.email if self.user else "N/A"

    def __repr__(self):
        return f"<Employee {self.emp_code} - {self.full_name}>"


class EmployeeProfile(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_profiles'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    marital_status = db.Column(db.String(20), default='Single', nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(80), default='American', nullable=True)
    nid_passport = db.Column(db.String(100), nullable=True)

    employee = db.relationship('Employee', back_populates='profile')


class EmployeeContact(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_contacts'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), unique=True, nullable=False)
    personal_email = db.Column(db.String(120), nullable=True)
    work_phone = db.Column(db.String(30), nullable=True)
    personal_phone = db.Column(db.String(30), nullable=True)
    skype_id = db.Column(db.String(80), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)

    employee = db.relationship('Employee', back_populates='contacts')


class EmployeeAddress(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_addresses'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    address_type = db.Column(db.String(30), default='Current', nullable=False) # Current / Permanent
    street = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), default='USA', nullable=False)

    employee = db.relationship('Employee', back_populates='addresses')


class EmployeeEducation(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_education'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    institution = db.Column(db.String(150), nullable=False)
    passing_year = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(50), nullable=True)
    major = db.Column(db.String(100), nullable=True)

    employee = db.relationship('Employee', back_populates='education')


class EmployeeExperience(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_experience'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    designation = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    responsibilities = db.Column(db.Text, nullable=True)

    employee = db.relationship('Employee', back_populates='experience')


class EmployeeDocument(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_documents'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False) # Resume, ID, Contract, Certificate
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)

    employee = db.relationship('Employee', back_populates='documents')


class EmployeeSkill(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_skills'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    proficiency_level = db.Column(db.String(50), default='Intermediate', nullable=False) # Beginner, Intermediate, Expert
    years_experience = db.Column(db.Numeric(4, 1), default=1.0, nullable=True)

    employee = db.relationship('Employee', back_populates='skills')


class EmployeeEmergencyContact(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_emergency_contacts'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    alt_phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    employee = db.relationship('Employee', back_populates='emergency_contacts')
