from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin

class SalaryStructure(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'salary_structures'

    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    basic_percentage = db.Column(db.Numeric(5, 2), default=50.00, nullable=False)
    hra_percentage = db.Column(db.Numeric(5, 2), default=20.00, nullable=False) # House Rent
    da_percentage = db.Column(db.Numeric(5, 2), default=10.00, nullable=False) # Dearness Allowance
    allowance_fixed = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    tax_percentage = db.Column(db.Numeric(5, 2), default=5.00, nullable=False)

    employee_salaries = db.relationship('EmployeeSalary', back_populates='salary_structure')

    def __repr__(self):
        return f"<SalaryStructure {self.name}>"


class EmployeeSalary(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'employee_salaries'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), unique=True, nullable=False)
    salary_structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id', ondelete='SET NULL'), nullable=True)
    basic_salary = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    house_rent = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    medical_allowance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    transport_allowance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    gross_salary = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    effective_date = db.Column(db.Date, default=date.today, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('salary', uselist=False), foreign_keys=[employee_id])
    salary_structure = db.relationship('SalaryStructure', back_populates='employee_salaries')


class Payroll(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'payrolls'

    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    total_deductions = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    net_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    payroll_status = db.Column(db.String(30), default='Draft', nullable=False) # Draft, Processed, Paid
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    details = db.relationship('PayrollDetail', back_populates='payroll', cascade='all, delete-orphan')
    processed_by_user = db.relationship('User', foreign_keys=[processed_by])

    def __repr__(self):
        return f"<Payroll {self.title} - {self.payroll_status}>"


class PayrollDetail(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'payroll_details'

    payroll_id = db.Column(db.Integer, db.ForeignKey('payrolls.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    basic = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    allowances = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    overtime_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    bonuses_total = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    deductions_total = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    net_salary = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    payment_status = db.Column(db.String(30), default='Unpaid', nullable=False) # Unpaid, Paid
    payment_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(db.String(50), default='Bank Transfer', nullable=True)

    payroll = db.relationship('Payroll', back_populates='details')
    employee = db.relationship('Employee', backref='payroll_details', foreign_keys=[employee_id])
    bonuses = db.relationship('Bonus', back_populates='payroll_detail', cascade='all, delete-orphan')
    deductions = db.relationship('Deduction', back_populates='payroll_detail', cascade='all, delete-orphan')


class Bonus(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'bonuses'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    payroll_detail_id = db.Column(db.Integer, db.ForeignKey('payroll_details.id', ondelete='SET NULL'), nullable=True)
    bonus_type = db.Column(db.String(50), nullable=False) # Performance, Festival, Referral
    amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    bonus_date = db.Column(db.Date, default=date.today, nullable=False)

    employee = db.relationship('Employee', foreign_keys=[employee_id])
    payroll_detail = db.relationship('PayrollDetail', back_populates='bonuses')


class Deduction(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'deductions'

    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    payroll_detail_id = db.Column(db.Integer, db.ForeignKey('payroll_details.id', ondelete='SET NULL'), nullable=True)
    deduction_type = db.Column(db.String(50), nullable=False) # Tax, Unpaid Leave, Fine, Loan
    amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    deduction_date = db.Column(db.Date, default=date.today, nullable=False)

    employee = db.relationship('Employee', foreign_keys=[employee_id])
    payroll_detail = db.relationship('PayrollDetail', back_populates='deductions')
