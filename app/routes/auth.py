from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from app.extensions import db
from app.models.auth import User, LoginHistory, Role
from app.models.employee import Department
from app.forms.auth_forms import LoginForm, UserProfileForm, ChangePasswordForm
from app.services.audit_service import log_audit
from app.services.email_service import send_email_notification
from app.utils.decorators import login_required, get_current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/login/<string:dept_code>', methods=['GET', 'POST'])
def login(dept_code=None):
    if session.get('user_id'):
        return redirect(url_for('dashboard.index'))

    # Retrieve all primary departments for the portal switcher
    departments = Department.active_query().order_by(Department.id).all()

    # Determine targeted department or employee portal if specified in URL or query arg
    target_code = (dept_code or request.args.get('dept', '') or request.args.get('portal', '')).strip().upper()
    is_employee_portal = (target_code in ['EMP', 'EMPLOYEE'])
    current_dept = None
    if target_code and not is_employee_portal:
        current_dept = Department.active_query().filter(Department.code == target_code).first()

    form = LoginForm()
    if form.validate_on_submit():
        user_identifier = form.username_or_email.data.strip()
        user = User.active_query().filter(
            (User.username == user_identifier) | (User.email == user_identifier)
        ).first()

        ip_addr = request.remote_addr or '127.0.0.1'
        u_agent = request.headers.get('User-Agent', '')[:255]

        if user and user.check_password(form.password.data):
            if user.status != 'Active':
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('auth/login.html', form=form, current_dept=current_dept, is_employee_portal=is_employee_portal, departments=departments)

            # Department portal access validation:
            # If logging in via a specific department portal, verify department affiliation (unless Super Admin)
            is_super_admin = user.is_admin or any(ur.role.name == 'super_admin' for ur in user.user_roles if ur.role and not ur.is_deleted)
            if current_dept and not is_super_admin:
                user_dept_id = user.employee.department_id if user.employee else None
                if user_dept_id != current_dept.id:
                    user_dept_name = user.employee.department.name if user.employee and user.employee.department else 'another division'
                    flash(f"Department Access Restricted: Your credentials are registered under '{user_dept_name}'. Please sign in through the {user_dept_name} Portal, Employee Login, or Central Workplace Login.", 'warning')
                    return render_template('auth/login.html', form=form, current_dept=current_dept, is_employee_portal=is_employee_portal, departments=departments)

            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['email'] = user.email
            session['is_admin'] = user.is_admin
            session['roles'] = [ur.role.name for ur in user.user_roles if ur.role and not ur.is_deleted]
            session['primary_role'] = user.primary_role
            session['department_id'] = user.employee.department_id if user.employee else None
            session['department_name'] = user.employee.department.name if user.employee and user.employee.department else ('All Corporate Departments' if is_super_admin else 'General')
            session['department_code'] = user.employee.department.code if user.employee and user.employee.department else ('ALL' if is_super_admin else 'GEN')
            session.permanent = form.remember_me.data

            # Record Login History
            history = LoginHistory(
                user_id=user.id,
                ip_address=ip_addr,
                user_agent=u_agent,
                status='Success',
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(history)
            db.session.commit()

            if is_employee_portal:
                portal_note = " via Employee Portal"
            elif current_dept:
                portal_note = f" via {current_dept.name} Portal"
            else:
                portal_note = ""

            portal_code = 'EMPLOYEE' if is_employee_portal else (current_dept.code if current_dept else 'CENTRAL')
            log_audit('LOGIN', 'users', user.id, None, {'username': user.username, 'portal': portal_code}, user.id)

            flash(f'Welcome back, {user.first_name}! Signed in{portal_note}.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            # Record failed login
            history = LoginHistory(
                user_id=user.id if user else None,
                ip_address=ip_addr,
                user_agent=u_agent,
                status='Failed',
                failure_reason='Invalid credentials provided'
            )
            db.session.add(history)
            db.session.commit()

            flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html', form=form, current_dept=current_dept, is_employee_portal=is_employee_portal, departments=departments)


@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_audit('LOGOUT', 'users', user_id, None, None, user_id)
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    profile_form = UserProfileForm(obj=user)
    password_form = ChangePasswordForm()

    if 'update_profile' in request.form and profile_form.validate_on_submit():
        old_val = {'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email, 'phone': user.phone}
        user.first_name = profile_form.first_name.data.strip()
        user.last_name = profile_form.last_name.data.strip()
        user.email = profile_form.email.data.strip()
        user.phone = profile_form.phone.data.strip() if profile_form.phone.data else None
        user.updated_by = user.id
        db.session.commit()

        session['full_name'] = user.full_name
        session['email'] = user.email
        log_audit('UPDATE', 'users', user.id, old_val, {'first_name': user.first_name, 'last_name': user.last_name})
        flash('Profile details updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    if 'change_password' in request.form and password_form.validate_on_submit():
        if not user.check_password(password_form.current_password.data):
            flash('Current password entered is incorrect.', 'danger')
        else:
            user.set_password(password_form.new_password.data)
            user.updated_by = user.id
            db.session.commit()
            log_audit('UPDATE', 'users', user.id, None, {'action': 'password_change'})
            flash('Password changed successfully.', 'success')
            return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', user=user, profile_form=profile_form, password_form=password_form)


def get_serializer():
    secret_key = current_app.config.get('SECRET_KEY', 'default-dev-secret-key-1234')
    return URLSafeTimedSerializer(secret_key)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.active_query().filter_by(email=email).first()

        if user:
            s = get_serializer()
            token = s.dumps(user.email, salt='password-reset-salt')
            reset_url = url_for('auth.reset_password', token=token, _external=True)

            subject = "OMS Password Reset Request"
            body = (
                f"Hello {user.first_name},\n\n"
                f"A password reset request was initiated for your Office Management System account.\n\n"
                f"To reset your password, visit the link below:\n{reset_url}\n\n"
                f"This link expires in 30 minutes. If you did not make this request, you can safely ignore this email."
            )
            send_email_notification(to_email=user.email, subject=subject, body=body)

        flash('If your email is registered in our system, password reset instructions have been dispatched.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = get_serializer()
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=1800)
    except (SignatureExpired, BadTimeSignature):
        flash('The password reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = User.active_query().filter_by(email=email).first_or_404()

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            user.set_password(new_password)
            user.updated_by = user.id
            db.session.commit()
            log_audit('UPDATE', 'users', user.id, None, {'action': 'password_reset_via_token'})
            flash('Your password has been successfully reset. You may now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token, user=user)


@auth_bp.route('/activate/<token>', methods=['GET', 'POST'], endpoint='activate_account')
def activate_account(token):
    s = get_serializer()
    try:
        email = s.loads(token, salt='account-activation-salt', max_age=604800)
    except (SignatureExpired, BadTimeSignature):
        flash('The account activation link is invalid or has expired. Please contact HR or request a password reset.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.active_query().filter_by(email=email).first_or_404()

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            user.set_password(new_password)
            user.status = 'Active'
            user.updated_by = user.id
            db.session.commit()
            log_audit('UPDATE', 'users', user.id, None, {'action': 'account_activation_completed'})
            flash('Your account has been successfully activated! You may now sign in with your credentials.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/activate.html', token=token, user=user)
