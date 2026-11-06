from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from app.extensions import db
from app.models.project import Task, Project, TaskAssignment, TaskComment
from app.models.employee import Employee
from app.forms.project_forms import TaskForm, TaskCommentForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, get_current_user, get_user_role, get_managed_department

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

@tasks_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    managed_dept = get_managed_department(user)

    priority_filter = request.args.get('priority', '')
    status_filter = request.args.get('status', '')
    view_mode = request.args.get('view', 'all')

    query = Task.active_query()

    if role == 'employee':
        # Employee sees ONLY tasks assigned to them
        if user.employee:
            query = query.filter(Task.assignments.any(TaskAssignment.employee_id == user.employee.id))
        else:
            query = query.filter(Task.id == -1)
    elif role == 'dept_manager':
        # Department Manager sees tasks for department projects OR tasks assigned to department employees
        if managed_dept:
            dept_emp_ids = [e.id for e in Employee.query.filter_by(department_id=managed_dept.id, is_deleted=False).all()]
            dept_project_ids = [p.id for p in Project.query.filter_by(department_id=managed_dept.id, is_deleted=False).all()]
            query = query.filter(
                db.or_(
                    Task.project_id.in_(dept_project_ids),
                    Task.assignments.any(TaskAssignment.employee_id.in_(dept_emp_ids))
                )
            )
            if view_mode == 'my' and user.employee:
                query = query.filter(Task.assignments.any(TaskAssignment.employee_id == user.employee.id))
        else:
            query = query.filter(Task.id == -1)
    else:
        # Super Admin / HR Manager
        if view_mode == 'my' and user.employee:
            query = query.filter(Task.assignments.any(TaskAssignment.employee_id == user.employee.id))

    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    if status_filter:
        if status_filter in ['Pending', 'To-Do']:
            query = query.filter(Task.task_status.in_(['Pending', 'To-Do']))
        elif status_filter in ['In-Progress', 'In Progress']:
            query = query.filter(Task.task_status.in_(['In-Progress', 'In Progress']))
        elif status_filter in ['Review', 'Under Review']:
            query = query.filter(Task.task_status.in_(['Review', 'Under Review']))
        else:
            query = query.filter(Task.task_status == status_filter)

    tasks_list = query.order_by(Task.due_date.asc(), Task.id.desc()).all()

    # Group into Kanban columns
    todo_tasks = [t for t in tasks_list if t.task_status in ['To-Do', 'Pending']]
    in_progress_tasks = [t for t in tasks_list if t.task_status in ['In-Progress', 'In Progress']]
    review_tasks = [t for t in tasks_list if t.task_status in ['Review', 'Under Review']]
    completed_tasks = [t for t in tasks_list if t.task_status == 'Completed']

    return render_template(
        'tasks/index.html',
        tasks=tasks_list,
        todo_tasks=todo_tasks,
        in_progress_tasks=in_progress_tasks,
        review_tasks=review_tasks,
        completed_tasks=completed_tasks,
        selected_priority=priority_filter,
        selected_status=status_filter,
        view_mode=view_mode
    )


