import os
import uuid
from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, send_from_directory
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.communication import Announcement, Notification, Message, MessageRecipient
from app.models.employee import Department
from app.models.auth import User
from app.forms.communication_forms import AnnouncementForm, DirectMessageForm
from app.services.audit_service import log_audit
from app.services.notification_service import notify_message_received
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


@communication_bp.route('/notifications/<int:notif_id>/click')
@login_required
def click_notification(notif_id):
    notif = Notification.get_active_or_404(notif_id)
    user = get_current_user()
    if notif.user_id != user.id:
        abort(403)

    notif.is_read = True
    notif.read_at = utc_now()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    if notif.action_url:
        return redirect(notif.action_url)
    return redirect(url_for('communication.notifications'))


@communication_bp.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    user = get_current_user()
    all_users = User.active_query().filter(User.id != user.id).order_by(User.first_name).all()
    form = DirectMessageForm()

    # Formatted categorized choices
    form.recipient_id.choices = [
        (u.id, f"{u.full_name} — {u.primary_role}{' (' + u.employee.department.name + ')' if u.employee and u.employee.department else ''}")
        for u in all_users
    ]

    if form.validate_on_submit():
        attachment_filename = None
        if form.attachment.data:
            file = form.attachment.data
            sec_filename = secure_filename(file.filename)
            if sec_filename:
                ext = sec_filename.rsplit('.', 1)[-1].lower() if '.' in sec_filename else 'bin'
                attachment_filename = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
                upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'messages')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, attachment_filename))

        msg = Message(
            sender_id=user.id,
            subject=form.subject.data.strip(),
            body=form.body.data.strip(),
            attachment_path=attachment_filename,
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

            recipient_user = db.session.get(User, form.recipient_id.data)
            if recipient_user:
                notify_message_received(sender=user, recipient_user=recipient_user, message=msg)

            flash('Message dispatched successfully.', 'success')
            return redirect(url_for('communication.messages'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to dispatch message: {str(e)}', 'danger')
    elif request.method == 'POST':
        for field, errs in form.errors.items():
            for e in errs:
                flash(f"{field}: {e}", 'danger')

    inbox_items = MessageRecipient.active_query().filter_by(recipient_id=user.id).order_by(MessageRecipient.id.desc()).all()
    sent_items = Message.active_query().filter_by(sender_id=user.id).order_by(Message.id.desc()).all()
    unread_inbox_count = sum(1 for item in inbox_items if not item.is_read)

    return render_template(
        'communication/messages.html',
        inbox_items=inbox_items,
        sent_items=sent_items,
        all_users=all_users,
        unread_inbox_count=unread_inbox_count,
        form=form
    )


@communication_bp.route('/messages/<int:msg_id>')
@login_required
def view_message(msg_id):
    user = get_current_user()
    msg = Message.get_active_or_404(msg_id)

    # Privacy check: current user must be sender or recipient
    is_sender = (msg.sender_id == user.id)
    recip_entry = MessageRecipient.active_query().filter_by(message_id=msg.id, recipient_id=user.id).first()

    if not is_sender and not recip_entry:
        abort(403)

    if recip_entry and not recip_entry.is_read:
        recip_entry.is_read = True
        recip_entry.read_at = utc_now()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    return render_template('communication/message_detail.html', message=msg, is_sender=is_sender, recip_entry=recip_entry)


@communication_bp.route('/messages/<int:msg_id>/attachment')
@login_required
def download_message_attachment(msg_id):
    user = get_current_user()
    msg = Message.get_active_or_404(msg_id)

    is_sender = (msg.sender_id == user.id)
    recip_entry = MessageRecipient.active_query().filter_by(message_id=msg.id, recipient_id=user.id).first()

    if not is_sender and not recip_entry:
        abort(403)

    if not msg.attachment_path:
        abort(404)

    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'messages')
    return send_from_directory(upload_dir, msg.attachment_path, as_attachment=True)
