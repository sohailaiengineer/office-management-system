from functools import wraps
from flask import session, redirect, url_for, flash, abort, request
from app.extensions import db
from app.models.auth import User

def get_current_user():
    """Retrieves current logged-in User instance from session user_id."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)

def get_user_role(user):
    """Returns normalized primary role code for current user."""
    if not user:
        return 'anonymous'
    if user.is_admin:
        return 'super_admin'
    user_roles = [ur.role.name.lower() for ur in user.user_roles if ur.role and not ur.is_deleted]
    if 'super_admin' in user_roles:
        return 'super_admin'
    elif 'hr_manager' in user_roles:
        return 'hr_manager'
    elif 'dept_manager' in user_roles:
        return 'dept_manager'
    elif 'employee' in user_roles:
        return 'employee'
    return 'employee'

def get_managed_department(user):
    """Returns the Department instance managed by the current user, or None."""
    if not user or not user.employee:
        return None
    from app.models.employee import Department
    # Check explicit manager_id link
    dept = Department.active_query().filter_by(manager_id=user.employee.id).first()
    if dept:
        return dept
    # Fallback to department where user is assigned if they hold dept_manager role
    user_roles = [ur.role.name.lower() for ur in user.user_roles if ur.role and not ur.is_deleted]
    if 'dept_manager' in user_roles and user.employee.department_id:
        return Department.active_query().filter_by(id=user.employee.department_id).first()
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """
    RBAC decorator that validates whether the logged-in user possesses
    at least one of the specified roles (or is Super Admin).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            user = get_current_user()
            if not user:
                session.clear()
                flash('Session invalid. Please log in again.', 'danger')
                return redirect(url_for('auth.login'))

            # Super admin has unconditional access
            user_roles = [ur.role.name.lower() for ur in user.user_roles if ur.role and not ur.is_deleted]
            if 'super_admin' in user_roles or user.is_admin:
                return f(*args, **kwargs)

            # Check if user has any of the permitted roles
            target_roles = [r.lower() for r in roles]
            if not any(r in user_roles for r in target_roles):
                flash('Access Denied: You do not possess the required permissions for this action.', 'danger')
                return redirect(url_for('dashboard.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required('super_admin')(f)

def hr_or_admin_required(f):
    return role_required('super_admin', 'hr_manager')(f)

def manager_or_admin_required(f):
    return role_required('super_admin', 'hr_manager', 'dept_manager')(f)

def dept_manager_or_admin_required(f):
    return role_required('super_admin', 'dept_manager')(f)
