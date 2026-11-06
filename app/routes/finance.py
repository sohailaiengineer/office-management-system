from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.finance import Expense, ExpenseCategory, ExpenseApproval, Invoice, Payment
from app.models.client import Client
from app.models.employee import Employee
from app.forms.finance_forms import ExpenseForm, InvoiceForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, hr_or_admin_required, get_current_user
from app.utils import utc_now

finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.route('/')
@login_required
def index():
    user = get_current_user()
    expenses = Expense.active_query().order_by(Expense.id.desc()).limit(20).all()
    invoices = Invoice.active_query().order_by(Invoice.id.desc()).limit(20).all()
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
        total_received=total_received
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


@finance_bp.route('/expenses/<int:exp_id>/action', methods=['POST'])
@login_required
@hr_or_admin_required
def approve_expense(exp_id):
    expense = Expense.get_active_or_404(exp_id)
    action = request.form.get('action') # Approved or Rejected
    user = get_current_user()

    if action in ['Approved', 'Rejected']:
        expense.expense_status = action
        expense.updated_by = user.id

        approval = ExpenseApproval(
            expense_id=expense.id,
            approver_id=user.employee.id if user.employee else expense.paid_by_id,
            action=action,
            comments=request.form.get('comments', ''),
            action_at=utc_now(),
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(approval)
        db.session.commit()
        log_audit('UPDATE', 'expenses', expense.id, None, {'status': action})
        flash(f'Expense claim #{expense.id} {action.lower()}.', 'success')

    return redirect(url_for('finance.index'))


@finance_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create_invoice():
    form = InvoiceForm()
    form.client_id.choices = [(c.id, c.company_name) for c in Client.active_query().all()]
    form.issue_date.data = date.today()

    if form.validate_on_submit():
        user = get_current_user()
        inv = Invoice(
            invoice_number=form.invoice_number.data.strip(),
            client_id=form.client_id.data,
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            subtotal=form.subtotal.data,
            tax_amount=form.tax_amount.data,
            total_amount=form.total_amount.data,
            amount_paid=Decimal('0.00'),
            payment_status='Sent',
            notes=form.notes.data.strip() if form.notes.data else None,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(inv)
        db.session.commit()

        log_audit('CREATE', 'invoices', inv.id, None, {'invoice_number': inv.invoice_number, 'total': str(inv.total_amount)})
        flash(f'Invoice {inv.invoice_number} generated successfully.', 'success')
        return redirect(url_for('finance.index'))

    return render_template('finance/create_invoice.html', form=form)


@finance_bp.route('/invoices/<int:inv_id>/payment', methods=['POST'])
@login_required
@hr_or_admin_required
def record_payment(inv_id):
    invoice = Invoice.get_active_or_404(inv_id)
    user = get_current_user()
    amount = Decimal(request.form.get('amount', '0.00'))
    method = request.form.get('payment_method', 'Bank Transfer')
    ref = request.form.get('transaction_ref', '')

    if amount > 0:
        pay = Payment(
            invoice_id=invoice.id,
            amount=amount,
            payment_date=date.today(),
            payment_method=method,
            transaction_ref=ref,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(pay)
        invoice.amount_paid += amount
        if invoice.amount_paid >= invoice.total_amount:
            invoice.payment_status = 'Paid'
        else:
            invoice.payment_status = 'Partially-Paid'

        db.session.commit()
        log_audit('CREATE', 'payments', pay.id, None, {'invoice_id': invoice.id, 'amount': str(amount)})
        flash(f'Payment of ${amount:,.2f} recorded for Invoice {invoice.invoice_number}.', 'success')

    return redirect(url_for('finance.index'))
