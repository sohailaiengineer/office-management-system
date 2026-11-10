import logging
from app.extensions import db
from app.models.communication import Notification
from app.models.auth import User, Role, UserRole
from app.models.employee import Department, Employee
from app.utils import utc_now

logger = logging.getLogger(__name__)

def create_notification(user_id, title, message, link=None, notification_type='Info'):
    """
    Creates and commits a single notification for a specific user.
    Never crashes the calling function if an error occurs.
    """
    if not user_id:
        return None
    try:
        notif = Notification(
            user_id=user_id,
            title=title.strip()[:150],
            message=message.strip(),
            link=link[:255] if link else None,
            notification_type=notification_type,
            is_read=False,
            created_by=user_id,
            updated_by=user_id
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Failed to create notification for user {user_id}: {str(e)}")
        return None


def notify_users(user_ids, title, message, link=None, notification_type='Info'):
    """
    Creates notifications for multiple distinct user IDs safely.
    """
    unique_ids = set(uid for uid in user_ids if uid)
    created = []
    for uid in unique_ids:
        n = create_notification(uid, title, message, link, notification_type)
        if n:
            created.append(n)
    return created


def get_admin_and_hr_user_ids():
    """
    Returns list of user IDs for Super Admins and HR Managers.
    """
    admin_users = User.active_query().filter(
        (User.is_admin == True) | 
        (User.user_roles.any(UserRole.role.has(Role.name.in_(['super_admin', 'hr_manager']))))
    ).all()
    return [u.id for u in admin_users]


def notify_leave_submitted(leave_request):
    """
    Notifies Super Admins, HR Managers, and the relevant Department Manager
    when a new leave request is submitted.
    """
    emp = leave_request.employee
    emp_name = emp.full_name if emp else "An employee"
    dept_name = emp.department.name if (emp and emp.department) else "General"
    days = float(leave_request.total_days)

    title = f"New Leave Application: {emp_name}"
    message = f"{emp_name} ({dept_name}) applied for {days:.1f} day(s) of {leave_request.leave_type.name if leave_request.leave_type else 'leave'} from {leave_request.start_date.strftime('%b %d')} to {leave_request.end_date.strftime('%b %d')}. Reason: {leave_request.reason[:80]}..."
    link = "/leaves/?status=Pending"

    # 1. Admin & HR User IDs
    target_uids = set(get_admin_and_hr_user_ids())

    # 2. Department Manager User ID
    if emp and emp.department and emp.department.manager_id:
        dept_mgr = Employee.query.get(emp.department.manager_id)
        if dept_mgr and dept_mgr.user_id:
            target_uids.add(dept_mgr.user_id)
    elif emp and emp.manager_id:
        direct_mgr = Employee.query.get(emp.manager_id)
        if direct_mgr and direct_mgr.user_id:
            target_uids.add(direct_mgr.user_id)

    # Exclude applicant from receiving applicant notification
    if emp and emp.user_id in target_uids:
        target_uids.remove(emp.user_id)

    notify_users(target_uids, title, message, link, notification_type='Warning')


def notify_leave_decision(leave_request, action, reviewer_name):
    """
    Notifies the employee when their leave request is Approved or Rejected.
    """
    emp = leave_request.employee
    if not emp or not emp.user_id:
        return

    days = float(leave_request.total_days)
    action_type = 'Success' if action == 'Approved' else 'Danger'
    title = f"Leave Request #{leave_request.id} {action}"
    message = f"Your leave request for {days:.1f} day(s) from {leave_request.start_date.strftime('%b %d')} to {leave_request.end_date.strftime('%b %d')} has been {action.lower()} by {reviewer_name}."
    if action == 'Rejected' and leave_request.rejection_reason:
        message += f" Remarks: {leave_request.rejection_reason}"
    link = "/leaves/"

    create_notification(emp.user_id, title, message, link, notification_type=action_type)


def notify_task_assignment(task, assigned_employee_id, assigner_name):
    """
    Notifies employee when a task is assigned to them.
    """
    emp = Employee.query.get(assigned_employee_id)
    if not emp or not emp.user_id:
        return

    title = f"New Task Assigned: {task.title[:50]}"
    deadline = task.due_date.strftime('%b %d, %Y') if task.due_date else 'No deadline'
    message = f"You have been assigned task '{task.title}' by {assigner_name}. Target deadline: {deadline}. Priority: {task.priority}."
    link = f"/tasks/{task.id}"

    create_notification(emp.user_id, title, message, link, notification_type='Info')


def notify_message_received(message_obj=None, recipient_user_id=None, sender=None, recipient_user=None, message=None):
    """
    Notifies recipient when a new internal message is sent.
    """
    msg = message_obj or message
    recip_id = recipient_user_id or (recipient_user.id if hasattr(recipient_user, 'id') else recipient_user)
    if not msg or not recip_id:
        return

    sender_name = sender.full_name if sender else (msg.sender.full_name if msg.sender else "A user")
    title = f"New Message from {sender_name}"
    preview = msg.body[:80] + ("..." if len(msg.body) > 80 else "")
    msg_text = f"Subject: {msg.subject}\n{preview}"
    link = f"/communication/messages/{msg.id}"

    create_notification(recip_id, title, msg_text, link, notification_type='Info')


create_system_notification = create_notification


