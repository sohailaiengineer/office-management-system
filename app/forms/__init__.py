from app.forms.auth_forms import LoginForm, UserProfileForm, ChangePasswordForm, CreateUserForm
from app.forms.employee_forms import EmployeeForm, DepartmentForm, DesignationForm
from app.forms.attendance_forms import ShiftForm, HolidayForm
from app.forms.leave_forms import LeaveRequestForm, LeaveTypeForm, LeaveApprovalForm
from app.forms.payroll_forms import ProcessPayrollForm, BonusForm, DeductionForm
from app.forms.finance_forms import ExpenseForm, InvoiceForm
from app.forms.project_forms import ProjectForm, TaskForm, TaskCommentForm
from app.forms.asset_forms import AssetForm, AssetAssignmentForm, AssetRequestForm
from app.forms.client_forms import ClientForm, ClientInteractionForm
from app.forms.document_forms import DocumentUploadForm, DocumentCategoryForm
from app.forms.communication_forms import AnnouncementForm, DirectMessageForm

__all__ = [
    'LoginForm', 'UserProfileForm', 'ChangePasswordForm', 'CreateUserForm',
    'EmployeeForm', 'DepartmentForm', 'DesignationForm',
    'ShiftForm', 'HolidayForm',
    'LeaveRequestForm', 'LeaveTypeForm', 'LeaveApprovalForm',
    'ProcessPayrollForm', 'BonusForm', 'DeductionForm',
    'ExpenseForm', 'InvoiceForm',
    'ProjectForm', 'TaskForm', 'TaskCommentForm',
    'AssetForm', 'AssetAssignmentForm', 'AssetRequestForm',
    'ClientForm', 'ClientInteractionForm',
    'DocumentUploadForm', 'DocumentCategoryForm',
    'AnnouncementForm', 'DirectMessageForm'
]
