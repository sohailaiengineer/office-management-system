from datetime import datetime, date
from app.extensions import db
from app.models.mixins import AuditSoftDeleteMixin, utc_now

class ExpenseCategory(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'expense_categories'

    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    monthly_budget = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)

    expenses = db.relationship('Expense', back_populates='category')

    def __repr__(self):
        return f"<ExpenseCategory {self.name}>"


class Expense(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'expenses'

    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    expense_date = db.Column(db.Date, default=date.today, nullable=False)
    paid_by_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True)
    payment_method = db.Column(db.String(50), default='Cash', nullable=False) # Cash, Card, Bank Transfer
    receipt_path = db.Column(db.String(255), nullable=True)
    expense_status = db.Column(db.String(30), default='Pending', nullable=False) # Pending, Approved, Rejected, Reimbursed
    description = db.Column(db.Text, nullable=True)

    category = db.relationship('ExpenseCategory', back_populates='expenses')
    paid_by = db.relationship('Employee', foreign_keys=[paid_by_id])
    approvals = db.relationship('ExpenseApproval', back_populates='expense', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Expense {self.title} - ${self.amount}>"


class ExpenseApproval(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'expense_approvals'

    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(30), nullable=False) # Approved, Rejected
    comments = db.Column(db.Text, nullable=True)
    action_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    expense = db.relationship('Expense', back_populates='approvals')
    approver = db.relationship('Employee', foreign_keys=[approver_id])


class Invoice(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'invoices'

    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='SET NULL'), nullable=True)
    issue_date = db.Column(db.Date, default=date.today, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    amount_paid = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    payment_status = db.Column(db.String(30), default='Draft', nullable=False) # Draft, Sent, Partially-Paid, Paid, Overdue
    notes = db.Column(db.Text, nullable=True)

    client = db.relationship('Client', backref='invoices')
    payments = db.relationship('Payment', back_populates='invoice', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Invoice {self.invoice_number} - ${self.total_amount}>"


class Payment(db.Model, AuditSoftDeleteMixin):
    __tablename__ = 'payments'

    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_date = db.Column(db.Date, default=date.today, nullable=False)
    payment_method = db.Column(db.String(50), default='Bank Transfer', nullable=False)
    transaction_ref = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    invoice = db.relationship('Invoice', back_populates='payments')
