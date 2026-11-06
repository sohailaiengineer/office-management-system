from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.communication import Announcement, Notification, Message, MessageRecipient
from app.models.employee import Department
from app.models.auth import User
from app.forms.communication_forms import AnnouncementForm, DirectMessageForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, hr_or_admin_required, get_current_user
from app.utils import utc_now

communication_bp = Blueprint('communication', __name__, url_prefix='/communication')

@communication_bp.route('/announcements')
@login_required
def announcements():
    announcements_list = Announcement.active_query().order_by(
        Announcement.is_pinned.desc(), Announcement.publish_date.desc()
    ).all()
    departments = Department.active_query().all()
    form = AnnouncementForm()
    form.department_id.choices = [(0, 'All / Company-Wide')] + [(d.id, d.name) for d in departments]
    return render_template('communication/announcements.html', announcements=announcements_list, departments=departments, form=form)


@communication_bp.route('/announcements/create', methods=['POST'])
@login_required
@hr_or_admin_required
def create_announcement():
    departments = Department.active_query().all()
    form = AnnouncementForm()
    form.department_id.choices = [(0, 'All / Company-Wide')] + [(d.id, d.name) for d in departments]
    user = get_current_user()

    if form.validate_on_submit():
        dept_id = form.department_id.data if form.department_id.data != 0 else None
        ann = Announcement(
            title=form.title.data.strip(),
            content=form.content.data.strip(),
            target_audience=form.target_audience.data,
            department_id=dept_id,
            publish_date=date.today(),
            is_pinned=form.is_pinned.data,
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(ann)
            db.session.commit()
            log_audit('CREATE', 'announcements', ann.id, None, {'title': ann.title})
            flash('Announcement broadcasted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to broadcast announcement: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"{field}: {err}", 'danger')

    return redirect(url_for('communication.announcements'))


@communication_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete_announcement(ann_id):
    ann = Announcement.get_active_or_404(ann_id)
    user = get_current_user()

    old_val = {'id': ann.id, 'title': ann.title}
    try:
        ann.soft_delete(user_id=user.id)
        db.session.commit()
        log_audit('DELETE', 'announcements', ann.id, old_val, {'is_deleted': True})
        flash(f'Announcement "{ann.title}" removed.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to remove announcement: {str(e)}', 'danger')
    return redirect(url_for('communication.announcements'))


@communication_bp.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    notifications_list = Notification.active_query().filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    return render_template('communication/notifications.html', notifications=notifications_list)


@communication_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.get_active_or_404(notif_id)
    notif.is_read = True
    notif.read_at = utc_now()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(url_for('communication.notifications'))


@communication_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    unread_notifs = Notification.active_query().filter_by(user_id=user.id, is_read=False).all()
    for n in unread_notifs:
        n.is_read = True
        n.read_at = utc_now()
    try:
        db.session.commit()
        flash('All notifications marked as read.', 'success')
    except Exception:
        db.session.rollback()
    return redirect(url_for('communication.notifications'))


@communication_bp.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    user = get_current_user()
    all_users = User.active_query().filter(User.id != user.id).all()
    form = DirectMessageForm()
    form.recipient_id.choices = [(u.id, f"{u.full_name} (@{u.username})") for u in all_users]

    if form.validate_on_submit():
        msg = Message(
            sender_id=user.id,
            subject=form.subject.data.strip(),
            body=form.body.data.strip(),
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(msg)
            db.session.flush()

            recip = MessageRecipient(
                message_id=msg.id,
                recipient_id=form.recipient_id.data,
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(recip)
            db.session.commit()
            flash('Message dispatched successfully.', 'success')
            return redirect(url_for('communication.messages'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to dispatch message: {str(e)}', 'danger')

    inbox_items = MessageRecipient.active_query().filter_by(recipient_id=user.id).order_by(MessageRecipient.id.desc()).all()
    sent_items = Message.active_query().filter_by(sender_id=user.id).order_by(Message.id.desc()).all()

    return render_template(
        'communication/messages.html',
        inbox_items=inbox_items,
        sent_items=sent_items,
        all_users=all_users,
        form=form
    )
