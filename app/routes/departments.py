from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.employee import Department, Designation, Employee
from app.forms.employee_forms import DepartmentForm, DesignationForm
from app.services.audit_service import log_audit
from app.utils.decorators import (
    login_required, hr_or_admin_required, get_current_user,
    get_user_role, get_managed_department
)

departments_bp = Blueprint('departments', __name__, url_prefix='/departments')

@departments_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)

    if role == 'employee':
        flash('Department governance is reserved for administrative management.', 'info')
        return redirect(url_for('dashboard.index'))

    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        departments = [managed_dept] if managed_dept else []
        designations = Designation.active_query().filter_by(department_id=managed_dept.id).all() if managed_dept else []
    else:
        departments = Department.active_query().all()
        designations = Designation.active_query().all()

    return render_template('departments/index.html', departments=departments, designations=designations)


@departments_bp.route('/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create():
    form = DepartmentForm()
    if form.validate_on_submit():
        if Department.query.filter_by(code=form.code.data.strip().upper()).first():
            flash('Department code already exists.', 'danger')
            return render_template('departments/create.html', form=form)

        current_user = get_current_user()
        dept = Department(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            budget=form.budget.data,
            description=form.description.data.strip() if form.description.data else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(dept)
        db.session.commit()

        log_audit('CREATE', 'departments', dept.id, None, {'name': dept.name, 'code': dept.code})
        flash(f'Department "{dept.name}" created successfully.', 'success')
        return redirect(url_for('departments.index'))

    return render_template('departments/create.html', form=form)


@departments_bp.route('/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def edit(dept_id):
    dept = Department.get_active_or_404(dept_id)
    form = DepartmentForm(obj=dept)

    if form.validate_on_submit():
        current_user = get_current_user()
        old_val = {'name': dept.name, 'code': dept.code, 'budget': str(dept.budget)}

        dept.name = form.name.data.strip()
        dept.code = form.code.data.strip().upper()
        dept.budget = form.budget.data
        dept.description = form.description.data.strip() if form.description.data else None
        dept.updated_by = current_user.id

        db.session.commit()
        log_audit('UPDATE', 'departments', dept.id, old_val, {'name': dept.name, 'code': dept.code})
        flash(f'Department "{dept.name}" updated successfully.', 'success')
        return redirect(url_for('departments.index'))

    return render_template('departments/edit.html', form=form, department=dept)


@departments_bp.route('/<int:dept_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete(dept_id):
    dept = Department.get_active_or_404(dept_id)
    current_user = get_current_user()

    old_val = {'id': dept.id, 'name': dept.name, 'code': dept.code}
    dept.soft_delete(user_id=current_user.id)
    db.session.commit()

    log_audit('DELETE', 'departments', dept.id, old_val, {'is_deleted': True})
    flash(f'Department "{dept.name}" moved to Recycle Bin.', 'warning')
    return redirect(url_for('departments.index'))


# Designations CRUD
@departments_bp.route('/designations/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create_designation():
    form = DesignationForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.active_query().all()]

    if form.validate_on_submit():
        if Designation.query.filter_by(code=form.code.data.strip().upper()).first():
            flash('Designation code already exists.', 'danger')
            return render_template('departments/create_designation.html', form=form)

        current_user = get_current_user()
        desig = Designation(
            title=form.title.data.strip(),
            code=form.code.data.strip().upper(),
            department_id=form.department_id.data,
            salary_grade=form.salary_grade.data.strip() if form.salary_grade.data else None,
            min_salary=form.min_salary.data,
            max_salary=form.max_salary.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(desig)
        db.session.commit()

        log_audit('CREATE', 'designations', desig.id, None, {'title': desig.title, 'code': desig.code})
        flash(f'Designation "{desig.title}" created successfully.', 'success')
        return redirect(url_for('departments.index'))

    return render_template('departments/create_designation.html', form=form)


@departments_bp.route('/designations/<int:desig_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def edit_designation(desig_id):
    desig = Designation.get_active_or_404(desig_id)
    form = DesignationForm(obj=desig)
    form.department_id.choices = [(d.id, d.name) for d in Department.active_query().all()]

    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        existing = Designation.query.filter(Designation.code == code, Designation.id != desig.id).first()
        if existing:
            flash('Designation code already exists.', 'danger')
            return render_template('departments/edit_designation.html', form=form, designation=desig)

        current_user = get_current_user()
        old_val = {'title': desig.title, 'code': desig.code}

        desig.title = form.title.data.strip()
        desig.code = code
        desig.department_id = form.department_id.data
        desig.salary_grade = form.salary_grade.data.strip() if form.salary_grade.data else None
        desig.min_salary = form.min_salary.data
        desig.max_salary = form.max_salary.data
        desig.updated_by = current_user.id

        try:
            db.session.commit()
            log_audit('UPDATE', 'designations', desig.id, old_val, {'title': desig.title, 'code': desig.code})
            flash(f'Designation "{desig.title}" updated successfully.', 'success')
            return redirect(url_for('departments.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating designation: {str(e)}', 'danger')

    return render_template('departments/edit_designation.html', form=form, designation=desig)


@departments_bp.route('/designations/<int:desig_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete_designation(desig_id):
    desig = Designation.get_active_or_404(desig_id)
    current_user = get_current_user()

    old_val = {'id': desig.id, 'title': desig.title}
    desig.soft_delete(user_id=current_user.id)
    db.session.commit()

    log_audit('DELETE', 'designations', desig.id, old_val, {'is_deleted': True})
    flash(f'Designation "{desig.title}" moved to Recycle Bin.', 'warning')
    return redirect(url_for('departments.index'))
