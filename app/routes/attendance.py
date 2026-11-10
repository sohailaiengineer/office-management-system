from datetime import datetime, date, time
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.attendance import Attendance, AttendanceLog, Shift, Holiday
from app.models.employee import Employee, Department
from app.forms.attendance_forms import ShiftForm, HolidayForm
from app.services.audit_service import log_audit
from app.utils.decorators import (
    login_required, hr_or_admin_required, get_current_user,
    get_user_role, get_managed_department
)
from app.utils import utc_now

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    dept_id = request.args.get('department_id', '', type=str)
    status_filter = request.args.get('status', '').strip()

    query = Attendance.active_query().join(Employee, Attendance.employee_id == Employee.id)

    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Attendance.date == target_date)
        except ValueError:
            pass

    if status_filter:
        query = query.filter(Attendance.attendance_status.ilike(f"%{status_filter}%"))

    # Strict role scoping:
    if role == 'employee':
        if user.employee:
            query = query.filter(Attendance.employee_id == user.employee.id)
        else:
            query = query.filter(db.literal(False))
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept:
            query = query.filter(Employee.department_id == managed_dept.id)
        else:
            query = query.filter(db.literal(False))
    else: # Admin and HR
        if dept_id and dept_id.isdigit():
            query = query.filter(Employee.department_id == int(dept_id))

    pagination = query.order_by(Attendance.date.desc(), Attendance.id.desc()).paginate(page=page, per_page=15, error_out=False)

    # Check today's punch state for current employee
    today_att = None
    if user.employee:
        today_att = Attendance.active_query().filter_by(employee_id=user.employee.id, date=date.today()).first()

    return render_template(
        'attendance/index.html',
        pagination=pagination,
        attendances=pagination.items,
        selected_date=date_filter,
        selected_status=status_filter,
        today_att=today_att,
        user_role=role
    )


@attendance_bp.route('/punch', methods=['POST'])
@login_required
def punch():
    user = get_current_user()
    if not user.employee:
        flash('No employee profile associated with this account.', 'danger')
        return redirect(url_for('attendance.index'))

    emp_id = user.employee.id
    now = utc_now()
    today = date.today()
    ip_addr = request.remote_addr or '127.0.0.1'

    att = Attendance.active_query().filter_by(employee_id=emp_id, date=today).first()

    if not att:
        # PUNCH IN
        # Shift start calculation (default 9:00 AM)
        shift_start = datetime.combine(today, time(9, 0))
        late_min = 0
        status = 'Present'
        if now > datetime.combine(today, time(9, 15)):
            late_min = int((now - shift_start).total_seconds() / 60)
            status = 'Late'

        att = Attendance(
            employee_id=emp_id,
            date=today,
            check_in=now,
            late_minutes=late_min,
            attendance_status=status,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(att)
        db.session.flush()

        log = AttendanceLog(
            attendance_id=att.id,
            employee_id=emp_id,
            log_time=now,
            device_ip=ip_addr,
            punch_type='IN',
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(log)
        db.session.commit()

        log_audit('CREATE', 'attendance', att.id, None, {'type': 'PUNCH_IN', 'time': str(now)})
        flash(f'Punched in successfully at {now.strftime("%I:%M %p")}.', 'success')
    else:
        # PUNCH OUT
        if att.check_out:
            flash('You have already completed check-out for today.', 'info')
            return redirect(url_for('attendance.index'))

        att.check_out = now
        total_seconds = (now - att.check_in).total_seconds()
        hours = Decimal(total_seconds / 3600).quantize(Decimal('0.01'))
        att.working_hours = hours
        att.updated_by = user.id

        log = AttendanceLog(
            attendance_id=att.id,
            employee_id=emp_id,
            log_time=now,
            device_ip=ip_addr,
            punch_type='OUT',
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(log)
        db.session.commit()

        log_audit('UPDATE', 'attendance', att.id, None, {'type': 'PUNCH_OUT', 'hours': str(hours)})
        flash(f'Punched out successfully at {now.strftime("%I:%M %p")}. Total: {hours} hrs.', 'success')

    return redirect(url_for('attendance.index'))


# Shifts CRUD
@attendance_bp.route('/shifts')
@login_required
@hr_or_admin_required
def shifts():
    shifts_list = Shift.active_query().all()
    holidays_list = Holiday.active_query().all()
    return render_template('attendance/shifts.html', shifts=shifts_list, holidays=holidays_list)


@attendance_bp.route('/shifts/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create_shift():
    form = ShiftForm()
    if form.validate_on_submit():
        user = get_current_user()
        shift = Shift(
            name=form.name.data.strip(),
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            grace_minutes=form.grace_minutes.data,
            is_night_shift=form.is_night_shift.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(shift)
        db.session.commit()
        log_audit('CREATE', 'shifts', shift.id, None, {'name': shift.name})
        flash(f'Shift "{shift.name}" created successfully.', 'success')
        return redirect(url_for('attendance.shifts'))

    return render_template('attendance/create_shift.html', form=form)


@attendance_bp.route('/holidays/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create_holiday():
    form = HolidayForm()
    if form.validate_on_submit():
        user = get_current_user()
        days = (form.end_date.data - form.start_date.data).days + 1
        holiday = Holiday(
            name=form.name.data.strip(),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            total_days=max(1, days),
            is_recurring=form.is_recurring.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(holiday)
        db.session.commit()
        log_audit('CREATE', 'holidays', holiday.id, None, {'name': holiday.name})
        flash(f'Holiday "{holiday.name}" scheduled.', 'success')
        return redirect(url_for('attendance.shifts'))

    return render_template('attendance/create_holiday.html', form=form)


@attendance_bp.route('/shifts/<int:shift_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def edit_shift(shift_id):
    shift = Shift.get_active_or_404(shift_id)
    form = ShiftForm(obj=shift)

    if form.validate_on_submit():
        user = get_current_user()
        old_val = {'name': shift.name, 'start': str(shift.start_time), 'end': str(shift.end_time)}

        shift.name = form.name.data.strip()
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.grace_minutes = form.grace_minutes.data
        shift.is_night_shift = form.is_night_shift.data
        shift.updated_by = user.id

        try:
            db.session.commit()
            log_audit('UPDATE', 'shifts', shift.id, old_val, {'name': shift.name})
            flash(f'Shift "{shift.name}" updated successfully.', 'success')
            return redirect(url_for('attendance.shifts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating shift: {str(e)}', 'danger')

    return render_template('attendance/edit_shift.html', form=form, shift=shift)


@attendance_bp.route('/shifts/<int:shift_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete_shift(shift_id):
    shift = Shift.get_active_or_404(shift_id)
    user = get_current_user()
    old_val = {'id': shift.id, 'name': shift.name}
    try:
        shift.soft_delete(user_id=user.id)
        db.session.commit()
        log_audit('DELETE', 'shifts', shift.id, old_val, {'is_deleted': True})
        flash(f'Shift "{shift.name}" moved to Recycle Bin.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting shift: {str(e)}', 'danger')
    return redirect(url_for('attendance.shifts'))


@attendance_bp.route('/holidays/<int:holiday_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete_holiday(holiday_id):
    holiday = Holiday.get_active_or_404(holiday_id)
    user = get_current_user()
    old_val = {'id': holiday.id, 'name': holiday.name}
    try:
        holiday.soft_delete(user_id=user.id)
        db.session.commit()
        log_audit('DELETE', 'holidays', holiday.id, old_val, {'is_deleted': True})
        flash(f'Holiday "{holiday.name}" deleted.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting holiday: {str(e)}', 'danger')
    return redirect(url_for('attendance.shifts'))
