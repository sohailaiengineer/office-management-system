from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.payroll import Payroll, PayrollDetail, Bonus, Deduction, SalaryStructure
from app.models.employee import Employee
from app.forms.payroll_forms import ProcessPayrollForm, BonusForm, DeductionForm
from app.services.payroll_service import generate_monthly_payroll
from app.services.audit_service import log_audit
from app.utils.decorators import (
    login_required, hr_or_admin_required, get_current_user,
    get_user_role
)

payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')

@payroll_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)

    if role == 'dept_manager':
        flash('Access Denied: Department Managers do not have permission to view company-wide payroll records.', 'danger')
        return redirect(url_for('dashboard.index'))

    if role == 'employee':
        if user.employee:
            # Show employee's own payslips
            payslips = PayrollDetail.active_query().filter_by(employee_id=user.employee.id).order_by(PayrollDetail.id.desc()).all()
            return render_template('payroll/employee_payslips.html', payslips=payslips)
        flash('No employee profile linked to your user account.', 'warning')
        return redirect(url_for('dashboard.index'))

    # Admin and HR access: payroll runs
    payrolls = Payroll.active_query().order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    form = ProcessPayrollForm()
    form.month.data = date.today().month
    form.year.data = date.today().year

    return render_template('payroll/index.html', payrolls=payrolls, form=form)


@payroll_bp.route('/generate', methods=['POST'])
@login_required
@hr_or_admin_required
def generate():
    form = ProcessPayrollForm()
    if form.validate_on_submit():
        user = get_current_user()
        payroll, success, message = generate_monthly_payroll(form.month.data, form.year.data, user_id=user.id)
        if success:
            log_audit('CREATE', 'payrolls', payroll.id, None, {'month': form.month.data, 'year': form.year.data, 'net': str(payroll.net_amount)})
            flash(message, 'success')
            return redirect(url_for('payroll.view_batch', payroll_id=payroll.id))
        else:
            flash(message, 'warning')
    return redirect(url_for('payroll.index'))


@payroll_bp.route('/<int:payroll_id>')
@login_required
@hr_or_admin_required
def view_batch(payroll_id):
    payroll = Payroll.get_active_or_404(payroll_id)
    return render_template('payroll/view_batch.html', payroll=payroll)


@payroll_bp.route('/payslip/<int:detail_id>')
@login_required
def view_payslip(detail_id):
    detail = PayrollDetail.get_active_or_404(detail_id)
    user = get_current_user()
    role = get_user_role(user)

    # Ensure access security: employee can only see their own payslip
    if role not in ['super_admin', 'hr_manager']:
        if not user.employee or detail.employee_id != user.employee.id:
            flash('Access Denied: You are not authorized to view this salary slip.', 'danger')
            return redirect(url_for('dashboard.index'))

    return render_template('payroll/payslip.html', detail=detail)


@payroll_bp.route('/bonuses/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create_bonus():
    form = BonusForm()
    form.employee_id.choices = [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]
    form.bonus_date.data = date.today()

    if form.validate_on_submit():
        user = get_current_user()
        bonus = Bonus(
            employee_id=form.employee_id.data,
            bonus_type=form.bonus_type.data,
            amount=form.amount.data,
            reason=form.reason.data.strip() if form.reason.data else None,
            bonus_date=form.bonus_date.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(bonus)
        db.session.commit()
        log_audit('CREATE', 'bonuses', bonus.id, None, {'emp_id': bonus.employee_id, 'amount': str(bonus.amount)})
        flash(f'Bonus of ${bonus.amount:,.2f} registered for employee.', 'success')
        return redirect(url_for('payroll.index'))

    return render_template('payroll/create_bonus.html', form=form)


@payroll_bp.route('/deductions/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create_deduction():
    form = DeductionForm()
    form.employee_id.choices = [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]
    if request.method == 'GET':
        form.deduction_date.data = date.today()

    if form.validate_on_submit():
        user = get_current_user()
        deduction = Deduction(
            employee_id=form.employee_id.data,
            deduction_type=form.deduction_type.data,
            amount=form.amount.data,
            reason=form.reason.data.strip() if form.reason.data else None,
            deduction_date=form.deduction_date.data,
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(deduction)
            db.session.commit()
            log_audit('CREATE', 'deductions', deduction.id, None, {'emp_id': deduction.employee_id, 'amount': str(deduction.amount)})
            flash(f'Deduction of ${deduction.amount:,.2f} recorded for employee.', 'success')
            return redirect(url_for('payroll.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to record deduction: {str(e)}', 'danger')

    return render_template('payroll/create_deduction.html', form=form)


@payroll_bp.route('/<int:payroll_id>/mark-paid', methods=['POST'])
@login_required
@hr_or_admin_required
def mark_paid(payroll_id):
    payroll = Payroll.get_active_or_404(payroll_id)
    user = get_current_user()

    payroll.payroll_status = 'Paid'
    payroll.processed_at = date.today()
    payroll.processed_by = user.id

    for d in payroll.details:
        d.payment_status = 'Paid'
        d.payment_date = date.today()

    db.session.commit()
    log_audit('UPDATE', 'payrolls', payroll.id, {'status': 'Draft'}, {'status': 'Paid'})
    flash(f'Payroll batch "{payroll.title}" marked as Paid.', 'success')
    return redirect(url_for('payroll.view_batch', payroll_id=payroll.id))