@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    user = get_current_user()
    role = get_user_role(user)
    managed_dept = get_managed_department(user)

    # Employees cannot assign tasks to others
    if role == 'employee':
        flash('Access Denied: Regular employees are not authorized to create or assign tasks.', 'warning')
        return redirect(url_for('tasks.index'))

    form = TaskForm()

    if role == 'dept_manager':
        if not managed_dept:
            flash('No managed department assigned. Cannot create tasks.', 'danger')
            return redirect(url_for('tasks.index'))
        dept_projects = Project.query.filter_by(department_id=managed_dept.id, is_deleted=False).all()
        dept_employees = Employee.query.filter_by(department_id=managed_dept.id, is_deleted=False).all()
        form.project_id.choices = [(p.id, f"{p.code} - {p.name}") for p in dept_projects]
        form.assigned_employee_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in dept_employees]
    else:
        # Admin / HR can assign tasks across any department
        form.project_id.choices = [(p.id, f"{p.code} - {p.name}") for p in Project.active_query().all()]
        form.assigned_employee_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]

    if not form.project_id.choices:
        flash('No projects available to create tasks for.', 'warning')
        return redirect(url_for('tasks.index'))

    if form.validate_on_submit():
        project = Project.get_active_or_404(form.project_id.data)
        if role == 'dept_manager' and project.department_id != managed_dept.id:
            flash('Unauthorized: You can only create tasks for projects belonging to your department.', 'danger')
            return redirect(url_for('tasks.index'))

        emp_creator_id = user.employee.id if user.employee else None

        task = Task(
            project_id=form.project_id.data,
            title=form.title.data.strip(),
            priority=form.priority.data,
            task_status=form.task_status.data,
            estimated_hours=form.estimated_hours.data,
            start_date=form.start_date.data or date.today(),
            due_date=form.due_date.data,
            description=form.description.data.strip() if form.description.data else None,
            created_by_emp_id=emp_creator_id,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(task)
        db.session.flush()

        assigned_emp_id = form.assigned_employee_id.data
        if assigned_emp_id and assigned_emp_id != 0:
            if role == 'dept_manager':
                target_emp = Employee.get_active_or_404(assigned_emp_id)
                if target_emp.department_id != managed_dept.id:
                    db.session.rollback()
                    flash('Unauthorized: Department Managers can only assign tasks to employees in their own department.', 'danger')
                    return redirect(url_for('tasks.create'))

            assignment = TaskAssignment(
                task_id=task.id,
                employee_id=assigned_emp_id,
                assigned_date=date.today(),
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(assignment)

        db.session.commit()
        log_audit('CREATE', 'tasks', task.id, None, {'title': task.title, 'project_id': task.project_id})
        flash(f'Task "{task.title}" created successfully.', 'success')
        return redirect(url_for('tasks.index'))

    return render_template('tasks/create.html', form=form)


@tasks_bp.route('/<int:task_id>', methods=['GET', 'POST'])
@login_required
def view(task_id):
    task = Task.get_active_or_404(task_id)
    user = get_current_user()
    role = get_user_role(user)
    managed_dept = get_managed_department(user)

    # Scoping check
    if role == 'employee':
        assigned_ids = [a.employee_id for a in task.assignments]
        if not user.employee or user.employee.id not in assigned_ids:
            flash('Access Denied: You are not assigned to this task.', 'danger')
            return redirect(url_for('tasks.index'))
    elif role == 'dept_manager':
        dept_id = task.project.department_id if task.project else None
        assigned_emp_dept_ids = [a.employee.department_id for a in task.assignments if a.employee]
        if not managed_dept or (dept_id != managed_dept.id and managed_dept.id not in assigned_emp_dept_ids):
            flash('Access Denied: This task does not belong to your department.', 'danger')
            return redirect(url_for('tasks.index'))

    comment_form = TaskCommentForm()
    if comment_form.validate_on_submit():
        comment = TaskComment(
            task_id=task.id,
            user_id=user.id,
            comment=comment_form.comment.data.strip(),
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(comment)
        db.session.commit()
        flash('Progress note / comment posted.', 'success')
        return redirect(url_for('tasks.view', task_id=task.id))

    return render_template('tasks/view.html', task=task, comment_form=comment_form)


@tasks_bp.route('/<int:task_id>/update-status', methods=['POST'])
@login_required
def update_status(task_id):
    task = Task.get_active_or_404(task_id)
    user = get_current_user()
    role = get_user_role(user)
    managed_dept = get_managed_department(user)

    # Permission verification
    if role == 'employee':
        assigned_ids = [a.employee_id for a in task.assignments]
        if not user.employee or user.employee.id not in assigned_ids:
            flash('Access Denied: You cannot update tasks not assigned to you.', 'danger')
            return redirect(url_for('tasks.index'))
    elif role == 'dept_manager':
        dept_id = task.project.department_id if task.project else None
        assigned_emp_dept_ids = [a.employee.department_id for a in task.assignments if a.employee]
        if not managed_dept or (dept_id != managed_dept.id and managed_dept.id not in assigned_emp_dept_ids):
            flash('Access Denied: This task does not belong to your department.', 'danger')
            return redirect(url_for('tasks.index'))

    new_status = request.form.get('task_status')
    completion_pct = request.form.get('completion_percentage')
    progress_note = request.form.get('progress_note', '').strip()

    valid_statuses = ['To-Do', 'Pending', 'In-Progress', 'In Progress', 'Review', 'Under Review', 'Completed']
    if new_status in valid_statuses:
        old_status = task.task_status
        task.task_status = new_status

        if completion_pct is not None and completion_pct.strip().isdigit():
            task.completion_percentage = max(0, min(100, int(completion_pct.strip())))
        elif new_status == 'Completed':
            task.completion_percentage = 100
        elif new_status in ['In-Progress', 'In Progress'] and task.completion_percentage == 0:
            task.completion_percentage = 25

        task.updated_by = user.id

        if progress_note:
            comment = TaskComment(
                task_id=task.id,
                user_id=user.id,
                comment=f"[Status Update -> {new_status} ({task.completion_percentage}%)]: {progress_note}",
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(comment)

        db.session.commit()
        log_audit('UPDATE', 'tasks', task.id, {'status': old_status}, {'status': new_status, 'completion': task.completion_percentage})
        flash(f'Task status updated to "{new_status}" ({task.completion_percentage}%).', 'success')
    else:
        flash('Invalid status provided.', 'warning')

    return redirect(url_for('tasks.view', task_id=task.id))


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    task = Task.get_active_or_404(task_id)
    user = get_current_user()
    role = get_user_role(user)
    managed_dept = get_managed_department(user)

    if role == 'employee':
        flash('Employees cannot edit task parameters. Please use status update and progress notes.', 'warning')
        return redirect(url_for('tasks.view', task_id=task.id))

    if role == 'dept_manager':
        dept_id = task.project.department_id if task.project else None
        if not managed_dept or dept_id != managed_dept.id:
            flash('Access Denied: You can only edit tasks belonging to your department.', 'danger')
            return redirect(url_for('tasks.index'))

    form = TaskForm(obj=task)
    if role == 'dept_manager':
        dept_projects = Project.query.filter_by(department_id=managed_dept.id, is_deleted=False).all()
        dept_employees = Employee.query.filter_by(department_id=managed_dept.id, is_deleted=False).all()
        form.project_id.choices = [(p.id, f"{p.code} - {p.name}") for p in dept_projects]
        form.assigned_employee_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in dept_employees]
    else:
        form.project_id.choices = [(p.id, f"{p.code} - {p.name}") for p in Project.active_query().all()]
        form.assigned_employee_id.choices = [(0, '-- Unassigned --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]

    active_assignment = task.assignments[0] if task.assignments else None

    if request.method == 'GET':
        form.assigned_employee_id.data = active_assignment.employee_id if active_assignment else 0

    if form.validate_on_submit():
        if role == 'dept_manager':
            proj = Project.get_active_or_404(form.project_id.data)
            if proj.department_id != managed_dept.id:
                flash('Cannot assign task to a project outside your department.', 'danger')
                return redirect(url_for('tasks.view', task_id=task.id))
            if form.assigned_employee_id.data and form.assigned_employee_id.data != 0:
                target_emp = Employee.get_active_or_404(form.assigned_employee_id.data)
                if target_emp.department_id != managed_dept.id:
                    flash('Cannot assign task to an employee outside your department.', 'danger')
                    return redirect(url_for('tasks.view', task_id=task.id))

        old_val = {'title': task.title, 'status': task.task_status, 'priority': task.priority}
        task.project_id = form.project_id.data
        task.title = form.title.data.strip()
        task.priority = form.priority.data
        task.task_status = form.task_status.data
        task.estimated_hours = form.estimated_hours.data
        task.start_date = form.start_date.data
        task.due_date = form.due_date.data
        task.description = form.description.data.strip() if form.description.data else None
        task.updated_by = user.id

        if form.assigned_employee_id.data and form.assigned_employee_id.data != 0:
            if active_assignment:
                active_assignment.employee_id = form.assigned_employee_id.data
                active_assignment.updated_by = user.id
            else:
                assignment = TaskAssignment(
                    task_id=task.id,
                    employee_id=form.assigned_employee_id.data,
                    assigned_date=date.today(),
                    created_by=user.id,
                    updated_by=user.id
                )
                db.session.add(assignment)

        try:
            db.session.commit()
            log_audit('UPDATE', 'tasks', task.id, old_val, {'title': task.title, 'status': task.task_status, 'priority': task.priority})
            flash(f'Task "{task.title}" updated successfully.', 'success')
            return redirect(url_for('tasks.view', task_id=task.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating task: {str(e)}', 'danger')

    return render_template('tasks/edit.html', form=form, task=task)


@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete(task_id):
    user = get_current_user()
    role = get_user_role(user)
    managed_dept = get_managed_department(user)

    if role not in ['super_admin', 'dept_manager']:
        flash('Unauthorized to delete tasks.', 'danger')
        return redirect(url_for('tasks.index'))

    task = Task.get_active_or_404(task_id)
    if role == 'dept_manager':
        dept_id = task.project.department_id if task.project else None
        if not managed_dept or dept_id != managed_dept.id:
            flash('Unauthorized: You can only delete tasks for projects in your department.', 'danger')
            return redirect(url_for('tasks.index'))

    old_val = {'id': task.id, 'title': task.title}
    task.soft_delete(user_id=user.id)
    db.session.commit()

    log_audit('DELETE', 'tasks', task.id, old_val, {'is_deleted': True})
    flash(f'Task "{task.title}" moved to Recycle Bin.', 'warning')
    return redirect(url_for('tasks.index'))
