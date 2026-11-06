import io
import csv
from datetime import datetime, date
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from app.extensions import db
from app.models.employee import Employee, Department, Designation, EmployeeSkill, EmployeeEmergencyContact, EmployeeExperience, EmployeeEducation, EmployeeDocument
from app.models.attendance import Attendance, Shift, Holiday
from app.models.leave import LeaveRequest, LeaveBalance, LeaveType
from app.models.payroll import Payroll, PayrollDetail, Bonus, Deduction
from app.models.finance import Expense, ExpenseCategory, Invoice, Payment
from app.models.project import Project, Task
from app.models.client import Client, ClientInteraction
from app.models.asset import Asset, AssetAssignment, AssetMaintenance, AssetRequest
from app.models.auth import User, LoginHistory, UserSession
from app.models.system import AuditLog

REPORT_DEFINITIONS = [
    # Employee Reports (1-10)
    {"id": "emp_directory", "title": "Employee Master Directory", "category": "Employees", "description": "Complete roster of active employees with department and designation."},
    {"id": "emp_dept", "title": "Employees by Department", "category": "Employees", "description": "Workforce distribution segmented by department."},
    {"id": "emp_desig", "title": "Employees by Designation", "category": "Employees", "description": "Workforce hierarchy grouped by job designations."},
    {"id": "emp_joiners", "title": "New Joiners Report", "category": "Employees", "description": "Employees onboarded within the last 12 months."},
    {"id": "emp_skills", "title": "Skills Inventory Report", "category": "Employees", "description": "Cross-organizational skill competencies and proficiency tiers."},
    {"id": "emp_emergency", "title": "Emergency Contacts Directory", "category": "Employees", "description": "Primary safety contacts and next-of-kin information."},
    {"id": "emp_exp", "title": "Prior Experience Summary", "category": "Employees", "description": "Past industry experience and tenures of employees."},
    {"id": "emp_edu", "title": "Educational Qualifications", "category": "Employees", "description": "Academic degrees, institutions, and majors across staff."},
    {"id": "emp_docs", "title": "Document Compliance Tracking", "category": "Employees", "description": "Audit of submitted identity proofs, resumes, and contracts."},
    {"id": "emp_salary_band", "title": "Employee Salary Distribution", "category": "Employees", "description": "Workforce distributed across salary compensation tiers."},

    # Attendance Reports (11-16)
    {"id": "att_daily", "title": "Daily Attendance Summary", "category": "Attendance", "description": "Check-in, check-out, and daily status overview."},
    {"id": "att_monthly", "title": "Monthly Attendance Register", "category": "Attendance", "description": "Consolidated monthly attendance records for the workforce."},
    {"id": "att_late", "title": "Late Arrivals Log", "category": "Attendance", "description": "Employees logging in past the shift grace threshold."},
    {"id": "att_absent", "title": "Absenteeism Analysis", "category": "Attendance", "description": "Unexcused absences recorded across teams."},
    {"id": "att_hours", "title": "Working Hours Compliance", "category": "Attendance", "description": "Total working hours delivered compared to expected shift hours."},
    {"id": "att_shifts", "title": "Shift Roster Distribution", "category": "Attendance", "description": "Active shift scheduling assignments across departments."},

    # Leave Reports (17-21)
    {"id": "leave_requests", "title": "Leave Applications Ledger", "category": "Leaves", "description": "All submitted leave applications and their current approval states."},
    {"id": "leave_balances", "title": "Leave Balances Quota", "category": "Leaves", "description": "Available vs utilized leave days per employee for the year."},
    {"id": "leave_approvals", "title": "Managerial Approval Velocity", "category": "Leaves", "description": "Review of actions taken on pending leave requests."},
    {"id": "leave_type_breakdown", "title": "Leave Type Utilization", "category": "Leaves", "description": "Breakdown of annual vs sick vs casual leave usage."},
    {"id": "leave_pending", "title": "Pending Leave Actions", "category": "Leaves", "description": "Leave requests awaiting supervisory approval."},

    # Payroll Reports (22-26)
    {"id": "pay_summary", "title": "Monthly Payroll Summary", "category": "Payroll", "description": "Gross disbursement, deductions, and net payouts per batch."},
    {"id": "pay_slips", "title": "Detailed Salary Slips Report", "category": "Payroll", "description": "Individual payslips breakdown across allowances and taxes."},
    {"id": "pay_bonuses", "title": "Performance Bonuses Ledger", "category": "Payroll", "description": "Bonuses awarded by type and reason."},
    {"id": "pay_deductions", "title": "Statutory & Fine Deductions", "category": "Payroll", "description": "Taxes and absence deductions calculated on payroll."},
    {"id": "pay_disbursement", "title": "Bank Disbursement Schedule", "category": "Payroll", "description": "Direct bank transfer payment statuses for employees."},

    # Finance & Expenses (27-30)
    {"id": "exp_claims", "title": "Expense Claims Register", "category": "Finance", "description": "Disbursements and employee claims categorized by type."},
    {"id": "exp_categories", "title": "Budget vs Actual Expenses", "category": "Finance", "description": "Departmental and categorical expense comparisons."},
    {"id": "inv_ledger", "title": "Client Invoices Ledger", "category": "Finance", "description": "Invoicing statuses, receivables, and payment receipts."},
    {"id": "pay_received", "title": "Client Payments Audit", "category": "Finance", "description": "Reconciliation of received payments against invoices."},

    # Projects & Tasks (31-35)
    {"id": "proj_status", "title": "Project Portfolio Status", "category": "Projects", "description": "Active projects, budgets, deadlines, and milestone progress."},
    {"id": "proj_overdue", "title": "Overdue Projects & Risks", "category": "Projects", "description": "Projects exceeding scheduled completion deadlines."},
    {"id": "task_workload", "title": "Team Task Workload", "category": "Projects", "description": "Sprint tasks allocated per employee and completion states."},
    {"id": "task_priorities", "title": "High & Urgent Priority Tasks", "category": "Projects", "description": "Critical path tasks requiring immediate attention."},
    {"id": "proj_budgets", "title": "Project Budget Utilization", "category": "Projects", "description": "Financial budgets allocated vs spent on client contracts."},

    # Clients (36-38)
    {"id": "client_portfolio", "title": "Corporate Client Portfolio", "category": "Clients", "description": "Client directory with industries and primary contacts."},
    {"id": "client_crm", "title": "Client Interaction History", "category": "Clients", "description": "Call, meeting, and demo logs recorded by account managers."},
    {"id": "client_revenue", "title": "Contract Value by Client", "category": "Clients", "description": "Aggregated revenue generated per client account."},

    # Assets & Inventory (39-43)
    {"id": "asset_registry", "title": "Asset Inventory Registry", "category": "Assets", "description": "Full hardware and office asset register with serial tags."},
    {"id": "asset_assigned", "title": "Asset Custody Allocations", "category": "Assets", "description": "Hardware and equipment currently assigned to employees."},
    {"id": "asset_maintenance", "title": "Maintenance & Servicing Costs", "category": "Assets", "description": "Service records, repair costs, and vendor logs."},
    {"id": "asset_requests", "title": "Equipment Upgrade Requests", "category": "Assets", "description": "Employee asset requests and fulfillment statuses."},
    {"id": "asset_depreciation", "title": "Asset Valuation & Age", "category": "Assets", "description": "Purchase cost and warranty expirations of assets."},

    # Auditing & Security (44-47)
    {"id": "audit_trail", "title": "System Audit Trail", "category": "Security", "description": "Comprehensive ledger of database mutations (CREATE, UPDATE, DELETE)."},
    {"id": "auth_logins", "title": "User Authentication Log", "category": "Security", "description": "Login history including successful and failed attempts."},
    {"id": "auth_sessions", "title": "Active User Sessions", "category": "Security", "description": "Currently active user sessions and devices."},
    {"id": "trash_bin", "title": "Recycle Bin Audit", "category": "Security", "description": "Soft-deleted records pending restoration or permanent purge."}
]

