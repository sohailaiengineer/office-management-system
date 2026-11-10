import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

def is_email_configured():
    username = os.environ.get('MAIL_USERNAME')
    password = os.environ.get('MAIL_PASSWORD')
    return bool(username and password)

def send_email_notification(to_email, subject, body_text, body_html=None):
    """
    Sends an email notification via SMTP.
    If SMTP credentials are not configured or network fails,
    it logs the failure safely and never raises an unhandled exception.
    """
    if not to_email:
        return False

    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_pass = os.environ.get('MAIL_PASSWORD')
    default_sender = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@enterprise-oms.com')
    use_tls = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = default_sender
    msg['To'] = to_email

    part1 = MIMEText(body_text, 'plain')
    msg.attach(part1)

    if body_html:
        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)

    if not is_email_configured():
        logger.info(f"[EMAIL SIMULATION] To: {to_email} | Subject: {subject} | Content:\n{body_text[:200]}")
        return True

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(default_sender, [to_email], msg.as_string())
        server.quit()
        logger.info(f"[EMAIL DELIVERED] To: {to_email} | Subject: {subject}")
        return True
    except Exception as e:
        logger.warning(f"[EMAIL DELIVERY FAILED] To: {to_email} | Error: {str(e)}")
        return False


def send_welcome_employee_email(employee, activation_url=None, temp_password=None, app_url="http://127.0.0.1:5001"):
    """
    Sends onboarding email to new employee with portal instructions and secure access info.
    Includes account activation link and temporary password if provided.
    """
    if not employee or not employee.email:
        return False

    subject = f"Welcome to the Enterprise Workplace — {employee.full_name}"
    login_url = f"{app_url}/auth/login"

    body_text = f"""Hello {employee.full_name},

Welcome to the company! Your corporate employee profile and portal access have been registered in the Office Management System (OMS).

Employment & Profile Overview:
- Employee ID: {employee.emp_code}
- Full Name: {employee.full_name}
- Work Email: {employee.email}
- Username: {employee.user.username if employee.user else employee.email}
- Department: {employee.department.name if employee.department else 'General'}
- Designation: {employee.designation.title if employee.designation else 'Staff'}
- Joining Date: {employee.date_of_joining.strftime('%B %d, %Y') if employee.date_of_joining else 'Today'}
"""

    if temp_password:
        body_text += f"\nTemporary Initial Password: {temp_password}\n(You will be prompted to update this password upon initial sign in)\n"

    if activation_url:
        body_text += f"""
Account Activation:
Please activate your corporate account and configure your secure personal password using this direct link:
{activation_url}
(This activation link is valid for 7 days)
"""
    else:
        body_text += f"""
Accessing the Portal:
You can log in to your employee self-service portal at:
{login_url}
"""

    body_text += """
Best regards,
Human Resources & System Administration
OMS Enterprise Global
"""
    return send_email_notification(employee.email, subject, body_text)


def send_task_assigned_email(task, employee, assigner_name, app_url="http://127.0.0.1:5001"):
    """
    Sends task assignment notification email to employee.
    """
    if not employee or not employee.email:
        return False

    subject = f"New Task Assignment: {task.title}"
    deadline = task.due_date.strftime('%B %d, %Y') if task.due_date else 'Not specified'
    proj_name = task.project.name if task.project else 'General Deliverable'

    body_text = f"""Hello {employee.full_name},

A new deliverable has been assigned to you by {assigner_name}.

Task Overview:
- Title: {task.title}
- Project: {proj_name}
- Priority: {task.priority}
- Target Deadline: {deadline}
- Estimated Hours: {task.estimated_hours} hrs

Description & Scope:
{task.description or 'No specifications provided.'}

You can track, update your progress percentage, and add comments on this work item at:
{app_url}/tasks/{task.id}

Best regards,
Project Management Team
OMS Enterprise Global
"""
    return send_email_notification(employee.email, subject, body_text)


def send_task_updated_email(task, employee, updater_name, app_url="http://127.0.0.1:5001"):
    """
    Sends task status or schedule update notification email to employee.
    """
    if not employee or not employee.email:
        return False

    subject = f"Task Updated: {task.title}"
    deadline = task.due_date.strftime('%B %d, %Y') if task.due_date else 'Not specified'

    body_text = f"""Hello {employee.full_name},

Task deliverable "{task.title}" has been updated by {updater_name}.

Current Status:
- Status: {task.task_status}
- Priority: {task.priority}
- Deadline: {deadline}
- Progress: {task.progress_percentage}%

View the full task details and updates here:
{app_url}/tasks/{task.id}

Best regards,
Project Management Team
OMS Enterprise Global
"""
    return send_email_notification(employee.email, subject, body_text)


def send_salary_notification_email(detail, employee, app_url="http://127.0.0.1:5001"):
    """
    Sends private, confidential salary notification email ONLY to the recipient employee.
    """
    if not employee or not employee.email:
        return False

    month_name = f"{detail.payroll.month:02d}/{detail.payroll.year}" if detail.payroll else 'Current Pay Period'
    subject = f"Confidential: Salary Statement for {month_name} — #{detail.id}"

    body_text = f"""Hello {employee.full_name},

Your monthly salary statement for {month_name} has been processed and posted to your private self-service portal.

CONFIDENTIAL SALARY STATEMENT:
- Pay Period: {month_name}
- Basic Salary: ${float(detail.basic or 0):,.2f}
- Total Allowances: ${float(detail.allowances or 0):,.2f}
- Bonuses & Incentives: ${float(detail.bonuses_total or 0):,.2f}
- Overtime Compensation: ${float(detail.overtime_amount or 0):,.2f}
- Deductions: ${float(detail.deductions_total or 0):,.2f}
----------------------------------------
- NET DISBURSED SALARY: ${float(detail.net_salary or 0):,.2f}
- Disbursal Status: {detail.payment_status}

To view and print your complete official salary payslip, please sign in to your employee portal:
{app_url}/payroll/payslip/{detail.id}

CONFIDENTIALITY NOTICE:
This notification and its contents are strictly confidential and intended solely for {employee.full_name}.

Best regards,
Finance & Payroll Operations
OMS Enterprise Global
"""
    return send_email_notification(employee.email, subject, body_text)


def send_leave_status_email(leave_request, action, reviewer_name, app_url="http://127.0.0.1:5001"):
    """
    Sends leave application decision email to employee.
    """
    emp = leave_request.employee
    if not emp or not emp.email:
        return False

    subject = f"Leave Request #{leave_request.id} — {action}"
    days = float(leave_request.total_days)

    days_str = f"{days:.1f}"
    start_str = leave_request.start_date.strftime('%b %d, %Y') if leave_request.start_date else ''
    end_str = leave_request.end_date.strftime('%b %d, %Y') if leave_request.end_date else ''

    body_text = f"""Hello {emp.full_name},

Your leave application has been reviewed and marked as {action.upper()} by {reviewer_name}.

Application Summary:
- Request ID: #{leave_request.id}
- Leave Type: {leave_request.leave_type.name if leave_request.leave_type else 'General'}
- Duration: {days_str} day(s) ({start_str} to {end_str})
- Review Decision: {action}
"""
    if action == 'Rejected' and leave_request.rejection_reason:
        body_text += f"- Reviewer Remarks: {leave_request.rejection_reason}\n"

    body_text += f"\nYou can view your leave ledger and balance quota at:\n{app_url}/leaves/\n\nBest regards,\nDepartment Management & HR Operations"
    return send_email_notification(emp.email, subject, body_text)

