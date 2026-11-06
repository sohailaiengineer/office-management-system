from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.leave import LeaveRequest, LeaveType, LeaveBalance, LeaveApproval
from app.models.employee import Employee
from app.forms.leave_forms import LeaveRequestForm, LeaveTypeForm, LeaveApprovalForm
from app.services.audit_service import log_audit
from app.utils.decorators import (
    login_required, hr_or_admin_required, get_current_user,
    get_user_role, get_managed_department
)
from app.utils import utc_now

leaves_bp = Blueprint('leaves', __name__, url_prefix='/leaves')

@leaves_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = LeaveRequest.active_query()

    # Strict role-based scoping
    if role == 'employee':
        if user.employee:
            query = query.filter_by(employee_id=user.employee.id)
        else:
            query = query.filter(db.literal(False))
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept:
            dept_emp_ids = [e.id for e in managed_dept.employees if not e.is_deleted]
            query = query.filter(LeaveRequest.employee_id.in_(dept_emp_ids))
        else:
            query = query.filter(db.literal(False))

    if status_filter:
        query = query.filter_by(approval_status=status_filter)

    pagination = query.order_by(LeaveRequest.id.desc()).paginate(page=page, per_page=10, error_out=False)

    # Leave balances for employee
    balances = []
    if user.employee:
        balances = LeaveBalance.active_query().filter_by(employee_id=user.employee.id, year=date.today().year).all()

    return render_template(
        'leaves/index.html',
        pagination=pagination,
        leaves=pagination.items,
        balances=balances,
        selected_status=status_filter,
        is_employee=(role == 'employee'),
        user_role=role
    )


@leaves_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    user = get_current_user()
    if not user.employee:
        flash('You must have an employee profile to apply for leave.', 'danger')
        return redirect(url_for('leaves.index'))

    form = LeaveRequestForm()
    form.leave_type_id.choices = [(lt.id, f"{lt.name} (Max: {lt.max_days_per_year} days)") for lt in LeaveType.active_query().all()]

    if form.validate_on_submit():
        if form.end_date.data < form.start_date.data:
            flash('End date cannot precede the start date.', 'danger')
            return render_template('leaves/apply.html', form=form)

        total_days = Decimal((form.end_date.data - form.start_date.data).days + 1)

        req = LeaveRequest(
            employee_id=user.employee.id,
            leave_type_id=form.leave_type_id.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            total_days=total_days,
            reason=form.reason.data.strip(),
            approval_status='Pending',
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(req)
        db.session.commit()

        log_audit('CREATE', 'leave_requests', req.id, None, {'days': float(total_days), 'reason': req.reason})
        flash('Leave application submitted successfully for managerial approval.', 'success')
        return redirect(url_for('leaves.index'))

    return render_template('leaves/apply.html', form=form)


@leaves_bp.route('/<int:req_id>/action', methods=['POST'])
@login_required
def take_action(req_id):
    user = get_current_user()
    role = get_user_role(user)

    if role == 'employee':
        flash('Access Denied: Employees cannot review leave applications.', 'danger')
        return redirect(url_for('leaves.index'))

    leave_req = LeaveRequest.get_active_or_404(req_id)

    # Department Manager can only approve/reject their department members
    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if not managed_dept or leave_req.employee.department_id != managed_dept.id:
            flash('Access Denied: You can only review leave applications for your department team.', 'danger')
            return redirect(url_for('leaves.index'))

    action = request.form.get('action') # Approved or Rejected
    comments = request.form.get('comments', '').strip()

    if action not in ['Approved', 'Rejected']:
        flash('Invalid action requested.', 'danger')
        return redirect(url_for('leaves.index'))

    old_status = leave_req.approval_status
    leave_req.approval_status = action
    leave_req.approver_id = user.employee.id if user.employee else None
    leave_req.approved_at = utc_now()
    leave_req.rejection_reason = comments if action == 'Rejected' else None
    leave_req.updated_by = user.id

    # Create approval trail
    approval_record = LeaveApproval(
        leave_request_id=leave_req.id,
        approver_id=user.employee.id if user.employee else leave_req.employee_id,
        action=action,
        comments=comments,
        action_at=utc_now(),
        created_by=user.id,
        updated_by=user.id
    )
    db.session.add(approval_record)

    # If approved, update leave balance
    if action == 'Approved':
        balance = LeaveBalance.active_query().filter_by(
            employee_id=leave_req.employee_id,
            leave_type_id=leave_req.leave_type_id,
            year=leave_req.start_date.year
        ).first()
        if balance:
            balance.used_days += leave_req.total_days
            balance.remaining_days = max(Decimal('0.0'), balance.total_allocated - balance.used_days)

    db.session.commit()
    log_audit('UPDATE', 'leave_requests', leave_req.id, {'status': old_status}, {'status': action, 'comments': comments})
    flash(f'Leave request #{leave_req.id} {action.lower()} successfully.', 'success')
    return redirect(url_for('leaves.index'))


@leaves_bp.route('/types', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def types():
    form = LeaveTypeForm()
    if form.validate_on_submit():
        user = get_current_user()
        lt = LeaveType(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            max_days_per_year=form.max_days_per_year.data,
            is_paid=form.is_paid.data,
            carry_forward=form.carry_forward.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(lt)
        db.session.commit()
        log_audit('CREATE', 'leave_types', lt.id, None, {'name': lt.name})
        flash(f'Leave type "{lt.name}" created.', 'success')
        return redirect(url_for('leaves.types'))

    types_list = LeaveType.active_query().all()
    return render_template('leaves/types.html', form=form, types=types_list)


@leaves_bp.route('/types/<int:type_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete_type(type_id):
    lt = LeaveType.get_active_or_404(type_id)
    user = get_current_user()
    lt.soft_delete(user_id=user.id)
    db.session.commit()
    log_audit('DELETE', 'leave_types', lt.id, {'name': lt.name}, {'is_deleted': True})
    flash(f'Leave type "{lt.name}" deleted successfully.', 'warning')
    return redirect(url_for('leaves.types'))


@leaves_bp.route('/<int:req_id>/cancel', methods=['POST'])
@login_required
def cancel_request(req_id):
    leave_req = LeaveRequest.get_active_or_404(req_id)
    user = get_current_user()
    role = get_user_role(user)

    # Only request owner or Admin/HR can cancel
    if role not in ['super_admin', 'hr_manager']:
        if not user.employee or leave_req.employee_id != user.employee.id:
            flash('Access Denied: You cannot cancel another employee\'s leave request.', 'danger')
            return redirect(url_for('leaves.index'))

    if leave_req.approval_status != 'Pending':
        flash('Only pending leave requests can be cancelled.', 'warning')
        return redirect(url_for('leaves.index'))

    old_status = leave_req.approval_status
    leave_req.approval_status = 'Cancelled'
    leave_req.updated_by = user.id
    db.session.commit()

    log_audit('UPDATE', 'leave_requests', leave_req.id, {'status': old_status}, {'status': 'Cancelled'})
    flash(f'Leave request #{leave_req.id} has been cancelled.', 'info')
    return redirect(url_for('leaves.index'))
