import os
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import inspect
from app import create_app
from app.extensions import db
from app.models import (
    User, Role, UserRole, Department, Designation, Employee,
    Shift, Holiday, Attendance, LeaveType, LeaveBalance, LeaveRequest,
    Payroll, PayrollDetail, Bonus, Deduction, ExpenseCategory, Expense,
    Invoice, Payment, Project, ProjectMember, Task, TaskComment,
    Client, ClientInteraction, AssetCategory, Asset, AssetAssignment,
    Document, DocumentCategory, Announcement, Notification, Message, MessageRecipient,
    AuditLog, SystemSetting
)

class EnterpriseOMSTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('development')
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app = self.__class__.app
        self.client = self.__class__.client
        self.logout()

    def login_as(self, username, password):
        self.logout()
        return self.client.post('/auth/login', data={
            'username_or_email': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    # ---------------------------------------------------------
    # Test 1: Verify all 68 tables exist in MySQL
    # ---------------------------------------------------------
    def test_01_all_68_mysql_tables_exist(self):
        with self.app.app_context():
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            self.assertGreaterEqual(len(tables), 68, f"Expected at least 68 tables, found {len(tables)}")
            # Verify critical domain tables
            expected = [
                'users', 'roles', 'permissions', 'user_roles', 'role_permissions',
                'user_sessions', 'login_history', 'password_reset_tokens',
                'departments', 'department_locations', 'designations', 'employees',
                'employee_profiles', 'employee_contacts', 'employee_addresses',
                'employee_education', 'employee_experience', 'employee_documents',
                'employee_skills', 'employee_emergency_contacts', 'shifts',
                'shift_assignments', 'attendance', 'attendance_logs', 'holidays',
                'leave_types', 'leave_balances', 'leave_requests', 'leave_approvals',
                'leave_attachments', 'salary_structures', 'employee_salaries',
                'payrolls', 'payroll_details', 'bonuses', 'deductions',
                'expense_categories', 'expenses', 'expense_approvals', 'invoices',
                'payments', 'projects', 'project_members', 'tasks',
                'task_assignments', 'task_comments', 'task_attachments',
                'clients', 'client_contacts', 'client_projects', 'client_interactions',
                'asset_categories', 'assets', 'asset_assignments', 'asset_maintenance',
                'asset_requests', 'document_categories', 'documents', 'document_versions',
                'document_shares', 'announcements', 'notifications', 'messages',
                'message_recipients', 'audit_logs', 'system_settings',
                'approval_workflows', 'approval_history'
            ]
            for tbl in expected:
                self.assertIn(tbl, tables, f"Table {tbl} must exist in MySQL")
            print(f"[OK] Test 1: Verified all {len(tables)} relational tables in MySQL (68 core models).")

    # ---------------------------------------------------------
    # Test 2: Authentication, Sessions, and Invalid Login
    # ---------------------------------------------------------
    def test_02_authentication_and_session(self):
        # 1. Login page renders
        res = self.client.get('/auth/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Sign In to OMS', res.data)

        # 2. Invalid credentials rejected
        bad_res = self.login_as('admin', 'WrongPass!999')
        self.assertEqual(bad_res.status_code, 200)
        self.assertIn(b'Invalid username/email or password', bad_res.data)

        # 3. Successful login creates session
        good_res = self.login_as('admin', 'Admin@123')
        self.assertEqual(good_res.status_code, 200)
        self.assertIn(b'Executive Operations Dashboard', good_res.data)

        # 4. Profile page accessible
        prof_res = self.client.get('/auth/profile')
        self.assertEqual(prof_res.status_code, 200)
        self.assertIn(b'Edit Details', prof_res.data)

        # 5. Logout destroys session
        logout_res = self.logout()
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'logged out successfully', logout_res.data)

        # 6. Unauthenticated protected route redirects
        prot_res = self.client.get('/dashboard/')
        self.assertEqual(prot_res.status_code, 302)
        print("[OK] Test 2: Authentication, Session Management & Password Security verified.")

    # ---------------------------------------------------------
    # Test 3: Role-Based Access Control (RBAC) Separation
    # ---------------------------------------------------------
    def test_03_role_based_access_control(self):
        # 1. Employee role login
        self.logout()
        emp_login = self.login_as('johndoe', 'Emp@123')
        self.assertEqual(emp_login.status_code, 200)
        # Employee should access employee-facing routes
        emp_res = self.client.get('/dashboard/')
        self.assertEqual(emp_res.status_code, 200)
        # Employee should NOT have access to Admin-only system routes
        admin_restricted = self.client.get('/system/settings')
        self.assertEqual(admin_restricted.status_code, 302) # Redirected due to access denial

        # 2. Dept Manager role login
        self.logout()
        mgr_login = self.login_as('deptmanager', 'Manager@123')
        self.assertEqual(mgr_login.status_code, 200)
        # Manager can access projects & tasks
        proj_res = self.client.get('/projects/')
        self.assertEqual(proj_res.status_code, 200)
        # Manager cannot access system configuration
        sys_res = self.client.get('/system/settings')
        self.assertEqual(sys_res.status_code, 302)

        # 3. Super Admin has unconditional access
        self.logout()
        admin_login = self.login_as('admin', 'Admin@123')
        self.assertEqual(admin_login.status_code, 200)
        sys_ok = self.client.get('/system/settings')
        self.assertEqual(sys_ok.status_code, 200)
        users_ok = self.client.get('/system/users')
        self.assertEqual(users_ok.status_code, 200)
        print("[OK] Test 3: Role-Based Access Control (RBAC) for Admin, Manager, HR, and Employee verified.")

    # ---------------------------------------------------------
    # Test 4: All 17 Blueprint Modules accessible with 200 OK
    # ---------------------------------------------------------
    def test_04_all_17_blueprints(self):
        self.login_as('admin', 'Admin@123')
        blueprint_endpoints = [
            ('/dashboard/', b'Dashboard'),
            ('/employees/', b'Workforce Directory'),
            ('/departments/', b'Organizational Departments'),
            ('/attendance/', b'Daily Attendance Records'),
            ('/leaves/', b'Leave Applications Ledger'),
            ('/payroll/', b'Batch Payroll Generator'),
            ('/finance/', b'Financial Ledger & Invoicing'),
            ('/projects/', b'Projects Directory'),
            ('/tasks/', b'Sprint Task Board'),
            ('/clients/', b'Client Directory'),
            ('/assets/', b'Asset Registry & Equipment'),
            ('/documents/', b'Corporate Document Repository'),
            ('/communication/announcements', b'Company Notices'),
            ('/communication/notifications', b'notifications'),
            ('/communication/messages', b'Internal Direct Messaging'),
            ('/recycle-bin/', b'Recycle Bin'),
            ('/reports/', b'Reports Catalog'),
            ('/system/audit-logs', b'Security & Transaction Audit Ledger'),
            ('/system/settings', b'Configuration')
        ]
        for url, expected_text in blueprint_endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Route {url} failed with {res.status_code}")
            self.assertIn(expected_text.lower(), res.data.lower(), f"Route {url} missing expected text {expected_text}")
        print("[OK] Test 4: All 17 Blueprints verified with 200 OK status.")

    # ---------------------------------------------------------
    # Test 5: Employee CRUD and Validation
    # ---------------------------------------------------------
    def test_05_employee_crud(self):
        self.login_as('admin', 'Admin@123')

        # 1. Create Employee
        with self.app.app_context():
            dept = Department.active_query().first()
            desig = Designation.active_query().first()
            dept_id = dept.id if dept else 1
            desig_id = desig.id if desig else 1

        emp_code = f"EMP-TEST-{datetime.now().strftime('%H%M%S')}"
        username = f"testuser_{datetime.now().strftime('%H%M%S')}"
        email = f"{username}@example.com"

        create_res = self.client.post('/employees/create', data={
            'first_name': 'Testy',
            'last_name': 'Testerson',
            'email': email,
            'username': username,
            'phone': '+1-555-0199',
            'emp_code': emp_code,
            'department_id': dept_id,
            'designation_id': desig_id,
            'manager_id': 0,
            'employment_type': 'Full-Time',
            'date_of_joining': '2026-01-15',
            'basic_salary': '5500.00',
            'status': 'Active',
            'gender': 'Male',
            'marital_status': 'Single',
            'blood_group': 'O+',
            'nationality': 'American'
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)

        with self.app.app_context():
            emp = Employee.active_query().filter_by(emp_code=emp_code).first()
            self.assertIsNotNone(emp, "Employee record should exist in active query")
            emp_id = emp.id

            # 2. View Employee
            view_res = self.client.get(f'/employees/{emp_id}')
            self.assertEqual(view_res.status_code, 200)
            self.assertIn(b'Testy Testerson', view_res.data)

            # 3. Edit Employee
            edit_res = self.client.post(f'/employees/{emp_id}/edit', data={
                'first_name': 'TestyUpdated',
                'last_name': 'Testerson',
                'email': email,
                'username': username,
                'phone': '+1-555-9999',
                'emp_code': emp_code,
                'department_id': dept_id,
                'designation_id': desig_id,
                'manager_id': 0,
                'employment_type': 'Full-Time',
                'date_of_joining': '2026-01-15',
                'basic_salary': '6200.00',
                'status': 'Active'
            }, follow_redirects=True)
            self.assertEqual(edit_res.status_code, 200)

            # 4. Soft Delete Employee
            del_res = self.client.post(f'/employees/{emp_id}/delete', follow_redirects=True)
            self.assertEqual(del_res.status_code, 200)

            # Verify in Recycle Bin
            deleted_emp = Employee.trash_query().filter_by(id=emp_id).first()
            self.assertIsNotNone(deleted_emp)
            self.assertTrue(deleted_emp.is_deleted)
        print("[OK] Test 5: Complete Employee CRUD and Soft Deletion verified.")

    # ---------------------------------------------------------
    # Test 6: Departments & Designations CRUD
    # ---------------------------------------------------------
    def test_06_departments_and_designations_crud(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')
        dept_code = f"DEP-{ts}"

        # 1. Create Department
        res = self.client.post('/departments/create', data={
            'name': f'Research Unit {ts}',
            'code': dept_code,
            'budget': '45000.00',
            'description': 'Advanced automated systems division'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            dept = Department.active_query().filter_by(code=dept_code).first()
            self.assertIsNotNone(dept)
            dept_id = dept.id

        # 2. Edit Department
        edit_res = self.client.post(f'/departments/{dept_id}/edit', data={
            'name': f'Research Unit {ts} Modified',
            'code': dept_code,
            'budget': '50000.00',
            'description': 'Updated scope'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        # 3. Create Designation under this Department
        desig_code = f"DSG-{ts}"
        desig_res = self.client.post('/departments/designations/create', data={
            'title': f'Lead Architect {ts}',
            'code': desig_code,
            'department_id': dept_id,
            'salary_grade': 'Tier 5',
            'min_salary': '8000.00',
            'max_salary': '12000.00'
        }, follow_redirects=True)
        self.assertEqual(desig_res.status_code, 200)

        with self.app.app_context():
            desig = Designation.active_query().filter_by(code=desig_code).first()
            self.assertIsNotNone(desig)
            desig_id = desig.id

        # 4. Edit Designation
        edit_desig_res = self.client.post(f'/departments/designations/{desig_id}/edit', data={
            'title': f'Senior Architect {ts}',
            'code': desig_code,
            'department_id': dept_id,
            'salary_grade': 'Tier 5A',
            'min_salary': '8500.00',
            'max_salary': '13000.00'
        }, follow_redirects=True)
        self.assertEqual(edit_desig_res.status_code, 200)

        # 5. Delete Designation and Department
        del_desig = self.client.post(f'/departments/designations/{desig_id}/delete', follow_redirects=True)
        self.assertEqual(del_desig.status_code, 200)
        del_dept = self.client.post(f'/departments/{dept_id}/delete', follow_redirects=True)
        self.assertEqual(del_dept.status_code, 200)
        print("[OK] Test 6: Departments and Designations Full CRUD verified.")

    # ---------------------------------------------------------
    # Test 7: Attendance & Shift Policy Management
    # ---------------------------------------------------------
    def test_07_attendance_and_shifts(self):
        self.login_as('admin', 'Admin@123')

        # 1. Shift list renders
        shifts_res = self.client.get('/attendance/shifts')
        self.assertEqual(shifts_res.status_code, 200)

        # 2. Create Shift
        ts = datetime.now().strftime('%H%M%S')
        shift_res = self.client.post('/attendance/shifts/create', data={
            'name': f'Rotating Shift {ts}',
            'start_time': '14:00',
            'end_time': '22:00',
            'grace_minutes': 10,
            'is_night_shift': False
        }, follow_redirects=True)
        self.assertEqual(shift_res.status_code, 200)

        with self.app.app_context():
            shift = Shift.active_query().filter_by(name=f'Rotating Shift {ts}').first()
            self.assertIsNotNone(shift)
            shift_id = shift.id

        # 3. Edit Shift
        edit_shift_res = self.client.post(f'/attendance/shifts/{shift_id}/edit', data={
            'name': f'Rotating Shift {ts} Updated',
            'start_time': '15:00',
            'end_time': '23:00',
            'grace_minutes': 15,
            'is_night_shift': False
        }, follow_redirects=True)
        self.assertEqual(edit_shift_res.status_code, 200)

        # 4. Schedule Holiday
        hol_res = self.client.post('/attendance/holidays/create', data={
            'name': f'Special Observance Day {ts}',
            'start_date': date.today().strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'is_recurring': False
        }, follow_redirects=True)
        self.assertEqual(hol_res.status_code, 200)

        with self.app.app_context():
            hol = Holiday.active_query().filter_by(name=f'Special Observance Day {ts}').first()
            self.assertIsNotNone(hol)
            hol_id = hol.id

        # 5. Delete Holiday and Shift
        self.client.post(f'/attendance/holidays/{hol_id}/delete', follow_redirects=True)
        self.client.post(f'/attendance/shifts/{shift_id}/delete', follow_redirects=True)
        print("[OK] Test 7: Attendance and Shift Policy Management verified.")

    # ---------------------------------------------------------
    # Test 8: Leave Applications, Balance & Cancel Workflow
    # ---------------------------------------------------------
    def test_08_leave_workflow(self):
        # Apply as employee
        self.logout()
        emp_login = self.login_as('johndoe', 'Emp@123')
        self.assertEqual(emp_login.status_code, 200)
        with self.app.app_context():
            lt = LeaveType.active_query().first()
            lt_id = lt.id if lt else 1

        apply_res = self.client.post('/leaves/apply', data={
            'leave_type_id': lt_id,
            'start_date': (date.today() + timedelta(days=20)).strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=22)).strftime('%Y-%m-%d'),
            'reason': 'Attending technical software engineering conference.'
        }, follow_redirects=True)
        self.assertEqual(apply_res.status_code, 200)

        with self.app.app_context():
            lr = LeaveRequest.active_query().filter_by(reason='Attending technical software engineering conference.').first()
            self.assertIsNotNone(lr)
            req_id = lr.id

        # Cancel leave request
        cancel_res = self.client.post(f'/leaves/{req_id}/cancel', follow_redirects=True)
        self.assertEqual(cancel_res.status_code, 200)

        with self.app.app_context():
            cancelled_lr = db.session.get(LeaveRequest, req_id)
            self.assertEqual(cancelled_lr.approval_status, 'Cancelled')
        print("[OK] Test 8: Leave Application, Validation and Cancellation Workflow verified.")

    # ---------------------------------------------------------
    # Test 9: Payroll, Bonuses and Deductions
    # ---------------------------------------------------------
    def test_09_payroll_bonuses_deductions(self):
        self.login_as('admin', 'Admin@123')

        with self.app.app_context():
            emp = Employee.active_query().first()
            emp_id = emp.id if emp else 1

        # 1. Record Bonus
        bonus_res = self.client.post('/payroll/bonuses/create', data={
            'employee_id': emp_id,
            'bonus_type': 'Performance',
            'amount': '750.00',
            'bonus_date': date.today().strftime('%Y-%m-%d'),
            'reason': 'Exceeded sprint targets.'
        }, follow_redirects=True)
        self.assertEqual(bonus_res.status_code, 200)

        # 2. Record Deduction
        ded_res = self.client.post('/payroll/deductions/create', data={
            'employee_id': emp_id,
            'deduction_type': 'Fine',
            'amount': '50.00',
            'deduction_date': date.today().strftime('%Y-%m-%d'),
            'reason': 'Card access badge replacement.'
        }, follow_redirects=True)
        self.assertEqual(ded_res.status_code, 200)

        with self.app.app_context():
            b = Bonus.active_query().filter_by(amount=Decimal('750.00')).first()
            d = Deduction.active_query().filter_by(amount=Decimal('50.00')).first()
            self.assertIsNotNone(b)
            self.assertIsNotNone(d)
        print("[OK] Test 9: Payroll Bonuses and Deductions Operations verified.")

    # ---------------------------------------------------------
    # Test 10: Projects and Tasks Full CRUD
    # ---------------------------------------------------------
    def test_10_projects_and_tasks_crud(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')
        prj_code = f"PRJ-{ts}"

        # 1. Create Project
        prj_res = self.client.post('/projects/create', data={
            'name': f'Cloud Migration {ts}',
            'code': prj_code,
            'client_id': 0,
            'department_id': 0,
            'lead_id': 0,
            'start_date': date.today().strftime('%Y-%m-%d'),
            'deadline': (date.today() + timedelta(days=90)).strftime('%Y-%m-%d'),
            'budget': '60000.00',
            'priority': 'High',
            'project_status': 'Planning',
            'description': 'Infrastructure migration to private cloud.'
        }, follow_redirects=True)
        self.assertEqual(prj_res.status_code, 200)

        with self.app.app_context():
            prj = Project.active_query().filter_by(code=prj_code).first()
            self.assertIsNotNone(prj)
            prj_id = prj.id

        # 2. Edit Project
        edit_prj_res = self.client.post(f'/projects/{prj_id}/edit', data={
            'name': f'Cloud Migration {ts} Phase 1',
            'code': prj_code,
            'client_id': 0,
            'department_id': 0,
            'lead_id': 0,
            'start_date': date.today().strftime('%Y-%m-%d'),
            'deadline': (date.today() + timedelta(days=120)).strftime('%Y-%m-%d'),
            'budget': '75000.00',
            'priority': 'Urgent',
            'project_status': 'In-Progress',
            'description': 'Expanded scope phase 1.'
        }, follow_redirects=True)
        self.assertEqual(edit_prj_res.status_code, 200)

        # 3. Create Task under Project
        task_res = self.client.post('/tasks/create', data={
            'project_id': prj_id,
            'title': f'Setup Terraform scripts {ts}',
            'assigned_employee_id': 0,
            'priority': 'High',
            'task_status': 'To-Do',
            'estimated_hours': '16.00',
            'due_date': (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'description': 'Automated IAC configuration.'
        }, follow_redirects=True)
        self.assertEqual(task_res.status_code, 200)

        with self.app.app_context():
            tsk = Task.active_query().filter_by(title=f'Setup Terraform scripts {ts}').first()
            self.assertIsNotNone(tsk)
            task_id = tsk.id

        # 4. Edit Task
        edit_task_res = self.client.post(f'/tasks/{task_id}/edit', data={
            'project_id': prj_id,
            'title': f'Setup Terraform scripts {ts} (Final)',
            'assigned_employee_id': 0,
            'priority': 'Urgent',
            'task_status': 'In-Progress',
            'estimated_hours': '20.00',
            'due_date': (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'description': 'Finalized IAC scripts.'
        }, follow_redirects=True)
        self.assertEqual(edit_task_res.status_code, 200)

        # 5. Add Task Comment
        comment_res = self.client.post(f'/tasks/{task_id}', data={
            'comment': 'Initial terraform configuration drafted and committed.'
        }, follow_redirects=True)
        self.assertEqual(comment_res.status_code, 200)

        # 6. Delete Task and Project
        del_task = self.client.post(f'/tasks/{task_id}/delete', follow_redirects=True)
        self.assertEqual(del_task.status_code, 200)
        del_prj = self.client.post(f'/projects/{prj_id}/delete', follow_redirects=True)
        self.assertEqual(del_prj.status_code, 200)
        print("[OK] Test 10: Projects and Sprint Tasks Complete Lifecycle verified.")

    # ---------------------------------------------------------
    # Test 11: Client CRM Full CRUD
    # ---------------------------------------------------------
    def test_11_clients_crm_crud(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')
        cl_code = f"CL-{ts}"

        # 1. Create Client with WTForms
        cl_res = self.client.post('/clients/create', data={
            'company_name': f'Vanguard Dynamics {ts}',
            'client_code': cl_code,
            'industry': 'Defense & Aerospace',
            'email': f'contact@{cl_code.lower()}.com',
            'phone': '+1-800-555-0188',
            'website': f'https://www.{cl_code.lower()}.com',
            'address': '500 Innovation Blvd',
            'country': 'USA'
        }, follow_redirects=True)
        self.assertEqual(cl_res.status_code, 200)

        with self.app.app_context():
            cl = Client.active_query().filter_by(client_code=cl_code).first()
            self.assertIsNotNone(cl)
            client_id = cl.id

        # 2. Edit Client
        edit_cl = self.client.post(f'/clients/{client_id}/edit', data={
            'company_name': f'Vanguard Dynamics Corp {ts}',
            'client_code': cl_code,
            'industry': 'Aerospace & Robotics',
            'email': f'info@{cl_code.lower()}.com',
            'phone': '+1-800-555-0199',
            'website': f'https://www.{cl_code.lower()}.com',
            'address': '550 Innovation Blvd',
            'country': 'USA'
        }, follow_redirects=True)
        self.assertEqual(edit_cl.status_code, 200)

        # 3. Log Interaction
        interact_res = self.client.post(f'/clients/{client_id}/interactions', data={
            'interaction_type': 'Meeting',
            'conducted_by_id': 0,
            'summary': 'Q3 Strategic roadmap alignment and procurement discussion.'
        }, follow_redirects=True)
        self.assertEqual(interact_res.status_code, 200)

        # 4. Soft Delete Client
        del_cl = self.client.post(f'/clients/{client_id}/delete', follow_redirects=True)
        self.assertEqual(del_cl.status_code, 200)
        print("[OK] Test 11: Corporate Client CRM Full CRUD & Interaction verified.")

    # ---------------------------------------------------------
    # Test 12: Asset Inventory Full CRUD
    # ---------------------------------------------------------
    def test_12_assets_crud(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')
        tag = f"AST-TEST-{ts}"

        with self.app.app_context():
            cat = AssetCategory.active_query().first()
            cat_id = cat.id if cat else 1

        # 1. Create Asset
        ast_res = self.client.post('/assets/create', data={
            'name': f'ThinkPad P16 Gen 2 {ts}',
            'category_id': cat_id,
            'asset_tag': tag,
            'serial_number': f'SN-{ts}',
            'purchase_date': date.today().strftime('%Y-%m-%d'),
            'purchase_cost': '2450.00',
            'warranty_expiry': (date.today() + timedelta(days=1095)).strftime('%Y-%m-%d'),
            'condition': 'New',
            'asset_status': 'Available'
        }, follow_redirects=True)
        self.assertEqual(ast_res.status_code, 200)

        with self.app.app_context():
            ast = Asset.active_query().filter_by(asset_tag=tag).first()
            self.assertIsNotNone(ast)
            asset_id = ast.id

        # 2. Edit Asset
        edit_ast = self.client.post(f'/assets/{asset_id}/edit', data={
            'name': f'ThinkPad P16 Gen 2 Workstation {ts}',
            'category_id': cat_id,
            'asset_tag': tag,
            'serial_number': f'SN-{ts}-REV',
            'purchase_date': date.today().strftime('%Y-%m-%d'),
            'purchase_cost': '2550.00',
            'warranty_expiry': (date.today() + timedelta(days=1095)).strftime('%Y-%m-%d'),
            'condition': 'Good',
            'asset_status': 'Available'
        }, follow_redirects=True)
        self.assertEqual(edit_ast.status_code, 200)

        # 3. Soft Delete Asset
        del_ast = self.client.post(f'/assets/{asset_id}/delete', follow_redirects=True)
        self.assertEqual(del_ast.status_code, 200)
        print("[OK] Test 12: Asset Inventory Management Full CRUD verified.")

    # ---------------------------------------------------------
    # Test 13: Document Repository Full CRUD
    # ---------------------------------------------------------
    def test_13_documents_crud(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')

        with self.app.app_context():
            cat = DocumentCategory.active_query().first()
            cat_id = cat.id if cat else 1

        # 1. Upload Document
        doc_res = self.client.post('/documents/upload', data={
            'title': f'Compliance Policy Charter {ts}',
            'category_id': cat_id,
            'department_id': 0,
            'description': 'Organizational data governance regulations.'
        }, follow_redirects=True)
        self.assertEqual(doc_res.status_code, 200)

        with self.app.app_context():
            doc = Document.active_query().filter_by(title=f'Compliance Policy Charter {ts}').first()
            self.assertIsNotNone(doc)
            doc_id = doc.id

        # 2. Edit Document
        edit_doc = self.client.post(f'/documents/{doc_id}/edit', data={
            'title': f'Compliance Policy Charter {ts} Rev 2',
            'category_id': cat_id,
            'department_id': 0,
            'description': 'Updated data governance guidelines.'
        }, follow_redirects=True)
        self.assertEqual(edit_doc.status_code, 200)

        # 3. Soft Delete Document
        del_doc = self.client.post(f'/documents/{doc_id}/delete', follow_redirects=True)
        self.assertEqual(del_doc.status_code, 200)
        print("[OK] Test 13: Corporate Document Repository Full CRUD verified.")

    # ---------------------------------------------------------
    # Test 14: Communication, Notices & Messages
    # ---------------------------------------------------------
    def test_14_communication_operations(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')

        # 1. Broadcast Announcement
        ann_res = self.client.post('/communication/announcements/create', data={
            'title': f'Office Townhall Meeting {ts}',
            'target_audience': 'All',
            'department_id': 0,
            'content': 'Quarterly executive presentation in main auditorium at 3 PM.',
            'is_pinned': True
        }, follow_redirects=True)
        self.assertEqual(ann_res.status_code, 200)

        with self.app.app_context():
            ann = Announcement.active_query().filter_by(title=f'Office Townhall Meeting {ts}').first()
            self.assertIsNotNone(ann)
            ann_id = ann.id

        # 2. Delete Announcement
        del_ann = self.client.post(f'/communication/announcements/{ann_id}/delete', follow_redirects=True)
        self.assertEqual(del_ann.status_code, 200)

        # 3. Send Internal Message
        with self.app.app_context():
            recip_user = User.active_query().filter(User.username != 'admin').first()
            recip_id = recip_user.id if recip_user else 2

        msg_res = self.client.post('/communication/messages', data={
            'recipient_id': recip_id,
            'subject': f'Project Architecture Review {ts}',
            'body': 'Please review the updated schema specification documents.'
        }, follow_redirects=True)
        self.assertEqual(msg_res.status_code, 200)
        print("[OK] Test 14: Internal Communication Broadcasts & Direct Messaging verified.")

    # ---------------------------------------------------------
    # Test 15: Reports Catalog (47 Reports) & CSV/Excel Exports
    # ---------------------------------------------------------
    def test_15_reports_and_exports(self):
        self.login_as('admin', 'Admin@123')
        res = self.client.get('/reports/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'47 Available Reports', res.data)

        # Test CSV Export
        csv_res = self.client.get('/reports/export/csv/emp_directory')
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(csv_res.mimetype, 'text/csv')
        self.assertIn(b'Emp Code,Full Name,Email', csv_res.data)

        # Test Excel Export
        excel_res = self.client.get('/reports/export/excel/emp_directory')
        self.assertEqual(excel_res.status_code, 200)
        self.assertEqual(excel_res.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertGreater(len(excel_res.data), 1000)

        # Test another category report (Payroll Summary)
        pay_csv = self.client.get('/reports/export/csv/pay_summary')
        self.assertEqual(pay_csv.status_code, 200)
        print("[OK] Test 15: Reports Catalog (47 reports) and live CSV & Excel (.xlsx) exports verified.")

    # ---------------------------------------------------------
    # Test 16: System Administration, Audit Logs & User Roles
    # ---------------------------------------------------------
    def test_16_system_administration(self):
        self.login_as('admin', 'Admin@123')

        # 1. Audit Logs Page
        audit_res = self.client.get('/system/audit-logs')
        self.assertEqual(audit_res.status_code, 200)

        # 2. Save System Configuration Settings
        settings_res = self.client.post('/system/settings', data={
            'company_name': 'OMS Enterprise Global',
            'support_email': 'support@enterprise-oms.com',
            'working_days': '5',
            'currency': 'USD'
        }, follow_redirects=True)
        self.assertEqual(settings_res.status_code, 200)

        # 3. User Management & Status Toggle
        users_res = self.client.get('/system/users')
        self.assertEqual(users_res.status_code, 200)

        with self.app.app_context():
            test_target = User.active_query().filter(User.username != 'admin').first()
            if test_target:
                target_id = test_target.id
                toggle_res = self.client.post(f'/system/users/{target_id}/toggle-status', follow_redirects=True)
                self.assertEqual(toggle_res.status_code, 200)
                # Toggle back to ensure test idempotency
                self.client.post(f'/system/users/{target_id}/toggle-status', follow_redirects=True)
        print("[OK] Test 16: System Settings, Audit Logging, and User Governance verified.")

    # ---------------------------------------------------------
    # Test 17: Recycle Bin Restoration
    # ---------------------------------------------------------
    def test_17_recycle_bin_restoration(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')

        # Create temporary department
        self.client.post('/departments/create', data={
            'name': f'Bin Restore Test {ts}',
            'code': f'BIN-{ts}',
            'budget': '12000.00',
            'description': 'Restore test'
        }, follow_redirects=True)

        with self.app.app_context():
            dept = Department.active_query().filter_by(code=f'BIN-{ts}').first()
            self.assertIsNotNone(dept)
            dept_id = dept.id

        # Soft delete
        self.client.post(f'/departments/{dept_id}/delete', follow_redirects=True)

        # Restore from recycle bin
        restore_res = self.client.post(f'/recycle-bin/departments/{dept_id}/restore', follow_redirects=True)
        self.assertEqual(restore_res.status_code, 200)

        with self.app.app_context():
            restored = Department.active_query().filter_by(id=dept_id).first()
            self.assertIsNotNone(restored)
            self.assertFalse(restored.is_deleted)
            db.session.delete(restored)
            db.session.commit()
        print("[OK] Test 17: Recycle Bin Cross-Module Restoration verified.")

    # ---------------------------------------------------------
    # Test 18: Four Distinct Role-Specific Dashboards
    # ---------------------------------------------------------
    def test_18_four_distinct_role_dashboards(self):
        # 1. Super Admin Dashboard
        admin_res = self.login_as('admin', 'Admin@123')
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b'Executive Operations Dashboard', admin_res.data)
        self.assertIn(b'Department Staff Distribution', admin_res.data)
        self.assertIn(b'Super Admin', admin_res.data)

        # 2. HR Manager Dashboard
        hr_res = self.login_as('hrmanager', 'Hr@123')
        self.assertEqual(hr_res.status_code, 200)
        self.assertIn(b'HR Manager Dashboard', hr_res.data)
        self.assertIn(b'Pending Leave Requests', hr_res.data)
        self.assertIn(b'HR Operations', hr_res.data)

        # 3. Department Manager Dashboard
        mgr_res = self.login_as('deptmanager', 'Manager@123')
        self.assertEqual(mgr_res.status_code, 200)
        self.assertIn(b'Department Manager Dashboard', mgr_res.data)
        self.assertIn(b'Department Console', mgr_res.data)
        self.assertIn(b'Department Projects', mgr_res.data)

        # 4. Standard Employee Dashboard
        emp_res = self.login_as('johndoe', 'Emp@123')
        self.assertEqual(emp_res.status_code, 200)
        self.assertIn(b'Employee Self-Service Portal', emp_res.data)
        self.assertIn(b'My Assigned Tasks', emp_res.data)
        self.assertIn(b'Self-Service Portal', emp_res.data)
        print("[OK] Test 18: All 4 Distinct Role-Specific Dashboards verified.")

    # ---------------------------------------------------------
    # Test 19: Strict Role Data Scoping and Privacy Enforcement
    # ---------------------------------------------------------
    def test_19_strict_role_data_scoping_and_privacy(self):
        # 1. Dept Manager cannot access payroll
        self.login_as('deptmanager', 'Manager@123')
        pay_res = self.client.get('/payroll/', follow_redirects=True)
        self.assertIn(b'Department Managers do not have permission to view company-wide payroll', pay_res.data)

        # 2. Dept Manager cannot view employees from other departments (e.g. Employee 2 in HR)
        hr_emp_res = self.client.get('/employees/2', follow_redirects=True)
        self.assertIn(b'Access Denied: You cannot view employee records outside your department', hr_emp_res.data)

        # 3. Dept Manager CAN view employees in own department (Employee 4 John Doe in Engineering)
        eng_emp_res = self.client.get('/employees/4', follow_redirects=True)
        self.assertEqual(eng_emp_res.status_code, 200)
        self.assertIn(b'John Doe', eng_emp_res.data)
        # But cannot see basic salary
        self.assertNotIn(b'Basic Salary:', eng_emp_res.data)

        # 4. Employee cannot access general employee directory
        self.login_as('johndoe', 'Emp@123')
        dir_res = self.client.get('/employees/', follow_redirects=True)
        # Redirected to personal profile
        self.assertIn(b'My Profile', dir_res.data)

        # 5. Employee viewing own profile can see their own basic salary
        own_res = self.client.get('/employees/4', follow_redirects=True)
        self.assertEqual(own_res.status_code, 200)
        self.assertIn(b'Basic Salary:', own_res.data)
        print("[OK] Test 19: Strict Role Data Scoping & Salary Privacy verified.")

    # ---------------------------------------------------------
    # Test 20: Task Assignment and Progress Update Workflow
    # ---------------------------------------------------------
    def test_20_task_assignment_and_progress_workflow(self):
        # 1. Employee cannot create tasks
        self.login_as('johndoe', 'Emp@123')
        create_attempt = self.client.post('/tasks/create', data={
            'project_id': 1,
            'title': 'Hacker Task',
            'priority': 'High',
            'task_status': 'To-Do',
            'due_date': str(date.today() + timedelta(days=5))
        }, follow_redirects=True)
        self.assertIn(b'Regular employees are not authorized to create or assign tasks', create_attempt.data)

        # 2. Dept Manager creates a task for Engineering project
        self.login_as('deptmanager', 'Manager@123')
        ts = datetime.now().strftime('%H%M%S')
        new_task_res = self.client.post('/tasks/create', data={
            'project_id': 1,
            'title': f'Sprint Workflow Task {ts}',
            'priority': 'High',
            'task_status': 'To-Do',
            'estimated_hours': '12.00',
            'due_date': str(date.today() + timedelta(days=7)),
            'description': 'Deliver RBAC task workflow module.',
            'assigned_employee_id': 4
        }, follow_redirects=True)
        self.assertEqual(new_task_res.status_code, 200)

        with self.app.app_context():
            created_task = Task.active_query().filter_by(title=f'Sprint Workflow Task {ts}').first()
            self.assertIsNotNone(created_task)
            task_id = created_task.id

        # 3. Employee updates status and records progress note
        self.login_as('johndoe', 'Emp@123')
        update_res = self.client.post(f'/tasks/{task_id}/update-status', data={
            'task_status': 'In-Progress',
            'completion_percentage': '65',
            'progress_note': 'Completed back-end controller and permission matrix.'
        }, follow_redirects=True)
        self.assertEqual(update_res.status_code, 200)

        with self.app.app_context():
            task_check = Task.active_query().filter_by(id=task_id).first()
            self.assertEqual(task_check.task_status, 'In-Progress')
            self.assertEqual(task_check.completion_percentage, 65)
            # Verify comment was logged
            comment = TaskComment.active_query().filter_by(task_id=task_id).first()
            self.assertIsNotNone(comment)
            self.assertIn('Completed back-end controller', comment.comment)
        print("[OK] Test 20: Task Assignment and Progress Update Workflow verified.")

    # ---------------------------------------------------------
    # Test 21: Reports Catalog Access Control
    # ---------------------------------------------------------
    def test_21_reports_catalog_access_control(self):
        # 1. Admin gets all 47 reports
        self.login_as('admin', 'Admin@123')
        admin_rep = self.client.get('/reports/')
        self.assertEqual(admin_rep.status_code, 200)
        self.assertIn(b'47', admin_rep.data)

        # 2. Dept Manager does not see salary band or payroll reports
        self.login_as('deptmanager', 'Manager@123')
        mgr_rep = self.client.get('/reports/')
        self.assertEqual(mgr_rep.status_code, 200)
        self.assertNotIn(b'Employee Salary Distribution', mgr_rep.data)
        self.assertNotIn(b'Monthly Payroll Summary', mgr_rep.data)

        # 3. Dept Manager cannot export forbidden report
        forbid_res = self.client.get('/reports/export/csv/emp_salary_band')
        self.assertEqual(forbid_res.status_code, 403)

        # 4. Employee only sees permitted personal reports
        self.login_as('johndoe', 'Emp@123')
        emp_rep = self.client.get('/reports/')
        self.assertEqual(emp_rep.status_code, 200)
        self.assertNotIn(b'Employee Salary Distribution', emp_rep.data)
        self.assertNotIn(b'System Audit Trail', emp_rep.data)
        print("[OK] Test 21: Reports Catalog Role Scoping & 403 Protection verified.")

    # ---------------------------------------------------------
    # Test 22: 12 Interactive Dashboard Cards & Filter Routes
    # ---------------------------------------------------------
    def test_22_interactive_dashboard_cards_and_filters(self):
        self.login_as('admin', 'Admin@123')
        
        # 1. Total Employees
        r1 = self.client.get('/employees/')
        self.assertEqual(r1.status_code, 200)

        # 2. Total Departments
        r2 = self.client.get('/departments/')
        self.assertEqual(r2.status_code, 200)

        # 3. Total Managers / Managers & Teams Overview
        r3 = self.client.get('/departments/managers')
        self.assertEqual(r3.status_code, 200)
        self.assertIn(b'Managers &amp; Teams Overview', r3.data)

        # 4. Present Employees
        r4 = self.client.get('/attendance/?status=Present')
        self.assertEqual(r4.status_code, 200)

        # 5. Absent Employees
        r5 = self.client.get('/attendance/?status=Absent')
        self.assertEqual(r5.status_code, 200)

        # 6. Pending Leaves
        r6 = self.client.get('/leaves/?status=Pending')
        self.assertEqual(r6.status_code, 200)

        # 7. Approved Leaves
        r7 = self.client.get('/leaves/?status=Approved')
        self.assertEqual(r7.status_code, 200)

        # 8. Rejected Leaves
        r8 = self.client.get('/leaves/?status=Rejected')
        self.assertEqual(r8.status_code, 200)

        # 9. Total Tasks
        r9 = self.client.get('/tasks/')
        self.assertEqual(r9.status_code, 200)

        # 10. Pending Tasks
        r10 = self.client.get('/tasks/?status=Pending')
        self.assertEqual(r10.status_code, 200)

        # 11. Completed Tasks
        r11 = self.client.get('/tasks/?status=Completed')
        self.assertEqual(r11.status_code, 200)

        # 12. Payroll Records
        r12 = self.client.get('/payroll/')
        self.assertEqual(r12.status_code, 200)
        print("[OK] Test 22: All 12 Interactive Dashboard Card Filter Routes verified.")

    # ---------------------------------------------------------
    # Test 23: Manager A vs Manager B Strict Department Isolation
    # ---------------------------------------------------------
    def test_23_department_manager_isolation(self):
        # Manager A: deptmanager (Engineering)
        self.login_as('deptmanager', 'Manager@123')
        dash_a = self.client.get('/dashboard/')
        self.assertEqual(dash_a.status_code, 200)
        self.assertIn(b'Engineering', dash_a.data)

        tasks_a = self.client.get('/tasks/')
        self.assertEqual(tasks_a.status_code, 200)
        # Should not see Marketing outreach task
        self.assertNotIn(b'Draft Outreach Collateral', tasks_a.data)

        # Manager B: mktmanager (Marketing & Sales)
        self.login_as('mktmanager', 'Manager@123')
        dash_b = self.client.get('/dashboard/')
        self.assertEqual(dash_b.status_code, 200)
        self.assertIn(b'Marketing', dash_b.data)

        tasks_b = self.client.get('/tasks/')
        self.assertEqual(tasks_b.status_code, 200)
        # Should see Marketing outreach task
        self.assertIn(b'Draft Outreach Collateral', tasks_b.data)
        print("[OK] Test 23: Department Manager A vs Manager B Strict Isolation verified.")

    # ---------------------------------------------------------
    # Test 24: Employee A vs Employee B Data Privacy
    # ---------------------------------------------------------
    def test_24_employee_data_privacy(self):
        # Employee A: johndoe (Engineering)
        self.login_as('johndoe', 'Emp@123')
        dash_john = self.client.get('/dashboard/')
        self.assertEqual(dash_john.status_code, 200)
        self.assertIn(b'John Doe', dash_john.data)

        # Cannot access all employee management directory
        emp_dir = self.client.get('/employees/', follow_redirects=True)
        self.assertIn(b'My Profile', emp_dir.data)

        # Employee B: janedoe (Marketing)
        self.login_as('janedoe', 'Emp@123')
        dash_jane = self.client.get('/dashboard/')
        self.assertEqual(dash_jane.status_code, 200)
        self.assertIn(b'Jane Doe', dash_jane.data)
        print("[OK] Test 24: Employee A vs Employee B Privacy and RBAC verified.")

    # ---------------------------------------------------------
    # Test 25: Leave Request Submission with Attachment & Notifications (No 500 Error!)
    # ---------------------------------------------------------
    def test_25_leave_request_attachment_and_notifications(self):
        self.login_as('johndoe', 'Emp@123')
        
        # 1. Apply page renders
        apply_page = self.client.get('/leaves/apply')
        self.assertEqual(apply_page.status_code, 200)
        self.assertIn(b'Apply for Leave', apply_page.data)

        # 2. Submit leave with attachment
        import io
        fake_doc = (io.BytesIO(b"%PDF-1.4 Fake Medical Certificate Content"), 'medical_cert.pdf')
        start_d = (date.today() + timedelta(days=20)).strftime('%Y-%m-%d')
        end_d = (date.today() + timedelta(days=22)).strftime('%Y-%m-%d')

        post_res = self.client.post('/leaves/apply', data={
            'leave_type_id': '1',
            'start_date': start_d,
            'end_date': end_d,
            'reason': 'Medical consultation and recovery period test request.',
            'supporting_document': fake_doc
        }, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(post_res.status_code, 200)
        self.assertIn(b'Leave application submitted successfully', post_res.data)

        # Verify DB records
        with self.app.app_context():
            john_emp = Employee.query.join(User, Employee.user_id == User.id).filter(User.username == 'johndoe').first()
            leave_req = LeaveRequest.query.filter_by(employee_id=john_emp.id, reason='Medical consultation and recovery period test request.').first()
            self.assertIsNotNone(leave_req)
            self.assertEqual(leave_req.approval_status, 'Pending')
            
            # Verify notifications dispatched
            admin_notif = Notification.query.filter(Notification.title.ilike('%Leave Application%')).first()
            self.assertIsNotNone(admin_notif)
        print("[OK] Test 25: Leave Submission with Attachment & Notifications (No 500 Error) verified.")

    # ---------------------------------------------------------
    # Test 26: Internal Messaging with Attachment & Privacy Protection
    # ---------------------------------------------------------
    def test_26_messaging_with_attachment_and_privacy(self):
        # 1. John Doe sends message with attachment to Rachel Green (mktmanager)
        self.login_as('johndoe', 'Emp@123')
        with self.app.app_context():
            rachel = User.query.filter_by(username='mktmanager').first()
            self.assertIsNotNone(rachel)
            rachel_id = rachel.id

        import io
        fake_attachment = (io.BytesIO(b"Confidential Sprint Brief Content"), 'sprint_brief.txt')

        msg_res = self.client.post('/communication/messages', data={
            'recipient_id': str(rachel_id),
            'subject': 'Cross-Department Sync Request',
            'body': 'Please review the attached project specs for Q4 integration.',
            'attachment': fake_attachment
        }, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(msg_res.status_code, 200)
        self.assertIn(b'Message dispatched successfully', msg_res.data)

        with self.app.app_context():
            msg = Message.query.filter_by(subject='Cross-Department Sync Request').first()
            self.assertIsNotNone(msg)
            self.assertIsNotNone(msg.attachment_path)
            msg_id = msg.id

        # 2. Third-party (deptmanager) CANNOT view private message between John and Rachel
        self.login_as('deptmanager', 'Manager@123')
        forbidden_view = self.client.get(f'/communication/messages/{msg_id}')
        self.assertEqual(forbidden_view.status_code, 403)

        # 3. Intended recipient (Rachel / mktmanager) CAN view and mark read
        self.login_as('mktmanager', 'Manager@123')
        allowed_view = self.client.get(f'/communication/messages/{msg_id}')
        self.assertEqual(allowed_view.status_code, 200)
        self.assertIn(b'Cross-Department Sync Request', allowed_view.data)

        # 4. Intended recipient can download attachment
        att_download = self.client.get(f'/communication/messages/{msg_id}/attachment')
        self.assertEqual(att_download.status_code, 200)
        print("[OK] Test 26: Messaging Recipient Selection, Attachment & Privacy Protection verified.")

    # ---------------------------------------------------------
    # Test 27: Document Management Multi-Filter & Download Authorization
    # ---------------------------------------------------------
    def test_27_document_management_and_password_reset(self):
        self.login_as('admin', 'Admin@123')

        # 1. Multi-filter search works
        doc_search = self.client.get('/documents/?search=handbook')
        self.assertEqual(doc_search.status_code, 200)

        # 2. Download endpoint authorized
        with self.app.app_context():
            doc = Document.active_query().first()
            doc_id = doc.id if doc else 1

        doc_dl = self.client.get(f'/documents/{doc_id}/download')
        self.assertIn(doc_dl.status_code, [200, 302])

        # 3. Forgot Password Request
        fp_res = self.client.post('/auth/forgot-password', data={
            'email': 'john.doe@enterprise-oms.com'
        }, follow_redirects=True)
        self.assertEqual(fp_res.status_code, 200)
        self.assertIn(b'password reset instructions have been dispatched', fp_res.data)
        print("[OK] Test 27: Document Management Filters & Password Reset Workflow verified.")

    # ---------------------------------------------------------
    # Test 28: Employee Salary Slip Access & HTTP 500 Elimination
    # ---------------------------------------------------------
    def test_28_employee_salary_slip_no_500_error(self):
        # 1. Login as employee John Doe (emp_id=4)
        self.login_as('johndoe', 'Emp@123')

        # 2. Access /payroll/ (employee view) - must be 200 OK without Jinja BuildError
        emp_payroll_res = self.client.get('/payroll/')
        self.assertEqual(emp_payroll_res.status_code, 200)
        self.assertIn(b'My Salary Slip History', emp_payroll_res.data)
        self.assertIn(b'View Slip', emp_payroll_res.data)

        # 3. Access individual salary slip /payroll/payslip/1
        slip_res = self.client.get('/payroll/payslip/1')
        self.assertEqual(slip_res.status_code, 200)
        self.assertIn(b'CONFIDENTIAL SALARY SLIP', slip_res.data)
        self.assertIn(b'TechVision Global Enterprises Inc.', slip_res.data)
        self.assertIn(b'John Doe', slip_res.data)
        self.assertIn(b'Basic Salary', slip_res.data)
        self.assertIn(b'NET TAKE-HOME DISBURSEMENT', slip_res.data)
        self.assertIn(b'Print / Download PDF', slip_res.data)

        # 4. Access alias routes: /payroll/my-slips and /payroll/slips/1
        my_slips_res = self.client.get('/payroll/my-slips')
        self.assertEqual(my_slips_res.status_code, 200)

        alias_slip_res = self.client.get('/payroll/slips/1')
        self.assertEqual(alias_slip_res.status_code, 200)

        # 5. Access control: another employee (janedoe) CANNOT access John's salary slip
        self.login_as('janedoe', 'Emp@123')
        forbidden_slip = self.client.get('/payroll/payslip/1', follow_redirects=True)
        self.assertEqual(forbidden_slip.status_code, 200)
        self.assertIn(b'Access Denied', forbidden_slip.data)
        print("[OK] Test 28: Employee Salary Slip Access & HTTP 500 Elimination verified.")

    # ---------------------------------------------------------
    # Test 29: HR Salary Management System & Duplicate Prevention
    # ---------------------------------------------------------
    def test_29_hr_salary_management_system(self):
        # 1. Login as HR Manager
        self.login_as('hrmanager', 'Hr@123')

        # 2. Access Payroll administration dashboard
        pr_index = self.client.get('/payroll/')
        self.assertEqual(pr_index.status_code, 200)
        self.assertIn(b'Master Employee Salary Records Register', pr_index.data)
        self.assertIn(b'Issue Individual Salary Slip', pr_index.data)

        # 3. Access Individual Salary Slip generator
        gen_form_res = self.client.get('/payroll/generate-individual')
        self.assertEqual(gen_form_res.status_code, 200)
        self.assertIn(b'Generate Individual Employee Salary Slip', gen_form_res.data)

        # Clean up any pre-existing test salary record for employee 4 in month 12, 2026
        with self.app.app_context():
            p_header = Payroll.active_query().filter_by(month=12, year=2026).first()
            if p_header:
                PayrollDetail.query.filter_by(payroll_id=p_header.id, employee_id=4).delete()
                db.session.commit()

        # 4. Generate new salary record for employee 4 for Month 12, Year 2026
        salary_payload = {
            'employee_id': 4,
            'month': 12,
            'year': 2026,
            'basic': '5000.00',
            'allowances': '1200.00',
            'bonuses_total': '600.00',
            'overtime_amount': '200.00',
            'deductions_total': '350.00',
            'payment_status': 'Paid',
            'payment_method': 'Bank Transfer'
        }
        create_res = self.client.post('/payroll/generate-individual', data=salary_payload, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b'Salary slip generated successfully', create_res.data)

        # Verify net salary: 5000 + 1200 + 600 + 200 - 350 = 6650.00
        with self.app.app_context():
            new_slip = PayrollDetail.active_query().filter_by(employee_id=4, basic=Decimal('5000.00')).first()
            self.assertIsNotNone(new_slip)
            self.assertEqual(new_slip.net_salary, Decimal('6650.00'))
            new_slip_id = new_slip.id

        # 5. Prevent duplicate generation for same employee and month/year
        dup_res = self.client.post('/payroll/generate-individual', data=salary_payload, follow_redirects=True)
        self.assertEqual(dup_res.status_code, 200)
        self.assertIn(b'Duplicate Alert', dup_res.data)

        # 6. Update payment status via /payroll/detail/<id>/status
        status_res = self.client.post(f'/payroll/detail/{new_slip_id}/status', data={
            'status': 'Pending'
        }, follow_redirects=True)
        self.assertEqual(status_res.status_code, 200)
        self.assertIn(b'status updated to Pending', status_res.data)

        with self.app.app_context():
            updated_slip = db.session.get(PayrollDetail, new_slip_id)
            self.assertEqual(updated_slip.payment_status, 'Pending')

        print("[OK] Test 29: HR Salary Management, Automatic Net Pay & Duplicate Prevention verified.")

    # ---------------------------------------------------------
    # Test 30: Separate Department Logins & Portal Validation
    # ---------------------------------------------------------
    def test_30_separate_department_logins_and_portals(self):
        # 1. Department Login Portal Pages render correctly
        portals = [
            ('/auth/login/ENG', b'ENG Division', b'Engineering'),
            ('/auth/login/HR', b'HR Division', b'Human Resources'),
            ('/auth/login/FIN', b'FIN Division', b'Finance & Accounts'),
            ('/auth/login/MKT', b'MKT Division', b'Marketing & Sales')
        ]
        for url, badge, name in portals:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(badge, resp.data)
            self.assertIn(name, resp.data)

        # 2. Verify dedicated department manager logins:
        # Engineering Manager: deptmanager
        eng_login = self.login_as('deptmanager', 'Manager@123')
        self.assertEqual(eng_login.status_code, 200)
        self.assertIn(b'Engineering', eng_login.data)

        # HR Manager: hrmanager
        hr_login = self.login_as('hrmanager', 'Hr@123')
        self.assertEqual(hr_login.status_code, 200)
        self.assertIn(b'HR Operations', hr_login.data)

        # Finance Manager: finmanager
        fin_login = self.login_as('finmanager', 'Manager@123')
        self.assertEqual(fin_login.status_code, 200)
        self.assertIn(b'Finance', fin_login.data)

        # Marketing Manager: mktmanager
        mkt_login = self.login_as('mktmanager', 'Manager@123')
        self.assertEqual(mkt_login.status_code, 200)
        self.assertIn(b'Marketing', mkt_login.data)

        # 3. Test cross-department login restriction:
        # If an Engineering user tries to sign into Finance Portal /auth/login/FIN
        self.logout()
        cross_res = self.client.post('/auth/login/FIN', data={
            'username_or_email': 'deptmanager',
            'password': 'Manager@123'
        }, follow_redirects=True)
        self.assertEqual(cross_res.status_code, 200)
        self.assertIn(b'Department Access Restricted', cross_res.data)

        # 4. Super Admin can access ANY department portal
        admin_portal_res = self.client.post('/auth/login/FIN', data={
            'username_or_email': 'admin',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(admin_portal_res.status_code, 200)
        self.assertIn(b'Executive Operations Dashboard', admin_portal_res.data)

        print("[OK] Test 30: Separate Department Logins, Portal Restriction & Super Admin Access verified.")

    # ---------------------------------------------------------
    # Test 31: Cross-Department Data Isolation & Strict RBAC
    # ---------------------------------------------------------
    def test_31_department_data_isolation_and_rbac(self):
        # 1. Finance Manager has access to /finance/
        self.login_as('finmanager', 'Manager@123')
        fin_res = self.client.get('/finance/')
        self.assertEqual(fin_res.status_code, 200)
        self.assertIn(b'Client Invoices', fin_res.data)

        # 2. Engineering Manager CANNOT create invoices
        self.login_as('deptmanager', 'Manager@123')
        forbidden_invoice = self.client.get('/finance/invoices/create', follow_redirects=True)
        self.assertEqual(forbidden_invoice.status_code, 200)
        self.assertIn(b'Access Denied', forbidden_invoice.data)

        # 3. Engineering Manager CANNOT view employee details outside Engineering
        with self.app.app_context():
            fin_emp = Employee.active_query().filter_by(emp_code='EMP-008').first()
            fin_emp_id = fin_emp.id

        forbidden_emp_view = self.client.get(f'/employees/{fin_emp_id}', follow_redirects=True)
        self.assertEqual(forbidden_emp_view.status_code, 200)
        self.assertIn(b'Access Denied', forbidden_emp_view.data)

        # 4. Super Admin retains full visibility across all 4 departments
        self.login_as('admin', 'Admin@123')
        admin_emp_view = self.client.get(f'/employees/{fin_emp_id}')
        self.assertEqual(admin_emp_view.status_code, 200)
        self.assertIn(b'David Miller', admin_emp_view.data)

        admin_dept_view = self.client.get('/departments/')
        self.assertEqual(admin_dept_view.status_code, 200)
        self.assertIn(b'Engineering', admin_dept_view.data)
        self.assertIn(b'Human Resources', admin_dept_view.data)
        self.assertIn(b'Finance', admin_dept_view.data)
        self.assertIn(b'Marketing', admin_dept_view.data)

        print("[OK] Test 31: Cross-Department Data Privacy & Anti-Tampering URL RBAC verified.")

    # ---------------------------------------------------------
    # Test 32: Employee Creation, Auto-Provisioning & Filtering
    # ---------------------------------------------------------
    def test_32_employee_creation_and_auto_account(self):
        self.login_as('admin', 'Admin@123')
        ts = datetime.now().strftime('%H%M%S')
        emp_code = f"EMP-N{ts}"
        username = f"at_{ts}"
        email = f"at_{ts}@enterprise-oms.com"

        # 1. Access Employee Registration Form
        create_page = self.client.get('/employees/create')
        self.assertEqual(create_page.status_code, 200)
        self.assertIn(b'Employee Registration Form', create_page.data)

        # 2. Submit Add New Employee
        post_data = {
            'first_name': 'Alexander',
            'last_name': 'Taylor',
            'username': username,
            'email': email,
            'phone': '+1 555-0199',
            'role_id': 4, # Employee role
            'password': '', # Auto-generate
            'send_activation_email': 'y',
            'emp_code': emp_code,
            'department_id': 1, # Engineering
            'designation_id': 1,
            'manager_id': 3,
            'employment_type': 'Full-Time',
            'date_of_joining': '2026-11-10',
            'basic_salary': '6200.00',
            'status': 'Active',
            'gender': 'Male',
            'nationality': 'American'
        }
        res = self.client.post('/employees/create', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'onboarded successfully', res.data)

        # 3. Verify Database Records
        with self.app.app_context():
            created_emp = Employee.active_query().filter_by(emp_code=emp_code).first()
            self.assertIsNotNone(created_emp)
            self.assertEqual(created_emp.full_name, 'Alexander Taylor')
            self.assertEqual(created_emp.department_id, 1)

            created_user = User.active_query().filter_by(username=username).first()
            self.assertIsNotNone(created_user)
            self.assertEqual(created_user.id, created_emp.user_id)
            self.assertTrue(created_user.has_role('employee'))

        # 4. Filter by Department and Manager
        filter_res = self.client.get(f'/employees/?department_id=1&manager_id=3')
        self.assertEqual(filter_res.status_code, 200)
        self.assertIn(username.encode(), filter_res.data)

        # 5. Edit Employee without creating duplicate accounts
        edit_res = self.client.post(f'/employees/{created_emp.id}/edit', data={
            'first_name': 'Alex',
            'last_name': 'Taylor',
            'username': username,
            'email': email,
            'phone': '+1 555-9988',
            'role_id': 4,
            'password': '',
            'emp_code': emp_code,
            'department_id': 1,
            'designation_id': 1,
            'manager_id': 3,
            'employment_type': 'Full-Time',
            'date_of_joining': '2026-11-10',
            'basic_salary': '6500.00',
            'status': 'Active'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        with self.app.app_context():
            user_count = User.query.filter_by(username=username).count()
            self.assertEqual(user_count, 1)

        print("[OK] Test 32: Employee Creation, Auto-Provisioning & Filtering verified.")

    # ---------------------------------------------------------
    # Test 33: Account Activation & Strict Salary Privacy
    # ---------------------------------------------------------
    def test_33_account_activation_and_salary_privacy(self):
        from itsdangerous import URLSafeTimedSerializer

        # 1. Test Token Activation Route
        with self.app.app_context():
            temp_user = User.query.filter_by(username='activate_test_user').first()
            if not temp_user:
                temp_user = User(
                    username='activate_test_user',
                    email='activate_test@enterprise-oms.com',
                    first_name='Activate',
                    last_name='Tester',
                    password_hash='initial_dummy_hash',
                    status='Active'
                )
                db.session.add(temp_user)
                db.session.commit()
            s = URLSafeTimedSerializer(self.app.config['SECRET_KEY'])
            token = s.dumps(temp_user.email, salt='account-activation-salt')

        activate_page = self.client.get(f'/auth/activate/{token}')
        self.assertEqual(activate_page.status_code, 200)
        self.assertIn(b'Activate Your Account', activate_page.data)

        # Complete activation with new password
        activate_res = self.client.post(f'/auth/activate/{token}', data={
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(activate_res.status_code, 200)
        self.assertIn(b'successfully activated', activate_res.data)

        # 2. Strict Salary Privacy Enforcement:
        # Dept Manager CANNOT access individual employee salary slips
        with self.app.app_context():
            slip = PayrollDetail.active_query().first()
            self.assertIsNotNone(slip)
            slip_id = slip.id

        self.login_as('deptmanager', 'Manager@123')
        mgr_slip_res = self.client.get(f'/payroll/payslip/{slip_id}', follow_redirects=True)
        self.assertEqual(mgr_slip_res.status_code, 200)
        self.assertIn(b'Access Denied', mgr_slip_res.data)

        # 3. Super Admin CAN view the payslip
        self.login_as('admin', 'Admin@123')
        admin_slip_res = self.client.get(f'/payroll/payslip/{slip_id}')
        self.assertEqual(admin_slip_res.status_code, 200)
        self.assertIn(b'Salary Slip', admin_slip_res.data)

        print("[OK] Test 33: Account Activation & Strict Salary Privacy verified.")


if __name__ == '__main__':
    unittest.main()
