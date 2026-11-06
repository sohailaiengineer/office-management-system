from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.employee import (
    Employee, Department, Designation, EmployeeProfile, EmployeeContact,
    EmployeeAddress, EmployeeEducation, EmployeeExperience,
    EmployeeDocument, EmployeeSkill, EmployeeEmergencyContact
)
from app.forms.employee_forms import EmployeeForm
from app.services.audit_service import log_audit
from app.utils.decorators import (
    login_required, hr_or_admin_required, get_current_user,
    get_user_role, get_managed_department
)

employees_bp = Blueprint('employees', __name__, url_prefix='/employees')

@employees_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)

    # Regular employees manage their information via personal profile
    if role == 'employee':
        flash('Staff directory is restricted to organizational management. View your personal details in My Profile.', 'info')
        return redirect(url_for('auth.profile'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    dept_id = request.args.get('department_id', '', type=str)
    status_filter = request.args.get('status', '', type=str)

    query = Employee.active_query().join(User, Employee.user_id == User.id)

    # Department Manager is scoped strictly to their own department!
    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept:
            query = query.filter(Employee.department_id == managed_dept.id)
            departments = [managed_dept]
        else:
            query = query.filter(Employee.id == (user.employee.id if user.employee else 0))
            departments = []
    else:
        departments = Department.active_query().all()
        if dept_id and dept_id.isdigit():
            query = query.filter(Employee.department_id == int(dept_id))

    if search:
        query = query.filter(
            (Employee.emp_code.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    if status_filter:
        query = query.filter(Employee.status == status_filter)

    pagination = query.order_by(Employee.id.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'employees/index.html',
        pagination=pagination,
        employees=pagination.items,
        departments=departments,
        search=search,
        selected_dept=dept_id,
        selected_status=status_filter
    )


@employees_bp.route('/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create():
    form = EmployeeForm()
    # Populate choices
    form.department_id.choices = [(d.id, d.name) for d in Department.active_query().all()]
    form.designation_id.choices = [(d.id, f"{d.title} ({d.department.name if d.department else 'General'})") for d in Designation.active_query().all()]
    form.manager_id.choices = [(0, '-- None / Top Level --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]

    if form.validate_on_submit():
        # Check uniqueness
        if User.query.filter_by(username=form.username.data.strip()).first():
            flash('Username is already taken.', 'danger')
            return render_template('employees/create.html', form=form)
        if User.query.filter_by(email=form.email.data.strip()).first():
            flash('Email address is already registered.', 'danger')
            return render_template('employees/create.html', form=form)
        if Employee.query.filter_by(emp_code=form.emp_code.data.strip().upper()).first():
            flash('Employee code already exists.', 'danger')
            return render_template('employees/create.html', form=form)

        current_user = get_current_user()

        # Create User Account
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            password_hash=generate_password_hash('Password@123'),
            is_admin=False,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(user)
        db.session.flush()

        # Assign Employee Role
        emp_role = Role.query.filter_by(name='employee').first()
        if emp_role:
            ur = UserRole(user_id=user.id, role_id=emp_role.id, created_by=current_user.id, updated_by=current_user.id)
            db.session.add(ur)

        # Create Employee Entity
        manager_val = form.manager_id.data if form.manager_id.data != 0 else None
        employee = Employee(
            user_id=user.id,
            emp_code=form.emp_code.data.strip().upper(),
            department_id=form.department_id.data,
            designation_id=form.designation_id.data,
            manager_id=manager_val,
            employment_type=form.employment_type.data,
            date_of_joining=form.date_of_joining.data,
            basic_salary=form.basic_salary.data,
            status=form.status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(employee)
        db.session.flush()

        # Create Profile
        profile = EmployeeProfile(
            employee_id=employee.id,
            gender=form.gender.data or None,
            marital_status=form.marital_status.data or None,
            blood_group=form.blood_group.data or None,
            dob=form.dob.data or None,
            nationality=form.nationality.data or 'American',
            nid_passport=form.nid_passport.data or None,
            bio=form.bio.data or None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(profile)
        db.session.commit()

        log_audit('CREATE', 'employees', employee.id, None, {'emp_code': employee.emp_code, 'name': employee.full_name})
        flash(f'Employee {employee.full_name} created successfully (Default password: Password@123).', 'success')
        return redirect(url_for('employees.index'))

    return render_template('employees/create.html', form=form)


@employees_bp.route('/<int:emp_id>')
@login_required
def view(emp_id):
    user = get_current_user()
    role = get_user_role(user)
    employee = Employee.get_active_or_404(emp_id)

    # Strict RBAC Scoping
    if role == 'employee':
        if not user.employee or user.employee.id != emp_id:
            flash('Access Denied: You are not authorized to view other employees\' records.', 'danger')
            return redirect(url_for('dashboard.index'))
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if not managed_dept or employee.department_id != managed_dept.id:
            flash('Access Denied: You cannot view employee records outside your department.', 'danger')
            return redirect(url_for('employees.index'))

    return render_template('employees/view.html', employee=employee, user_role=role)


@employees_bp.route('/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def edit(emp_id):
    employee = Employee.get_active_or_404(emp_id)
    user = employee.user
    profile = employee.profile

    form = EmployeeForm(obj=employee)
    form.department_id.choices = [(d.id, d.name) for d in Department.active_query().all()]
    form.designation_id.choices = [(d.id, f"{d.title} ({d.department.name if d.department else 'General'})") for d in Designation.active_query().all()]
    form.manager_id.choices = [(0, '-- None / Top Level --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().filter(Employee.id != emp_id).all()]

    if request.method == 'GET':
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.email.data = user.email
        form.username.data = user.username
        form.phone.data = user.phone
        form.manager_id.data = employee.manager_id or 0
        if profile:
            form.gender.data = profile.gender
            form.marital_status.data = profile.marital_status
            form.blood_group.data = profile.blood_group
            form.dob.data = profile.dob
            form.nationality.data = profile.nationality
            form.nid_passport.data = profile.nid_passport
            form.bio.data = profile.bio

    if form.validate_on_submit():
        current_user = get_current_user()
        old_val = {'emp_code': employee.emp_code, 'name': employee.full_name, 'status': employee.status}

        # Update User
        user.first_name = form.first_name.data.strip()
        user.last_name = form.last_name.data.strip()
        user.email = form.email.data.strip()
        user.phone = form.phone.data.strip() if form.phone.data else None
        user.updated_by = current_user.id

        # Update Employee
        employee.department_id = form.department_id.data
        employee.designation_id = form.designation_id.data
        employee.manager_id = form.manager_id.data if form.manager_id.data != 0 else None
        employee.employment_type = form.employment_type.data
        employee.date_of_joining = form.date_of_joining.data
        employee.basic_salary = form.basic_salary.data
        employee.status = form.status.data
        employee.updated_by = current_user.id

        # Update or create profile
        if not profile:
            profile = EmployeeProfile(employee_id=employee.id, created_by=current_user.id)
            db.session.add(profile)
        profile.gender = form.gender.data or None
        profile.marital_status = form.marital_status.data or None
        profile.blood_group = form.blood_group.data or None
        profile.dob = form.dob.data or None
        profile.nationality = form.nationality.data or 'American'
        profile.nid_passport = form.nid_passport.data or None
        profile.bio = form.bio.data or None
        profile.updated_by = current_user.id

        db.session.commit()
        log_audit('UPDATE', 'employees', employee.id, old_val, {'emp_code': employee.emp_code, 'name': employee.full_name, 'status': employee.status})
        flash(f'Employee {employee.full_name} updated successfully.', 'success')
        return redirect(url_for('employees.view', emp_id=employee.id))

    return render_template('employees/edit.html', form=form, employee=employee)


@employees_bp.route('/<int:emp_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete(emp_id):
    employee = Employee.get_active_or_404(emp_id)
    current_user = get_current_user()

    old_val = {'id': employee.id, 'emp_code': employee.emp_code, 'name': employee.full_name}
    employee.soft_delete(user_id=current_user.id)
    if employee.user:
        employee.user.soft_delete(user_id=current_user.id)

    db.session.commit()
    log_audit('DELETE', 'employees', employee.id, old_val, {'is_deleted': True})
    flash(f'Employee {employee.full_name} moved to Recycle Bin (Soft Deleted).', 'warning')
    return redirect(url_for('employees.index'))
