from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.finance import Expense, ExpenseCategory, ExpenseApproval, Invoice, Payment
from app.models.client import Client
from app.models.employee import Employee, Department
from app.forms.finance_forms import ExpenseForm, InvoiceForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, hr_or_admin_required, get_current_user, get_user_role, get_managed_department
from app.utils import utc_now

finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    dept_code = user.employee.department.code if user.employee and user.employee.department else ''
    is_finance_dept = (dept_code == 'FIN')
    is_admin = (role == 'super_admin')

    # Department Isolation Logic:
    # 1. Super Admin and Finance Department personnel see full company books.
    # 2. Other Department Managers only see expenses incurred by their own department team.
    # 3. Regular employees only see their own submitted expense claims.
    if is_admin or is_finance_dept:
        expenses = Expense.active_query().order_by(Expense.id.desc()).limit(50).all()
        invoices = Invoice.active_query().order_by(Invoice.id.desc()).limit(50).all()
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept:
            dept_emp_ids = [e.id for e in managed_dept.employees if not e.is_deleted]
            expenses = Expense.active_query().filter(Expense.paid_by_id.in_(dept_emp_ids)).order_by(Expense.id.desc()).all()
        else:
            expenses = []
        invoices = [] # Invoices are confidential to Finance and Admin
    else:
        # Regular employee
        emp_id = user.employee.id if user.employee else 0
        expenses = Expense.active_query().filter_by(paid_by_id=emp_id).order_by(Expense.id.desc()).all()
        invoices = []

    categories = ExpenseCategory.active_query().all()
    total_expense = sum(e.amount for e in expenses if e.expense_status in ['Approved', 'Reimbursed'])
    total_invoiced = sum(i.total_amount for i in invoices)
    total_received = sum(i.amount_paid for i in invoices)

    return render_template(
        'finance/index.html',
        expenses=expenses,
        invoices=invoices,
        categories=categories,
        total_expense=total_expense,
        total_invoiced=total_invoiced,
        total_received=total_received,
        is_finance_dept=is_finance_dept,
        is_admin=is_admin
    )


@finance_bp.route('/expenses/create', methods=['GET', 'POST'])
@login_required
def create_expense():
    form = ExpenseForm()
    form.category_id.choices = [(c.id, c.name) for c in ExpenseCategory.active_query().all()]
    form.expense_date.data = date.today()

    if form.validate_on_submit():
        user = get_current_user()
        emp_id = user.employee.id if user.employee else None

        expense = Expense(
            category_id=form.category_id.data,
            title=form.title.data.strip(),
            amount=form.amount.data,
            expense_date=form.expense_date.data,
            paid_by_id=emp_id,
            payment_method=form.payment_method.data,
            description=form.description.data.strip() if form.description.data else None,
            expense_status='Pending',
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(expense)
        db.session.commit()

        log_audit('CREATE', 'expenses', expense.id, None, {'title': expense.title, 'amount': str(expense.amount)})
        flash('Expense claim submitted for approval.', 'success')
        return redirect(url_for('finance.index'))

    return render_template('finance/create_expense.html', form=form)


@finance_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    user = get_current_user()
    role = get_user_role(user)
    dept_code = user.employee.department.code if user.employee and user.employee.department else ''

    # Only Super Admin and Finance Department personnel can create invoices
    if role != 'super_admin' and dept_code != 'FIN':
        flash('Access Denied: Invoicing and billing operations are restricted to Finance & Accounts and Super Admin.', 'danger')
        return redirect(url_for('finance.index'))

    form = InvoiceForm()
    form.client_id.choices = [(c.id, c.company_name) for c in Client.active_query().all()]
    if request.method == 'GET':
        form.issue_date.data = date.today()

    if form.validate_on_submit():
        if Invoice.query.filter_by(invoice_number=form.invoice_number.data.strip()).first():
            flash('Invoice number must be unique.', 'danger')
            return render_template('finance/create_invoice.html', form=form)

        invoice = Invoice(
            client_id=form.client_id.data,
            invoice_number=form.invoice_number.data.strip(),
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            total_amount=form.total_amount.data,
            tax_rate=form.tax_rate.data or Decimal('0.00'),
            notes=form.notes.data.strip() if form.notes.data else None,
            invoice_status='Sent',
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(invoice)
        db.session.commit()

        log_audit('CREATE', 'invoices', invoice.id, None, {'number': invoice.invoice_number, 'total': str(invoice.total_amount)})
        flash(f'Invoice {invoice.invoice_number} created successfully.', 'success')
        return redirect(url_for('finance.index'))

    return render_template('finance/create_invoice.html', form=form)
