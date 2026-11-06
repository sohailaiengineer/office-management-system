from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.project import Project, ProjectMember, Task
from app.models.client import Client
from app.models.employee import Department, Employee
from app.forms.project_forms import ProjectForm
from app.services.audit_service import log_audit
from app.utils.decorators import (
    login_required, manager_or_admin_required, get_current_user,
    get_user_role, get_managed_department
)

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    status_filter = request.args.get('status', '')
    query = Project.active_query()

    # Role Scoping:
    if role == 'employee':
        if user.employee:
            query = query.join(Project.members).filter(ProjectMember.employee_id == user.employee.id)
        else:
            query = query.filter(db.literal(False))
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept:
            query = query.filter(
                (Project.department_id == managed_dept.id) | 
                (Project.lead_id == (user.employee.id if user.employee else 0))
            )
        else:
            query = query.filter(Project.lead_id == (user.employee.id if user.employee else 0))

    if status_filter:
        query = query.filter_by(project_status=status_filter)

    projects = query.order_by(Project.id.desc()).all()
    return render_template('projects/index.html', projects=projects, selected_status=status_filter)


@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def create():
    user = get_current_user()
    role = get_user_role(user)
    form = ProjectForm()

    form.client_id.choices = [(0, '-- Internal / No Client --')] + [(c.id, c.company_name) for c in Client.active_query().all()]

    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        form.department_id.choices = [(managed_dept.id, managed_dept.name)] if managed_dept else [(0, '-- None --')]
        form.lead_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().filter_by(department_id=managed_dept.id).all()] if managed_dept else [(0, '-- None --')]
    else:
        form.department_id.choices = [(0, '-- None --')] + [(d.id, d.name) for d in Department.active_query().all()]
        form.lead_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]

    if form.validate_on_submit():
        if Project.query.filter_by(code=form.code.data.strip().upper()).first():
            flash('Project code already exists.', 'danger')
            return render_template('projects/create.html', form=form)

        client_val = form.client_id.data if form.client_id.data != 0 else None
        dept_val = form.department_id.data if form.department_id.data != 0 else None
        lead_val = form.lead_id.data if form.lead_id.data != 0 else None

        project = Project(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            client_id=client_val,
            department_id=dept_val,
            lead_id=lead_val,
            start_date=form.start_date.data,
            deadline=form.deadline.data,
            budget=form.budget.data,
            priority=form.priority.data,
            project_status=form.project_status.data,
            description=form.description.data.strip() if form.description.data else None,
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(project)
            db.session.commit()
            log_audit('CREATE', 'projects', project.id, None, {'name': project.name, 'code': project.code})
            flash(f'Project "{project.name}" launched.', 'success')
            return redirect(url_for('projects.view', project_id=project.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating project: {str(e)}', 'danger')

    return render_template('projects/create.html', form=form)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def edit(project_id):
    project = Project.get_active_or_404(project_id)
    user = get_current_user()
    role = get_user_role(user)

    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept and project.department_id != managed_dept.id and project.lead_id != (user.employee.id if user.employee else 0):
            flash('Access Denied: You cannot modify projects outside your department.', 'danger')
            return redirect(url_for('projects.index'))

    form = ProjectForm(obj=project)
    form.client_id.choices = [(0, '-- Internal / No Client --')] + [(c.id, c.company_name) for c in Client.active_query().all()]

    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        form.department_id.choices = [(managed_dept.id, managed_dept.name)] if managed_dept else [(0, '-- None --')]
        form.lead_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().filter_by(department_id=managed_dept.id).all()] if managed_dept else [(0, '-- None --')]
    else:
        form.department_id.choices = [(0, '-- None --')] + [(d.id, d.name) for d in Department.active_query().all()]
        form.lead_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]

    if request.method == 'GET':
        form.client_id.data = project.client_id or 0
        form.department_id.data = project.department_id or 0
        form.lead_id.data = project.lead_id or 0

    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        existing = Project.query.filter(Project.code == code, Project.id != project.id).first()
        if existing:
            flash('Project code already in use by another project.', 'danger')
            return render_template('projects/edit.html', form=form, project=project)

        old_val = {'name': project.name, 'code': project.code, 'status': project.project_status}

        project.name = form.name.data.strip()
        project.code = code
        project.client_id = form.client_id.data if form.client_id.data != 0 else None
        project.department_id = form.department_id.data if form.department_id.data != 0 else None
        project.lead_id = form.lead_id.data if form.lead_id.data != 0 else None
        project.start_date = form.start_date.data
        project.deadline = form.deadline.data
        project.budget = form.budget.data
        project.priority = form.priority.data
        project.project_status = form.project_status.data
        project.description = form.description.data.strip() if form.description.data else None
        project.updated_by = user.id

        try:
            db.session.commit()
            log_audit('UPDATE', 'projects', project.id, old_val, {'name': project.name, 'code': project.code, 'status': project.project_status})
            flash(f'Project "{project.name}" updated successfully.', 'success')
            return redirect(url_for('projects.view', project_id=project.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating project: {str(e)}', 'danger')

    return render_template('projects/edit.html', form=form, project=project)


@projects_bp.route('/<int:project_id>')
@login_required
def view(project_id):
    user = get_current_user()
    role = get_user_role(user)
    project = Project.get_active_or_404(project_id)

    # Scoping check
    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept and project.department_id != managed_dept.id and project.lead_id != (user.employee.id if user.employee else 0):
            flash('Access Denied: You cannot view projects outside your department.', 'danger')
            return redirect(url_for('projects.index'))
    elif role == 'employee':
        is_member = False
        if user.employee:
            is_member = any(m.employee_id == user.employee.id for m in project.members) or any(
                any(a.employee_id == user.employee.id for a in t.assignments) for t in project.tasks
            )
        if not is_member:
            flash('Access Denied: You are not assigned to this project.', 'danger')
            return redirect(url_for('projects.index'))

    all_employees = Employee.active_query().all()
    if role == 'dept_manager':
        managed_dept = get_managed_department(user)
        if managed_dept:
            all_employees = Employee.active_query().filter_by(department_id=managed_dept.id).all()

    return render_template('projects/view.html', project=project, all_employees=all_employees, user_role=role)


@projects_bp.route('/<int:project_id>/add-member', methods=['POST'])
@login_required
@manager_or_admin_required
def add_member(project_id):
    project = Project.get_active_or_404(project_id)
    emp_id = request.form.get('employee_id', type=int)
    role_name = request.form.get('project_role', 'Team Member').strip()
    user = get_current_user()

    if emp_id:
        existing = ProjectMember.active_query().filter_by(project_id=project.id, employee_id=emp_id).first()
        if not existing:
            member = ProjectMember(
                project_id=project.id,
                employee_id=emp_id,
                project_role=role_name,
                created_by=user.id,
                updated_by=user.id
            )
            try:
                db.session.add(member)
                db.session.commit()
                log_audit('CREATE', 'project_members', member.id, None, {'project_id': project.id, 'employee_id': emp_id})
                flash('Team member added to project.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding team member: {str(e)}', 'danger')

    return redirect(url_for('projects.view', project_id=project.id))


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@manager_or_admin_required
def delete(project_id):
    project = Project.get_active_or_404(project_id)
    user = get_current_user()

    old_val = {'id': project.id, 'name': project.name, 'code': project.code}
    try:
        project.soft_delete(user_id=user.id)
        db.session.commit()
        log_audit('DELETE', 'projects', project.id, old_val, {'is_deleted': True})
        flash(f'Project "{project.name}" moved to Recycle Bin.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting project: {str(e)}', 'danger')
    return redirect(url_for('projects.index'))
