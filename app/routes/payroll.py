from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.payroll import Payroll, PayrollDetail, Bonus, Deduction, SalaryStructure, EmployeeSalary
from app.models.employee import Employee
from app.forms.payroll_forms import ProcessPayrollForm, IndividualSalaryForm, BonusForm, DeductionForm
from app.services.payroll_service import generate_monthly_payroll, calculate_employee_salary_components
from app.services.audit_service import log_audit
from app.services.email_service import send_salary_notification_email
from app.services.notification_service import create_system_notification
from app.utils.decorators import (
    login_required, hr_or_admin_required, get_current_user,
    get_user_role, get_managed_department
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

    # Admin and HR access: payroll batches + master salary records
    month_filter = request.args.get('month', type=int)
    year_filter = request.args.get('year', type=int)
    status_filter = request.args.get('status', '').strip()
    emp_filter = request.args.get('employee_id', type=int)

    payrolls = Payroll.active_query().order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    
    slips_query = PayrollDetail.active_query().join(Payroll, PayrollDetail.payroll_id == Payroll.id)
    if month_filter:
        slips_query = slips_query.filter(Payroll.month == month_filter)
    if year_filter:
        slips_query = slips_query.filter(Payroll.year == year_filter)
    if status_filter:
        slips_query = slips_query.filter(PayrollDetail.payment_status == status_filter)
    if emp_filter:
        slips_query = slips_query.filter(PayrollDetail.employee_id == emp_filter)

    salary_slips = slips_query.order_by(PayrollDetail.id.desc()).limit(100).all()

    form = ProcessPayrollForm()
    form.month.data = date.today().month
    form.year.data = date.today().year

    all_employees = Employee.active_query().all()

    return render_template(
        'payroll/index.html',
        payrolls=payrolls,
        salary_slips=salary_slips,
        form=form,
        all_employees=all_employees,
        month_filter=month_filter,
        year_filter=year_filter,
        status_filter=status_filter,
        emp_filter=emp_filter
    )


@payroll_bp.route('/my-slips', endpoint='my_slips')
@login_required
def my_slips():
    user = get_current_user()
    role = get_user_role(user)
    if not user.employee:
        flash('No employee profile linked to your account.', 'warning')
        return redirect(url_for('dashboard.index'))
    payslips = PayrollDetail.active_query().filter_by(employee_id=user.employee.id).order_by(PayrollDetail.id.desc()).all()
    return render_template('payroll/employee_payslips.html', payslips=payslips)


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


@payroll_bp.route('/generate-individual', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def generate_individual():
    form = IndividualSalaryForm()
    active_employees = Employee.active_query().all()
    form.employee_id.choices = [(e.id, f"{e.emp_code} - {e.full_name} ({e.department.name if e.department else 'General'})") for e in active_employees]

    if request.method == 'GET':
        form.month.data = date.today().month
        form.year.data = date.today().year
        # Prepopulate basic salary if employee selected
        emp_id = request.args.get('employee_id', type=int)
        if emp_id:
            form.employee_id.data = emp_id
            comps = calculate_employee_salary_components(emp_id)
            form.basic.data = comps['basic']
            form.allowances.data = comps['house_rent'] + comps['medical'] + comps['transport']

    if form.validate_on_submit():
        user = get_current_user()
        emp_id = form.employee_id.data
        month = form.month.data
        year = form.year.data

        # 1. Locate or create monthly Payroll header
        payroll = Payroll.active_query().filter_by(month=month, year=year).first()
        if not payroll:
            payroll = Payroll(
                month=month,
                year=year,
                title=f"Payroll - {date(year, month, 1).strftime('%B %Y')}",
                total_amount=Decimal('0.00'),
                total_deductions=Decimal('0.00'),
                net_amount=Decimal('0.00'),
                payroll_status='Draft',
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(payroll)
            db.session.flush()

        # 2. Prevent duplicate salary generation for the same employee and month/year
        existing_detail = PayrollDetail.active_query().filter_by(payroll_id=payroll.id, employee_id=emp_id).first()
        if existing_detail:
            flash(f'Duplicate Alert: A salary record already exists for this employee for {month}/{year}. View slip #{existing_detail.id}.', 'warning')
            return redirect(url_for('payroll.index'))

        # 3. Calculate net salary
        basic = Decimal(str(form.basic.data or 0.00))
        allowances = Decimal(str(form.allowances.data or 0.00))
        bonuses = Decimal(str(form.bonuses_total.data or 0.00))
        overtime = Decimal(str(form.overtime_amount.data or 0.00))
        deductions = Decimal(str(form.deductions_total.data or 0.00))
        gross = basic + allowances + bonuses + overtime
        net_salary = gross - deductions

        # 4. Create PayrollDetail
        detail = PayrollDetail(
            payroll_id=payroll.id,
            employee_id=emp_id,
            basic=basic,
            allowances=allowances,
            overtime_amount=overtime,
            bonuses_total=bonuses,
            deductions_total=deductions,
            net_salary=net_salary,
            payment_status=form.payment_status.data,
            payment_date=date.today() if form.payment_status.data == 'Paid' else None,
            payment_method=form.payment_method.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(detail)

        # 5. Update Payroll Header Totals
        payroll.total_amount = (payroll.total_amount or Decimal('0.00')) + gross
        payroll.total_deductions = (payroll.total_deductions or Decimal('0.00')) + deductions
        payroll.net_amount = (payroll.net_amount or Decimal('0.00')) + net_salary

        db.session.commit()

        # Send Private Salary Notification to recipient employee ONLY
        target_employee = Employee.get_active_or_404(emp_id)
        send_salary_notification_email(detail, target_employee)
        if target_employee.user_id:
            create_system_notification(
                user_id=target_employee.user_id,
                title=f"Salary Statement Available ({month:02d}/{year})",
                message=f"Your salary slip for {month:02d}/{year} (Net: ${net_salary:,.2f}) has been generated. Disbursal status: {detail.payment_status}.",
                notification_type="Payroll"
            )

        log_audit('CREATE', 'payroll_details', detail.id, None, {
            'employee_id': emp_id,
            'month': month,
            'year': year,
            'net_salary': str(net_salary),
            'status': detail.payment_status
        })

        flash(f'Salary slip generated successfully for {target_employee.full_name} (Net: ${net_salary:,.2f}). Private notification dispatched.', 'success')
        return redirect(url_for('payroll.index'))

    return render_template('payroll/generate_individual.html', form=form)


@payroll_bp.route('/<int:payroll_id>')
@login_required
@hr_or_admin_required
def view_batch(payroll_id):
    payroll = Payroll.get_active_or_404(payroll_id)
    return render_template('payroll/view_batch.html', payroll=payroll)


@payroll_bp.route('/payslip/<int:detail_id>', endpoint='view_payslip')
@payroll_bp.route('/payslip/<int:detail_id>', endpoint='payslip')
@payroll_bp.route('/slips/<int:detail_id>', endpoint='view_slip')
@payroll_bp.route('/<int:detail_id>/payslip')
@login_required
def view_payslip(detail_id):
    detail = PayrollDetail.get_active_or_404(detail_id)
    user = get_current_user()
    role = get_user_role(user)

    # Access security:
    # Super Admin and HR can view any payslip.
    # Dept Manager can view their department members' slips.
    # Employee can ONLY view their own payslip.
    if role not in ['super_admin', 'hr_manager']:
        if role == 'dept_manager':
            flash('Access Denied: Department Managers are not authorized to view individual salary data.', 'danger')
            return redirect(url_for('dashboard.index'))
        else:
            if not user.employee or detail.employee_id != user.employee.id:
                flash('Access Denied: You are not authorized to view this salary slip.', 'danger')
                return redirect(url_for('dashboard.index'))

    return render_template('payroll/payslip.html', detail=detail)


@payroll_bp.route('/detail/<int:detail_id>/status', methods=['POST'])
@login_required
@hr_or_admin_required
def update_detail_status(detail_id):
    detail = PayrollDetail.get_active_or_404(detail_id)
    user = get_current_user()
    new_status = request.form.get('status', '').strip()

    if new_status in ['Paid', 'Pending', 'Unpaid']:
        old_status = detail.payment_status
        detail.payment_status = new_status
        if new_status == 'Paid':
            detail.payment_date = date.today()
        detail.updated_by = user.id
        db.session.commit()
        log_audit('UPDATE', 'payroll_details', detail.id, {'status': old_status}, {'status': new_status})
        flash(f'Salary slip #{detail.id} status updated to {new_status}.', 'success')
    else:
        flash('Invalid payment status specified.', 'danger')

    return redirect(request.referrer or url_for('payroll.index'))


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
