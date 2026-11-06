from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.extensions import db
from app.models.auth import User, LoginHistory, Role
from app.forms.auth_forms import LoginForm, UserProfileForm, ChangePasswordForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, get_current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard.index'))

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
                return render_template('auth/login.html', form=form)

            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['email'] = user.email
            session['is_admin'] = user.is_admin
            session['roles'] = [ur.role.name for ur in user.user_roles if ur.role and not ur.is_deleted]
            session['primary_role'] = user.primary_role
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

            log_audit('LOGIN', 'users', user.id, None, {'username': user.username}, user.id)

            flash(f'Welcome back, {user.first_name}!', 'success')
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

    return render_template('auth/login.html', form=form)


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
