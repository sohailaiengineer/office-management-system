import os
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.utils import utc_now
from app.models import (
    # Auth (8)
    User, Role, Permission, UserRole, RolePermission, UserSession, LoginHistory, PasswordResetToken,
    # Employee (12)
    Department, DepartmentLocation, Designation, Employee, EmployeeProfile,
    EmployeeContact, EmployeeAddress, EmployeeEducation, EmployeeExperience,
    EmployeeDocument, EmployeeSkill, EmployeeEmergencyContact,
    # Attendance (5)
    Shift, ShiftAssignment, Attendance, AttendanceLog, Holiday,
    # Leave (5)
    LeaveType, LeaveBalance, LeaveRequest, LeaveApproval, LeaveAttachment,
    # Payroll (6)
    SalaryStructure, EmployeeSalary, Payroll, PayrollDetail, Bonus, Deduction,
    # Finance (5)
    ExpenseCategory, Expense, ExpenseApproval, Invoice, Payment,
    # Project (6)
    Project, ProjectMember, Task, TaskAssignment, TaskComment, TaskAttachment,
    # Client (4)
    Client, ClientContact, ClientProject, ClientInteraction,
    # Asset (5)
    AssetCategory, Asset, AssetAssignment, AssetMaintenance, AssetRequest,
    # Document (4)
    DocumentCategory, Document, DocumentVersion, DocumentShare,
    # Communication (4)
    Announcement, Notification, Message, MessageRecipient,
    # System (4)
    AuditLog, SystemSetting, ApprovalWorkflow, ApprovalHistory
)

app = create_app('development')