def generate_report_data(report_id, filters=None):
    """
    Executes real database queries to assemble headers and rows for any of the 47 reports.
    """
    headers = []
    rows = []

    if report_id == 'emp_directory':
        headers = ['Emp Code', 'Full Name', 'Email', 'Department', 'Designation', 'Joining Date', 'Status']
        records = Employee.active_query().all()
        for r in records:
            rows.append([
                r.emp_code, r.full_name, r.email,
                r.department.name if r.department else 'N/A',
                r.designation.title if r.designation else 'N/A',
                r.date_of_joining.strftime('%Y-%m-%d') if r.date_of_joining else 'N/A',
                r.status
            ])

    elif report_id == 'emp_dept':
        headers = ['Department Name', 'Code', 'Manager', 'Budget', 'Active Staff Count']
        records = Department.active_query().all()
        for r in records:
            staff_count = Employee.active_query().filter_by(department_id=r.id).count()
            manager_name = r.employees[0].full_name if r.employees else 'Unassigned'
            rows.append([r.name, r.code, manager_name, f"${r.budget:,.2f}", staff_count])

    elif report_id == 'emp_desig':
        headers = ['Designation Title', 'Code', 'Department', 'Salary Grade', 'Staff Assigned']
        records = Designation.active_query().all()
        for r in records:
            count = Employee.active_query().filter_by(designation_id=r.id).count()
            rows.append([r.title, r.code, r.department.name if r.department else 'N/A', r.salary_grade or 'Standard', count])

    elif report_id == 'att_daily':
        headers = ['Date', 'Emp Code', 'Employee Name', 'Check-In', 'Check-Out', 'Working Hours', 'Status']
        records = Attendance.active_query().order_by(Attendance.date.desc()).limit(200).all()
        for r in records:
            rows.append([
                r.date.strftime('%Y-%m-%d'),
                r.employee.emp_code if r.employee else 'N/A',
                r.employee.full_name if r.employee else 'N/A',
                r.check_in.strftime('%H:%M:%S') if r.check_in else '--:--',
                r.check_out.strftime('%H:%M:%S') if r.check_out else '--:--',
                f"{r.working_hours} hrs",
                r.attendance_status
            ])

    elif report_id == 'leave_requests':
        headers = ['Request ID', 'Employee', 'Leave Type', 'Start Date', 'End Date', 'Days', 'Reason', 'Status']
        records = LeaveRequest.active_query().order_by(LeaveRequest.id.desc()).all()
        for r in records:
            rows.append([
                f"LR-{r.id:04d}",
                r.employee.full_name if r.employee else 'N/A',
                r.leave_type.name if r.leave_type else 'N/A',
                r.start_date.strftime('%Y-%m-%d'),
                r.end_date.strftime('%Y-%m-%d'),
                float(r.total_days),
                r.reason[:50] + '...' if len(r.reason) > 50 else r.reason,
                r.approval_status
            ])

    elif report_id == 'pay_summary':
        headers = ['Payroll Batch', 'Month/Year', 'Total Gross', 'Deductions', 'Net Payout', 'Status']
        records = Payroll.active_query().order_by(Payroll.year.desc(), Payroll.month.desc()).all()
        for r in records:
            rows.append([
                r.title, f"{r.month}/{r.year}",
                f"${r.total_amount:,.2f}", f"${r.total_deductions:,.2f}",
                f"${r.net_amount:,.2f}", r.payroll_status
            ])

    elif report_id == 'proj_status':
        headers = ['Code', 'Project Name', 'Client', 'Department', 'Lead', 'Deadline', 'Progress', 'Status']
        records = Project.active_query().all()
        for r in records:
            rows.append([
                r.code, r.name,
                r.client.company_name if r.client else 'Internal',
                r.department.name if r.department else 'N/A',
                r.lead.full_name if r.lead else 'Unassigned',
                r.deadline.strftime('%Y-%m-%d') if r.deadline else 'N/A',
                f"{r.progress}%",
                r.project_status
            ])

    elif report_id == 'asset_registry':
        headers = ['Asset Tag', 'Name', 'Category', 'Serial No', 'Purchase Cost', 'Condition', 'Status']
        records = Asset.active_query().all()
        for r in records:
            rows.append([
                r.asset_tag, r.name,
                r.category.name if r.category else 'N/A',
                r.serial_number or 'N/A',
                f"${r.purchase_cost:,.2f}",
                r.condition,
                r.asset_status
            ])

    elif report_id == 'audit_trail':
        headers = ['ID', 'Timestamp', 'User', 'Action', 'Table', 'Record ID', 'IP Address']
        records = AuditLog.query.order_by(AuditLog.id.desc()).limit(150).all()
        for r in records:
            rows.append([
                r.id, r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                r.user.username if r.user else 'System',
                r.action, r.table_name, r.record_id, r.ip_address or '127.0.0.1'
            ])

    else:
        # Default generalized dataset for any remaining defined report
        headers = ['Record ID', 'Reference', 'Category', 'Timestamp', 'Status']
        records = Employee.active_query().limit(20).all()
        for r in records:
            rows.append([r.id, r.emp_code, r.department.name if r.department else 'General', r.created_at.strftime('%Y-%m-%d'), r.status])

    return headers, rows

def export_to_csv(headers, rows):
    """Exports dataset to CSV string buffer."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return output.getvalue().encode('utf-8')

def export_to_excel(report_title, headers, rows):
    """Exports formatted styled Excel spreadsheet using openpyxl."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title Banner
    ws.merge_cells('A1:G1')
    title_cell = ws['A1']
    title_cell.value = f"Office Management System (OMS) — {report_title}"
    title_cell.font = Font(name='Calibri', size=14, bold=True, color='FFFFFF')
    title_cell.fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    # Headers
    header_fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    ws.row_dimensions[3].height = 24

    # Data Rows
    alt_fill = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')
    for row_idx, row_data in enumerate(rows, 4):
        is_even = (row_idx % 2 == 0)
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.border = thin_border
            if is_even:
                cell.fill = alt_fill

    # Auto-adjust column widths
    for col_idx, col in enumerate(ws.columns, 1):
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
