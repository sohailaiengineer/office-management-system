from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.extensions import db
from app.models.employee import Employee, Department, Designation
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest, LeaveBalance
from app.models.payroll import Payroll, PayrollDetail
from app.models.project import Project, Task, TaskAssignment, ProjectMember
from app.models.communication import Notification, Announcement
from app.models.system import AuditLog
from app.models.client import Client
from app.utils.decorators import login_required, get_current_user, get_user_role, get_managed_department

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    today = date.today()

    # ==============================================================
    # 1. SUPER ADMIN / ADMIN DASHBOARD
    # ==============================================================
    if role == 'super_admin':
        total_employees = Employee.active_query().count()
        active_employees = Employee.active_query().filter_by(status='Active').count()
        total_departments = Department.active_query().count()

        # Total managers assigned across departments
        total_managers = Department.active_query().filter(Department.manager_id.isnot(None)).count()

        # Today's attendance
        att_present = Attendance.active_query().filter(
            Attendance.date == today, Attendance.attendance_status == 'Present'
        ).count()
        att_late = Attendance.active_query().filter(
            Attendance.date == today, Attendance.attendance_status == 'Late'
        ).count()
        today_attendance_count = att_present + att_late
        att_absent = max(0, active_employees - today_attendance_count)

        # Leave metrics (Pending, Approved, Rejected)
        pending_leaves = LeaveRequest.active_query().filter_by(approval_status='Pending').count()
        approved_leaves = LeaveRequest.active_query().filter_by(approval_status='Approved').count()
        rejected_leaves = LeaveRequest.active_query().filter_by(approval_status='Rejected').count()

        # Monthly Payroll Summary & Total Payroll Runs
        latest_payroll = Payroll.active_query().order_by(Payroll.year.desc(), Payroll.month.desc()).first()
        monthly_payroll_amount = latest_payroll.net_amount if latest_payroll else Decimal('0.00')
        payroll_records_count = Payroll.active_query().count()

        # Projects & Tasks metrics
        active_projects = Project.active_query().filter(Project.project_status.in_(['Planning', 'In-Progress'])).count()
        total_tasks = Task.active_query().count()
        pending_tasks = Task.active_query().filter(Task.task_status.in_(['To-Do', 'Pending', 'In-Progress', 'Review'])).count()
        completed_tasks = Task.active_query().filter_by(task_status='Completed').count()
        total_clients = Client.active_query().count()

        # Managers & Teams Overview for Admin Dashboard
        all_departments = Department.active_query().all()
        managers_summary = []
        for d in all_departments:
            mem_count = Employee.active_query().filter_by(department_id=d.id).count()
            proj_count = Project.query.filter_by(department_id=d.id, is_deleted=False).count()
            managers_summary.append({
                'dept': d,
                'manager': d.manager,
                'members_count': mem_count,
                'projects_count': proj_count
            })

        # Department Distribution (Chart.js)
        dept_distribution = db.session.query(
            Department.name, db.func.count(Employee.id)
        ).join(Employee, Employee.department_id == Department.id)\
         .filter(Department.is_deleted == False, Employee.is_deleted == False)\
         .group_by(Department.name).all()

        dept_labels = [d[0] for d in dept_distribution] or ['Engineering', 'HR', 'Finance', 'Marketing']
        dept_counts = [d[1] for d in dept_distribution] or [1, 1, 1, 1]

        # Recent activities & approvals
        recent_activities = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
        pending_approvals_list = LeaveRequest.active_query().filter_by(approval_status='Pending').order_by(LeaveRequest.created_at.desc()).limit(5).all()
        recent_employees = Employee.active_query().order_by(Employee.id.desc()).limit(5).all()
        recent_notifications = Notification.active_query().filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard/admin_dashboard.html',
            total_employees=total_employees,
            active_employees=active_employees,
            total_departments=total_departments,
            total_managers=total_managers,
            today_attendance_count=today_attendance_count,
            att_present=att_present,
            att_late=att_late,
            att_absent=att_absent,
            pending_leaves=pending_leaves,
            approved_leaves=approved_leaves,
            rejected_leaves=rejected_leaves,
            monthly_payroll_amount=monthly_payroll_amount,
            payroll_records_count=payroll_records_count,
            active_projects=active_projects,
            total_tasks=total_tasks,
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            total_clients=total_clients,
            managers_summary=managers_summary,
            dept_labels=dept_labels,
            dept_counts=dept_counts,
            recent_activities=recent_activities,
            pending_approvals_list=pending_approvals_list,
            recent_employees=recent_employees,
            recent_notifications=recent_notifications
        )

    # ==============================================================
    # 2. HR MANAGER DASHBOARD
    # ==============================================================
    elif role == 'hr_manager':
        total_employees = Employee.active_query().count()
        active_employees = Employee.active_query().filter_by(status='Active').count()
        thirty_days_ago = today - timedelta(days=60)
        new_employees_count = Employee.active_query().filter(Employee.date_of_joining >= thirty_days_ago).count()

        # Employees on Leave Today
        employees_on_leave_today = LeaveRequest.active_query().filter(
            LeaveRequest.approval_status == 'Approved',
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today
        ).count()

        # Attendance breakdown today
        att_present = Attendance.active_query().filter(
            Attendance.date == today, Attendance.attendance_status == 'Present'
        ).count()
        att_late = Attendance.active_query().filter(
            Attendance.date == today, Attendance.attendance_status == 'Late'
        ).count()
        today_attendance = att_present + att_late
        att_absent = max(0, active_employees - today_attendance)

        # Leave metrics
        pending_leaves = LeaveRequest.active_query().filter_by(approval_status='Pending').count()
        approved_leaves_month = LeaveRequest.active_query().filter(
            LeaveRequest.approval_status == 'Approved',
            db.extract('month', LeaveRequest.start_date) == today.month
        ).count()

        # Monthly Payroll
        latest_payroll = Payroll.active_query().order_by(Payroll.year.desc(), Payroll.month.desc()).first()
        monthly_payroll_amount = latest_payroll.net_amount if latest_payroll else Decimal('0.00')

        # Recent joiners
        recent_joiners = Employee.active_query().order_by(Employee.date_of_joining.desc()).limit(5).all()

        # Pending Leave Applications
        pending_leave_applications = LeaveRequest.active_query().filter_by(approval_status='Pending').order_by(LeaveRequest.created_at.desc()).limit(6).all()

        # Recent HR activities
        recent_hr_activities = AuditLog.query.filter(
            AuditLog.table_name.in_(['employees', 'leaves', 'payrolls', 'attendance', 'salary_structures'])
        ).order_by(AuditLog.created_at.desc()).limit(7).all()

        # Department distribution
        dept_distribution = db.session.query(
            Department.name, db.func.count(Employee.id)
        ).join(Employee, Employee.department_id == Department.id)\
         .filter(Department.is_deleted == False, Employee.is_deleted == False)\
         .group_by(Department.name).all()

        dept_labels = [d[0] for d in dept_distribution] or ['HR', 'Engineering', 'Finance']
        dept_counts = [d[1] for d in dept_distribution] or [1, 1, 1]

        recent_notifications = Notification.active_query().filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard/hr_dashboard.html',
            total_employees=total_employees,
            active_employees=active_employees,
            new_employees_count=new_employees_count,
            employees_on_leave_today=employees_on_leave_today,
            today_attendance=today_attendance,
            att_present=att_present,
            att_late=att_late,
            att_absent=att_absent,
            pending_leaves=pending_leaves,
            approved_leaves_month=approved_leaves_month,
            monthly_payroll_amount=monthly_payroll_amount,
            recent_joiners=recent_joiners,
            pending_leave_applications=pending_leave_applications,
            recent_hr_activities=recent_hr_activities,
            dept_labels=dept_labels,
            dept_counts=dept_counts,
            recent_notifications=recent_notifications
        )

    # ==============================================================
    # 3. DEPARTMENT MANAGER DASHBOARD
    # ==============================================================
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        emp = user.employee

        if not managed_dept and emp and emp.department:
            managed_dept = emp.department

        dept_employees = []
        dept_emp_ids = []
        if managed_dept:
            dept_employees = Employee.active_query().filter_by(department_id=managed_dept.id).all()
            dept_emp_ids = [e.id for e in dept_employees]

        dept_total_employees = len(dept_employees)
        dept_active_employees = len([e for e in dept_employees if e.status == 'Active'])

        # Department Attendance today
        dept_present = 0
        dept_late = 0
        dept_attendance = 0
        dept_absent = 0
        if dept_emp_ids:
            dept_present = Attendance.active_query().filter(
                Attendance.employee_id.in_(dept_emp_ids),
                Attendance.date == today,
                Attendance.attendance_status == 'Present'
            ).count()
            dept_late = Attendance.active_query().filter(
                Attendance.employee_id.in_(dept_emp_ids),
                Attendance.date == today,
                Attendance.attendance_status == 'Late'
            ).count()
            dept_attendance = dept_present + dept_late
            dept_absent = max(0, dept_active_employees - dept_attendance)

        # Department Projects
        dept_projects = []
        if managed_dept:
            dept_projects = Project.active_query().filter(
                (Project.department_id == managed_dept.id) | (Project.lead_id == (emp.id if emp else 0))
            ).all()

        dept_project_ids = [p.id for p in dept_projects]

        # Department Tasks
        dept_tasks = []
        if dept_project_ids:
            dept_tasks = Task.active_query().filter(Task.project_id.in_(dept_project_ids)).all()
        elif dept_emp_ids:
            dept_tasks = Task.active_query().join(Task.assignments).filter(TaskAssignment.employee_id.in_(dept_emp_ids)).all()

        dept_pending_tasks = [t for t in dept_tasks if t.task_status in ['To-Do', 'Pending']]
        dept_in_progress_tasks = [t for t in dept_tasks if t.task_status == 'In-Progress']
        dept_review_tasks = [t for t in dept_tasks if t.task_status == 'Review']
        dept_completed_tasks = [t for t in dept_tasks if t.task_status == 'Completed']

        # Department Leave Requests
        dept_pending_leaves = []
        dept_approved_leaves_count = 0
        dept_rejected_leaves_count = 0
        if dept_emp_ids:
            dept_pending_leaves = LeaveRequest.active_query().filter(
                LeaveRequest.employee_id.in_(dept_emp_ids),
                LeaveRequest.approval_status == 'Pending'
            ).order_by(LeaveRequest.created_at.desc()).all()
            dept_approved_leaves_count = LeaveRequest.active_query().filter(
                LeaveRequest.employee_id.in_(dept_emp_ids),
                LeaveRequest.approval_status == 'Approved'
            ).count()
            dept_rejected_leaves_count = LeaveRequest.active_query().filter(
                LeaveRequest.employee_id.in_(dept_emp_ids),
                LeaveRequest.approval_status == 'Rejected'
            ).count()

        dept_pending_leaves_count = len(dept_pending_leaves)

        # Department Announcements
        dept_announcements = Announcement.active_query().filter(
            (Announcement.target_audience == 'All') | 
            (Announcement.department_id == (managed_dept.id if managed_dept else 0))
        ).order_by(Announcement.created_at.desc()).limit(5).all()

        recent_notifications = Notification.active_query().filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard/dept_manager_dashboard.html',
            managed_dept=managed_dept,
            dept_employees=dept_employees,
            dept_total_employees=dept_total_employees,
            dept_active_employees=dept_active_employees,
            dept_attendance=dept_attendance,
            dept_present=dept_present,
            dept_late=dept_late,
            dept_absent=dept_absent,
            dept_projects=dept_projects,
            dept_tasks=dept_tasks,
            dept_pending_tasks=dept_pending_tasks,
            dept_in_progress_tasks=dept_in_progress_tasks,
            dept_review_tasks=dept_review_tasks,
            dept_completed_tasks=dept_completed_tasks,
            dept_pending_leaves=dept_pending_leaves,
            dept_pending_leaves_count=dept_pending_leaves_count,
            dept_approved_leaves_count=dept_approved_leaves_count,
            dept_rejected_leaves_count=dept_rejected_leaves_count,
            dept_announcements=dept_announcements,
            recent_notifications=recent_notifications
        )

    # ==============================================================
    # 4. EMPLOYEE SELF-SERVICE DASHBOARD
    # ==============================================================
    else:
        emp = user.employee
        if not emp:
            flash('No employee profile is currently linked to your user account.', 'info')
            return render_template('dashboard/no_profile.html', user=user)

        # Today's attendance status
        today_attendance = Attendance.active_query().filter_by(employee_id=emp.id, date=today).first()

        # Monthly attendance summary
        month_records = Attendance.active_query().filter(
            Attendance.employee_id == emp.id,
            db.extract('year', Attendance.date) == today.year,
            db.extract('month', Attendance.date) == today.month
        ).all()
        month_present = len([a for a in month_records if a.attendance_status in ['Present', 'Late']])
        month_late = len([a for a in month_records if a.attendance_status == 'Late'])

        # Available Leave Balances
        leave_balances = LeaveBalance.active_query().filter_by(
            employee_id=emp.id, year=today.year
        ).all()

        # Pending & Recent Leave Requests
        pending_leaves = LeaveRequest.active_query().filter_by(
            employee_id=emp.id, approval_status='Pending'
        ).all()
        recent_leaves = LeaveRequest.active_query().filter_by(
            employee_id=emp.id
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()

        # Assigned Tasks
        my_tasks = Task.active_query().join(Task.assignments).filter(
            TaskAssignment.employee_id == emp.id
        ).order_by(Task.due_date.asc()).all()

        my_pending_tasks = [t for t in my_tasks if t.task_status in ['To-Do', 'Pending']]
        my_in_progress_tasks = [t for t in my_tasks if t.task_status == 'In-Progress']
        my_completed_tasks = [t for t in my_tasks if t.task_status == 'Completed']
        upcoming_tasks = [t for t in my_tasks if t.task_status != 'Completed'][:5]

        # Assigned Projects
        my_project_memberships = ProjectMember.active_query().filter_by(employee_id=emp.id).all()
        my_projects = [pm.project for pm in my_project_memberships if pm.project and not pm.project.is_deleted]
        if not my_projects and emp.department:
            my_projects = Project.active_query().filter_by(department_id=emp.department_id).limit(3).all()

        # Latest Salary Slip
        latest_payslip = PayrollDetail.active_query().filter_by(
            employee_id=emp.id
        ).order_by(PayrollDetail.id.desc()).first()

        # Announcements & Notifications
        announcements = Announcement.active_query().filter(
            (Announcement.target_audience == 'All') |
            (Announcement.department_id == (emp.department_id or 0))
        ).order_by(Announcement.created_at.desc()).limit(5).all()

        recent_notifications = Notification.active_query().filter_by(
            user_id=user.id
        ).order_by(Notification.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard/employee_dashboard.html',
            emp=emp,
            today_attendance=today_attendance,
            month_present=month_present,
            month_late=month_late,
            leave_balances=leave_balances,
            pending_leaves=pending_leaves,
            recent_leaves=recent_leaves,
            my_tasks=my_tasks,
            my_pending_tasks=my_pending_tasks,
            my_in_progress_tasks=my_in_progress_tasks,
            my_completed_tasks=my_completed_tasks,
            upcoming_tasks=upcoming_tasks,
            my_projects=my_projects,
            latest_payslip=latest_payslip,
            announcements=announcements,
            recent_notifications=recent_notifications
        )