def seed_database():
    with app.app_context():
        print("Creating all tables in MySQL...")
        db.create_all()
        print("All database tables created successfully!")

        # Check if already seeded
        if User.query.first():
            print("Database already contains data. Skipping initial seeding.")
            return

        print("Seeding Roles and Permissions...")
        roles_data = [
            ('super_admin', 'Super Admin', 'Unrestricted administrative control across all enterprise modules.', True),
            ('hr_manager', 'HR Manager', 'Workforce administration, attendance, leaves, and payroll management.', True),
            ('dept_manager', 'Department Manager', 'Departmental oversight, projects, and task management.', True),
            ('employee', 'Employee', 'Employee self-service portal, attendance, and tasks.', True)
        ]
        roles_dict = {}
        for code, disp, desc, sys in roles_data:
            r = Role(name=code, display_name=disp, description=desc, is_system=sys)
            db.session.add(r)
            roles_dict[code] = r
        db.session.flush()

        # Seed Users
        print("Seeding Enterprise Users...")
        # 1. Super Admin
        admin_user = User(
            username='admin',
            email='admin@enterprise-oms.com',
            first_name='Alexander',
            last_name='Pierce',
            phone='+1-555-0100',
            password_hash=generate_password_hash('Admin@123'),
            is_admin=True
        )
        db.session.add(admin_user)

        # 2. HR Manager
        hr_user = User(
            username='hrmanager',
            email='hr@enterprise-oms.com',
            first_name='Sarah',
            last_name='Connor',
            phone='+1-555-0101',
            password_hash=generate_password_hash('Hr@123'),
            is_admin=False
        )
        db.session.add(hr_user)

        # 3. Dept Manager
        mgr_user = User(
            username='deptmanager',
            email='manager@enterprise-oms.com',
            first_name='Michael',
            last_name='Scott',
            phone='+1-555-0102',
            password_hash=generate_password_hash('Manager@123'),
            is_admin=False
        )
        db.session.add(mgr_user)

        # 4. Standard Employee
        emp_user = User(
            username='johndoe',
            email='john.doe@enterprise-oms.com',
            first_name='John',
            last_name='Doe',
            phone='+1-555-0103',
            password_hash=generate_password_hash('Emp@123'),
            is_admin=False
        )
        db.session.add(emp_user)
        db.session.flush()

        # Link users to roles
        db.session.add(UserRole(user_id=admin_user.id, role_id=roles_dict['super_admin'].id, created_by=admin_user.id))
        db.session.add(UserRole(user_id=hr_user.id, role_id=roles_dict['hr_manager'].id, created_by=admin_user.id))
        db.session.add(UserRole(user_id=mgr_user.id, role_id=roles_dict['dept_manager'].id, created_by=admin_user.id))
        db.session.add(UserRole(user_id=emp_user.id, role_id=roles_dict['employee'].id, created_by=admin_user.id))
        db.session.flush()

        # Seed Departments
        print("Seeding Departments and Designations...")
        eng_dept = Department(name='Engineering', code='ENG', budget=Decimal('350000.00'), description='Software development and IT operations.', created_by=admin_user.id)
        hr_dept = Department(name='Human Resources', code='HR', budget=Decimal('120000.00'), description='Recruiting, employee relations, and payroll.', created_by=admin_user.id)
        fin_dept = Department(name='Finance & Accounts', code='FIN', budget=Decimal('150000.00'), description='Financial reporting and invoicing.', created_by=admin_user.id)
        mkt_dept = Department(name='Marketing & Sales', code='MKT', budget=Decimal('200000.00'), description='Client acquisition and branding.', created_by=admin_user.id)
        db.session.add_all([eng_dept, hr_dept, fin_dept, mkt_dept])
        db.session.flush()

        # Department Locations
        db.session.add(DepartmentLocation(department_id=eng_dept.id, location_name='Tech Hub Floor 4', floor='4', room_number='401-410', created_by=admin_user.id))
        db.session.add(DepartmentLocation(department_id=hr_dept.id, location_name='Corporate Floor 2', floor='2', room_number='205', created_by=admin_user.id))

        # Designations
        desig_eng_lead = Designation(title='Engineering Manager', code='ENG-MGR', department_id=eng_dept.id, min_salary=Decimal('8000.00'), max_salary=Decimal('12000.00'), created_by=admin_user.id)
        desig_sr_dev = Designation(title='Senior Full-Stack Developer', code='SR-DEV', department_id=eng_dept.id, min_salary=Decimal('5000.00'), max_salary=Decimal('8000.00'), created_by=admin_user.id)
        desig_hr_mgr = Designation(title='HR Operations Manager', code='HR-MGR', department_id=hr_dept.id, min_salary=Decimal('6000.00'), max_salary=Decimal('9000.00'), created_by=admin_user.id)
        db.session.add_all([desig_eng_lead, desig_sr_dev, desig_hr_mgr])
        db.session.flush()

        # Seed Employees
        print("Seeding Employee Profiles...")
        emp_admin = Employee(
            user_id=admin_user.id, emp_code='EMP-001', department_id=eng_dept.id, designation_id=desig_eng_lead.id,
            date_of_joining=date(2021, 1, 15), employment_type='Full-Time', basic_salary=Decimal('9500.00'),
            created_by=admin_user.id
        )
        emp_hr = Employee(
            user_id=hr_user.id, emp_code='EMP-002', department_id=hr_dept.id, designation_id=desig_hr_mgr.id,
            date_of_joining=date(2022, 3, 1), employment_type='Full-Time', basic_salary=Decimal('6500.00'),
            created_by=admin_user.id
        )
        emp_mgr = Employee(
            user_id=mgr_user.id, emp_code='EMP-003', department_id=eng_dept.id, designation_id=desig_eng_lead.id,
            date_of_joining=date(2022, 6, 15), employment_type='Full-Time', basic_salary=Decimal('8200.00'),
            created_by=admin_user.id
        )
        db.session.add_all([emp_admin, emp_hr, emp_mgr])
        db.session.flush()

        # Assign Department Managers
        eng_dept.manager_id = emp_mgr.id
        hr_dept.manager_id = emp_hr.id

        emp_dev = Employee(
            user_id=emp_user.id, emp_code='EMP-004', department_id=eng_dept.id, designation_id=desig_sr_dev.id,
            manager_id=emp_mgr.id, date_of_joining=date(2023, 2, 1), employment_type='Full-Time', basic_salary=Decimal('5500.00'),
            created_by=admin_user.id
        )
        db.session.add(emp_dev)
        db.session.flush()

        # Profiles
        db.session.add(EmployeeProfile(employee_id=emp_admin.id, bio='System architect with 15 years experience.', gender='Male', marital_status='Married', blood_group='O+', nationality='American', created_by=admin_user.id))
        db.session.add(EmployeeProfile(employee_id=emp_hr.id, bio='Specialist in talent management and HR tech.', gender='Female', marital_status='Single', blood_group='A+', nationality='American', created_by=admin_user.id))
        db.session.add(EmployeeProfile(employee_id=emp_mgr.id, bio='Experienced departmental lead.', gender='Male', marital_status='Married', blood_group='B+', nationality='American', created_by=admin_user.id))
        db.session.add(EmployeeProfile(employee_id=emp_dev.id, bio='Full-Stack developer proficient in Python, Flask, and JS.', gender='Male', marital_status='Single', blood_group='AB+', nationality='American', created_by=admin_user.id))

        # Contacts & Addresses
        db.session.add(EmployeeContact(employee_id=emp_dev.id, personal_email='johndoe.personal@gmail.com', work_phone='+1-555-0103', personal_phone='+1-555-9988', created_by=admin_user.id))
        db.session.add(EmployeeAddress(employee_id=emp_dev.id, address_type='Current', street='742 Evergreen Terrace', city='Springfield', state='IL', zip_code='62704', country='USA', created_by=admin_user.id))
        db.session.add(EmployeeEducation(employee_id=emp_dev.id, degree='B.S. in Computer Science', institution='State University', passing_year=2020, result='3.85 GPA', major='Software Systems', created_by=admin_user.id))
        db.session.add(EmployeeExperience(employee_id=emp_dev.id, company_name='TechSoft Innovations', designation='Junior Python Developer', start_date=date(2020, 7, 1), end_date=date(2023, 1, 15), responsibilities='Built REST APIs and web scraping pipelines.', created_by=admin_user.id))
        db.session.add(EmployeeSkill(employee_id=emp_dev.id, skill_name='Python & Flask', proficiency_level='Expert', years_experience=Decimal('4.5'), created_by=admin_user.id))
        db.session.add(EmployeeSkill(employee_id=emp_dev.id, skill_name='MySQL & Database Design', proficiency_level='Expert', years_experience=Decimal('4.0'), created_by=admin_user.id))
        db.session.add(EmployeeEmergencyContact(employee_id=emp_dev.id, name='Jane Doe', relationship='Spouse', phone='+1-555-1234', address='Same as residential', created_by=admin_user.id))

        # Seed Shifts & Attendance
        print("Seeding Shifts and Attendance Records...")
        day_shift = Shift(name='Regular Day Shift', start_time=time(9, 0), end_time=time(17, 0), grace_minutes=15, half_day_hours=Decimal('4.00'), is_night_shift=False, created_by=admin_user.id)
        db.session.add(day_shift)
        db.session.flush()

        db.session.add(ShiftAssignment(employee_id=emp_dev.id, shift_id=day_shift.id, start_date=date(2023, 2, 1), is_active=True, created_by=admin_user.id))
        db.session.add(Holiday(name='New Year Holiday', start_date=date(date.today().year, 1, 1), end_date=date(date.today().year, 1, 1), total_days=1, is_recurring=True, created_by=admin_user.id))
        db.session.add(Holiday(name='Independence Day', start_date=date(date.today().year, 7, 4), end_date=date(date.today().year, 7, 4), total_days=1, is_recurring=True, created_by=admin_user.id))

        # 5 days of attendance for each employee
        for i in range(5):
            att_date = date.today() - timedelta(days=i)
            # Today's record
            check_in_time = datetime.combine(att_date, time(9, 5))
            check_out_time = datetime.combine(att_date, time(17, 10))
            att = Attendance(
                employee_id=emp_dev.id,
                date=att_date,
                check_in=check_in_time,
                check_out=check_out_time,
                working_hours=Decimal('8.08'),
                late_minutes=0,
                attendance_status='Present',
                created_by=admin_user.id
            )
            db.session.add(att)
            db.session.flush()
            db.session.add(AttendanceLog(attendance_id=att.id, employee_id=emp_dev.id, log_time=check_in_time, punch_type='IN', created_by=admin_user.id))
            db.session.add(AttendanceLog(attendance_id=att.id, employee_id=emp_dev.id, log_time=check_out_time, punch_type='OUT', created_by=admin_user.id))

        # Seed Leave Management
        print("Seeding Leave Types and Balances...")
        annual_leave = LeaveType(name='Annual Leave', code='AL', max_days_per_year=18, is_paid=True, carry_forward=True, created_by=admin_user.id)
        sick_leave = LeaveType(name='Sick Leave', code='SL', max_days_per_year=12, is_paid=True, carry_forward=False, created_by=admin_user.id)
        casual_leave = LeaveType(name='Casual Leave', code='CL', max_days_per_year=10, is_paid=True, carry_forward=False, created_by=admin_user.id)
        db.session.add_all([annual_leave, sick_leave, casual_leave])
        db.session.flush()

        for emp in [emp_admin, emp_hr, emp_mgr, emp_dev]:
            db.session.add(LeaveBalance(employee_id=emp.id, leave_type_id=annual_leave.id, year=date.today().year, total_allocated=Decimal('18.0'), used_days=Decimal('2.0'), pending_days=Decimal('0.0'), remaining_days=Decimal('16.0'), created_by=admin_user.id))
            db.session.add(LeaveBalance(employee_id=emp.id, leave_type_id=sick_leave.id, year=date.today().year, total_allocated=Decimal('12.0'), used_days=Decimal('1.0'), pending_days=Decimal('0.0'), remaining_days=Decimal('11.0'), created_by=admin_user.id))

        # Sample Leave Request
        lr = LeaveRequest(
            employee_id=emp_dev.id,
            leave_type_id=annual_leave.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            total_days=Decimal('3.0'),
            reason='Family gathering and annual vacation trip.',
            approval_status='Approved',
            approver_id=emp_hr.id,
            approved_at=utc_now(),
            created_by=emp_dev.user_id
        )
        db.session.add(lr)

        # Seed Payroll
        print("Seeding Payroll & Compensation...")
        salary_structure = SalaryStructure(
            name='Standard Enterprise Structure',
            code='SAL-STD',
            basic_percentage=Decimal('50.00'),
            hra_percentage=Decimal('20.00'),
            da_percentage=Decimal('10.00'),
            allowance_fixed=Decimal('500.00'),
            tax_percentage=Decimal('5.00'),
            created_by=admin_user.id
        )
        db.session.add(salary_structure)
        db.session.flush()

        # Employee Salaries
        db.session.add(EmployeeSalary(
            employee_id=emp_dev.id,
            salary_structure_id=salary_structure.id,
            basic_salary=Decimal('5500.00'),
            house_rent=Decimal('1100.00'),
            medical_allowance=Decimal('350.00'),
            transport_allowance=Decimal('250.00'),
            gross_salary=Decimal('7200.00'),
            created_by=admin_user.id
        ))

        # Seed a processed payroll
        prev_month = date.today().month - 1 if date.today().month > 1 else 12
        prev_year = date.today().year if date.today().month > 1 else date.today().year - 1
        payroll_batch = Payroll(
            month=prev_month,
            year=prev_year,
            title=f"Monthly Payroll - {date(prev_year, prev_month, 1).strftime('%B %Y')}",
            total_amount=Decimal('28500.00'),
            total_deductions=Decimal('1425.00'),
            net_amount=Decimal('27075.00'),
            payroll_status='Paid',
            processed_at=utc_now(),
            processed_by=admin_user.id,
            created_by=admin_user.id
        )
        db.session.add(payroll_batch)
        db.session.flush()

        detail_dev = PayrollDetail(
            payroll_id=payroll_batch.id,
            employee_id=emp_dev.id,
            basic=Decimal('5500.00'),
            allowances=Decimal('1700.00'),
            overtime_amount=Decimal('0.00'),
            bonuses_total=Decimal('500.00'),
            deductions_total=Decimal('360.00'),
            net_salary=Decimal('7340.00'),
            payment_status='Paid',
            payment_date=date.today(),
            payment_method='Bank Wire',
            created_by=admin_user.id
        )
        db.session.add(detail_dev)
        db.session.flush()

        db.session.add(Bonus(employee_id=emp_dev.id, payroll_detail_id=detail_dev.id, bonus_type='Performance', amount=Decimal('500.00'), reason='Q3 milestone deliverable completed ahead of schedule.', created_by=admin_user.id))
        db.session.add(Deduction(employee_id=emp_dev.id, payroll_detail_id=detail_dev.id, deduction_type='Tax', amount=Decimal('360.00'), reason='Federal and state statutory income tax.', created_by=admin_user.id))

        # Seed Finance
        print("Seeding Finance, Expenses, and Invoices...")
        exp_cat1 = ExpenseCategory(name='Office Supplies & Equipment', code='EXP-OFF', monthly_budget=Decimal('5000.00'), created_by=admin_user.id)
        exp_cat2 = ExpenseCategory(name='Travel & Transportation', code='EXP-TRV', monthly_budget=Decimal('10000.00'), created_by=admin_user.id)
        exp_cat3 = ExpenseCategory(name='Software & Cloud Subscriptions', code='EXP-SFT', monthly_budget=Decimal('8000.00'), created_by=admin_user.id)
        db.session.add_all([exp_cat1, exp_cat2, exp_cat3])
        db.session.flush()

        db.session.add(Expense(
            category_id=exp_cat3.id,
            title='AWS Cloud Hosting Infrastructure',
            amount=Decimal('1240.50'),
            expense_date=date.today() - timedelta(days=5),
            paid_by_id=emp_dev.id,
            payment_method='Corporate Card',
            expense_status='Approved',
            description='Monthly cloud server hosting and RDS database hosting.',
            created_by=admin_user.id
        ))

        # Clients & Projects
        print("Seeding Clients, Projects, and Tasks...")
        client1 = Client(
            company_name='Apex Financial Global',
            client_code='CL-APEX',
            industry='FinTech',
            website='https://apexfinance.example.com',
            email='contracts@apexfinance.example.com',
            phone='+1-800-555-0199',
            country='USA',
            created_by=admin_user.id
        )
        db.session.add(client1)
        db.session.flush()

        db.session.add(ClientContact(client_id=client1.id, name='Eleanor Vance', designation='Chief Technology Officer', email='evance@apexfinance.example.com', phone='+1-555-4321', is_primary=True, created_by=admin_user.id))
        db.session.add(ClientInteraction(client_id=client1.id, interaction_type='Meeting', summary='Quarterly review of software features and performance metrics.', conducted_by_id=emp_mgr.id, created_by=admin_user.id))

        # Invoice
        inv1 = Invoice(
            invoice_number='INV-2026-001',
            client_id=client1.id,
            issue_date=date.today() - timedelta(days=15),
            due_date=date.today() + timedelta(days=15),
            subtotal=Decimal('25000.00'),
            tax_amount=Decimal('1250.00'),
            total_amount=Decimal('26250.00'),
            amount_paid=Decimal('26250.00'),
            payment_status='Paid',
            notes='Q1 Enterprise Software Development Milestone.',
            created_by=admin_user.id
        )
        db.session.add(inv1)
        db.session.flush()
        db.session.add(Payment(invoice_id=inv1.id, amount=Decimal('26250.00'), payment_date=date.today() - timedelta(days=5), payment_method='Bank Wire', transaction_ref='TXN-984210', created_by=admin_user.id))

        # Projects & Tasks
        proj1 = Project(
            name='Enterprise Portal Modernization',
            code='PRJ-OMS-2026',
            client_id=client1.id,
            department_id=eng_dept.id,
            lead_id=emp_mgr.id,
            start_date=date(2026, 1, 10),
            deadline=date(2026, 12, 31),
            budget=Decimal('120000.00'),
            progress=65,
            priority='High',
            project_status='In-Progress',
            description='Three-tier web application architecture featuring normalized relational database.',
            created_by=admin_user.id
        )
        db.session.add(proj1)
        db.session.flush()

        db.session.add(ProjectMember(project_id=proj1.id, employee_id=emp_dev.id, project_role='Full-Stack Lead', created_by=admin_user.id))

        t1 = Task(
            project_id=proj1.id,
            title='Implement Database Schema with 68 Relational Tables',
            priority='Urgent',
            task_status='Completed',
            estimated_hours=Decimal('35.00'),
            actual_hours=Decimal('32.50'),
            due_date=date.today(),
            completion_percentage=100,
            created_by_emp_id=emp_mgr.id,
            created_by=admin_user.id
        )
        t2 = Task(
            project_id=proj1.id,
            title='Build Audit Trail and Soft-Delete Restoration Center',
            priority='High',
            task_status='In-Progress',
            estimated_hours=Decimal('20.00'),
            actual_hours=Decimal('12.00'),
            due_date=date.today() + timedelta(days=3),
            completion_percentage=60,
            created_by_emp_id=emp_mgr.id,
            created_by=admin_user.id
        )
        db.session.add_all([t1, t2])
        db.session.flush()

        db.session.add(TaskAssignment(task_id=t1.id, employee_id=emp_dev.id, created_by=admin_user.id))
        db.session.add(TaskAssignment(task_id=t2.id, employee_id=emp_dev.id, created_by=admin_user.id))
        db.session.add(TaskComment(task_id=t1.id, user_id=admin_user.id, comment='Schema design validated and verified against university project rubric.', created_by=admin_user.id))

        # Assets
        print("Seeding Office Assets & Inventory...")
        cat_lap = AssetCategory(name='Laptops & Workstations', code='AST-LAP', description='Portable developer computers.', created_by=admin_user.id)
        cat_mon = AssetCategory(name='Monitors & Displays', code='AST-MON', description='High-resolution monitors.', created_by=admin_user.id)
        db.session.add_all([cat_lap, cat_mon])
        db.session.flush()

        asset1 = Asset(
            category_id=cat_lap.id,
            name='MacBook Pro 16" M3 Max',
            asset_tag='AST-MBP-001',
            serial_number='C02G8721MD6T',
            purchase_date=date(2024, 2, 10),
            purchase_cost=Decimal('3499.00'),
            warranty_expiry=date(2027, 2, 10),
            condition='New',
            asset_status='Assigned',
            created_by=admin_user.id
        )
        db.session.add(asset1)
        db.session.flush()

        db.session.add(AssetAssignment(asset_id=asset1.id, employee_id=emp_dev.id, condition_at_assign='New', created_by=admin_user.id))

        # Documents & Communication
        print("Seeding Documents, Announcements, and System Settings...")
        doc_cat = DocumentCategory(name='Company Policies', code='DOC-POL', description='Official organizational handbooks and rules.', created_by=admin_user.id)
        db.session.add(doc_cat)
        db.session.flush()

        db.session.add(Document(
            category_id=doc_cat.id,
            title='Employee Code of Conduct & Ethics Handbook 2026',
            description='Standard operating procedures, workplace conduct, and academic confidentiality guidelines.',
            file_path='uploads/employee_handbook.pdf',
            file_size=2048500,
            file_type='pdf',
            uploaded_by_id=admin_user.id,
            created_by=admin_user.id
        ))

        db.session.add(Announcement(
            title='Welcome to the Office Management System (OMS) v2.0',
            content='We are proud to introduce our modern enterprise platform built with Python Flask, Jinja2, Bootstrap 5, and MySQL. All modules are live.',
            target_audience='All',
            is_pinned=True,
            created_by=admin_user.id
        ))

        db.session.add(Notification(
            user_id=emp_user.id,
            title='Payslip Ready',
            message='Your salary slip for last month has been generated and approved.',
            notification_type='Success',
            created_by=admin_user.id
        ))

        # System Settings
        settings_data = [
            ('company_name', 'TechVision Global Enterprises Inc.', 'Company'),
            ('company_email', 'contact@techvision-global.com', 'Company'),
            ('timezone', 'UTC', 'General'),
            ('currency_symbol', '$', 'Payroll'),
            ('fiscal_year_start', 'January', 'General'),
            ('standard_work_hours_per_day', '8.0', 'Attendance'),
            ('enable_audit_logging', 'True', 'Security')
        ]
        for k, v, c in settings_data:
            db.session.add(SystemSetting(setting_key=k, setting_value=v, category=c, created_by=admin_user.id))

        # Initial Audit Log
        db.session.add(AuditLog(
            user_id=admin_user.id,
            action='SYSTEM_SEED',
            table_name='system',
            record_id=1,
            new_values='{"status": "Database successfully seeded with 68 enterprise models and demo records."}',
            ip_address='127.0.0.1',
            user_agent='System Seeder'
        ))

        db.session.commit()
        print("Database Seeding Completed Successfully! All 68 tables populated.")

if __name__ == '__main__':
    seed_database()
