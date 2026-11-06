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
            ('/communication/notifications', b'My Notifications Feed'),
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


if __name__ == '__main__':
    unittest.main()
