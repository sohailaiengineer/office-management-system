import os
from flask import Flask, redirect, url_for, session, render_template
from app.extensions import db, csrf
from app.models.auth import User
from app.models.leave import LeaveRequest
from app.routes import all_blueprints
from config import config_by_name

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register all modular blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    # Root route redirect
    @app.route('/')
    def root():
        if session.get('user_id'):
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    # Global context processors for templates
    @app.context_processor
    def inject_global_data():
        current_user = None
        user_role = 'anonymous'
        managed_department = None
        unread_notifications_count = 0
        unread_messages_count = 0
        pending_leaves_count = 0

        user_id = session.get('user_id')
        if user_id:
            current_user = db.session.get(User, user_id)
            if current_user:
                from app.utils.decorators import get_user_role, get_managed_department
                from app.models.communication import Notification, MessageRecipient
                user_role = get_user_role(current_user)
                managed_department = get_managed_department(current_user)
                unread_notifications_count = Notification.active_query().filter_by(
                    user_id=current_user.id, is_read=False
                ).count()
                unread_messages_count = MessageRecipient.active_query().filter_by(
                    recipient_id=current_user.id, is_read=False
                ).count()

                if user_role in ['super_admin', 'hr_manager']:
                    pending_leaves_count = LeaveRequest.active_query().filter_by(approval_status='Pending').count()
                elif user_role == 'dept_manager' and managed_department:
                    dept_emp_ids = [e.id for e in managed_department.employees if not e.is_deleted]
                    if dept_emp_ids:
                        pending_leaves_count = LeaveRequest.active_query().filter(
                            LeaveRequest.employee_id.in_(dept_emp_ids),
                            LeaveRequest.approval_status == 'Pending'
                        ).count()

        return {
            'current_user': current_user,
            'user_role': user_role,
            'managed_department': managed_department,
            'unread_notifications_count': unread_notifications_count,
            'unread_messages_count': unread_messages_count,
            'pending_leaves_count': pending_leaves_count,
            'app_name': 'OMS Enterprise',
            'app_version': '2.0.0'
        }

    # Custom Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
