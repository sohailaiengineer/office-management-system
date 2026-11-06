import json
from flask import request, session
from app.extensions import db
from app.models.system import AuditLog

def log_audit(action, table_name, record_id, old_values=None, new_values=None, user_id=None):
    """
    Records an immutable audit entry in the audit_logs table.
    Captures actor ID, table, action, old/new serialized JSON state, IP address, and user agent.
    """
    try:
        actor_id = user_id or session.get('user_id')
        ip_addr = request.remote_addr if request else '127.0.0.1'
        u_agent = request.headers.get('User-Agent')[:255] if request and request.headers.get('User-Agent') else 'System'

        old_str = json.dumps(old_values, default=str) if old_values is not None else None
        new_str = json.dumps(new_values, default=str) if new_values is not None else None

        audit = AuditLog(
            user_id=actor_id,
            action=action.upper(),
            table_name=table_name,
            record_id=record_id,
            old_values=old_str,
            new_values=new_str,
            ip_address=ip_addr,
            user_agent=u_agent
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fail silently in production or print in development to not abort primary business transaction
        print(f"[Audit Log Error]: {e}")
