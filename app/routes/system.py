from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.system import AuditLog, SystemSetting
from app.models.auth import User, Role, UserRole
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, admin_required, get_current_user

system_bp = Blueprint('system', __name__, url_prefix='/system')

@system_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    table_filter = request.args.get('table', '')

    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)
    if table_filter:
        query = query.filter_by(table_name=table_filter)

    pagination = query.order_by(AuditLog.id.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'system/audit_logs.html',
        pagination=pagination,
        logs=pagination.items,
        selected_action=action_filter,
        selected_table=table_filter
    )


@system_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        user = get_current_user()
        for key, value in request.form.items():
            if key != 'csrf_token':
                setting = SystemSetting.active_query().filter_by(setting_key=key).first()
                if setting:
                    setting.setting_value = value.strip()
                    setting.updated_by = user.id
                else:
                    setting = SystemSetting(
                        setting_key=key,
                        setting_value=value.strip(),
                        category='General',
                        created_by=user.id,
                        updated_by=user.id
                    )
                    db.session.add(setting)

        db.session.commit()
        log_audit('UPDATE', 'system_settings', 0, None, {'action': 'settings_saved'})
        flash('System configuration updated successfully.', 'success')
        return redirect(url_for('system.settings'))

    all_settings = {s.setting_key: s.setting_value for s in SystemSetting.active_query().all()}
    return render_template('system/settings.html', settings=all_settings)


@system_bp.route('/users')
@login_required
@admin_required
def users():
    users_list = User.active_query().order_by(User.id.desc()).all()
    roles_list = Role.active_query().all()
    return render_template('system/users.html', users=users_list, roles=roles_list)


@system_bp.route('/users/<int:user_id>/assign-role', methods=['POST'])
@login_required
@admin_required
def assign_role(user_id):
    target_user = User.get_active_or_404(user_id)
    role_id = request.form.get('role_id', type=int)
    current_admin = get_current_user()

    if role_id:
        # Check if already assigned
        existing = UserRole.active_query().filter_by(user_id=target_user.id, role_id=role_id).first()
        if not existing:
            ur = UserRole(user_id=target_user.id, role_id=role_id, created_by=current_admin.id, updated_by=current_admin.id)
            db.session.add(ur)
            db.session.commit()
            log_audit('CREATE', 'user_roles', ur.id, None, {'user_id': target_user.id, 'role_id': role_id})
            flash('Role assigned successfully.', 'success')

    return redirect(url_for('system.users'))


@system_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    current_admin = get_current_user()
    if current_admin.id == user_id:
        flash('You cannot deactivate your own administrative account.', 'danger')
        return redirect(url_for('system.users'))

    target_user = User.get_active_or_404(user_id)
    old_status = target_user.status
    target_user.status = 'Deactive' if old_status == 'Active' else 'Active'
    target_user.updated_by = current_admin.id

    try:
        db.session.commit()
        log_audit('UPDATE', 'users', target_user.id, {'status': old_status}, {'status': target_user.status})
        flash(f'Account status for {target_user.username} toggled to {target_user.status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'danger')

    return redirect(url_for('system.users'))


@system_bp.route('/users/<int:user_id>/remove-role/<int:role_id>', methods=['POST'])
@login_required
@admin_required
def remove_role(user_id, role_id):
    current_admin = get_current_user()
    ur = UserRole.active_query().filter_by(user_id=user_id, role_id=role_id).first_or_404()
    old_val = {'user_id': user_id, 'role_id': role_id}
    try:
        ur.soft_delete(user_id=current_admin.id)
        db.session.commit()
        log_audit('DELETE', 'user_roles', ur.id, old_val, {'is_deleted': True})
        flash('Role revoked from user.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error revoking role: {str(e)}', 'danger')

    return redirect(url_for('system.users'))
