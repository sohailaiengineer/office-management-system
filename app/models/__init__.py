from app.models.mixins import AuditSoftDeleteMixin
from app.models.auth import (
    User, Role, Permission, UserRole, RolePermission,
    UserSession, LoginHistory, PasswordResetToken
)
from app.models.employee import (
    Department, DepartmentLocation, Designation, Employee,
    EmployeeProfile, EmployeeContact, EmployeeAddress,
    EmployeeEducation, EmployeeExperience, EmployeeDocument,
    EmployeeSkill, EmployeeEmergencyContact
)
from app.models.attendance import (
    Shift, ShiftAssignment, Attendance, AttendanceLog, Holiday
)
from app.models.leave import (
    LeaveType, LeaveBalance, LeaveRequest, LeaveApproval, LeaveAttachment
)
from app.models.payroll import (
    SalaryStructure, EmployeeSalary, Payroll, PayrollDetail, Bonus, Deduction
)
from app.models.finance import (
    ExpenseCategory, Expense, ExpenseApproval, Invoice, Payment
)
from app.models.project import (
    Project, ProjectMember, Task, TaskAssignment, TaskComment, TaskAttachment
)
from app.models.client import (
    Client, ClientContact, ClientProject, ClientInteraction
)
from app.models.asset import (
    AssetCategory, Asset, AssetAssignment, AssetMaintenance, AssetRequest
)
from app.models.document import (
    DocumentCategory, Document, DocumentVersion, DocumentShare
)
from app.models.communication import (
    Announcement, Notification, Message, MessageRecipient
)
from app.models.system import (
    AuditLog, SystemSetting, ApprovalWorkflow, ApprovalHistory
)

__all__ = [
    'AuditSoftDeleteMixin',
    # Auth (8)
    'User', 'Role', 'Permission', 'UserRole', 'RolePermission',
    'UserSession', 'LoginHistory', 'PasswordResetToken',
    # Employee (12)
    'Department', 'DepartmentLocation', 'Designation', 'Employee',
    'EmployeeProfile', 'EmployeeContact', 'EmployeeAddress',
    'EmployeeEducation', 'EmployeeExperience', 'EmployeeDocument',
    'EmployeeSkill', 'EmployeeEmergencyContact',
    # Attendance (5)
    'Shift', 'ShiftAssignment', 'Attendance', 'AttendanceLog', 'Holiday',
    # Leave (5)
    'LeaveType', 'LeaveBalance', 'LeaveRequest', 'LeaveApproval', 'LeaveAttachment',
    # Payroll (6)
    'SalaryStructure', 'EmployeeSalary', 'Payroll', 'PayrollDetail', 'Bonus', 'Deduction',
    # Finance (5)
    'ExpenseCategory', 'Expense', 'ExpenseApproval', 'Invoice', 'Payment',
    # Project (6)
    'Project', 'ProjectMember', 'Task', 'TaskAssignment', 'TaskComment', 'TaskAttachment',
    # Client (4)
    'Client', 'ClientContact', 'ClientProject', 'ClientInteraction',
    # Asset (5)
    'AssetCategory', 'Asset', 'AssetAssignment', 'AssetMaintenance', 'AssetRequest',
    # Document (4)
    'DocumentCategory', 'Document', 'DocumentVersion', 'DocumentShare',
    # Communication (4)
    'Announcement', 'Notification', 'Message', 'MessageRecipient',
    # System (4)
    'AuditLog', 'SystemSetting', 'ApprovalWorkflow', 'ApprovalHistory'
]
