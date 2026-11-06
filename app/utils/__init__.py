from datetime import datetime, timezone
from app.utils.decorators import (
    login_required,
    role_required,
    admin_required,
    hr_or_admin_required,
    manager_or_admin_required,
    get_current_user
)

def utc_now():
    """Returns naive UTC datetime object compatible with Python 3.12+ and MySQL DATETIME."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

__all__ = [
    'login_required',
    'role_required',
    'admin_required',
    'hr_or_admin_required',
    'manager_or_admin_required',
    'get_current_user',
    'utc_now'
]
