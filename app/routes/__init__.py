from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.employees import employees_bp
from app.routes.departments import departments_bp
from app.routes.attendance import attendance_bp
from app.routes.leaves import leaves_bp
from app.routes.payroll import payroll_bp
from app.routes.finance import finance_bp
from app.routes.projects import projects_bp
from app.routes.tasks import tasks_bp
from app.routes.clients import clients_bp
from app.routes.assets import assets_bp
from app.routes.documents import documents_bp
from app.routes.communication import communication_bp
from app.routes.reports import reports_bp
from app.routes.recycle_bin import recycle_bin_bp
from app.routes.system import system_bp

all_blueprints = [
    auth_bp,
    dashboard_bp,
    employees_bp,
    departments_bp,
    attendance_bp,
    leaves_bp,
    payroll_bp,
    finance_bp,
    projects_bp,
    tasks_bp,
    clients_bp,
    assets_bp,
    documents_bp,
    communication_bp,
    reports_bp,
    recycle_bin_bp,
    system_bp
]
