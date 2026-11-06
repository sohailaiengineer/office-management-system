from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.employee import Employee, Department, Designation
from app.models.project import Project, Task
from app.models.asset import Asset
from app.models.document import Document
from app.models.client import Client
from app.models.finance import Expense, Invoice
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, hr_or_admin_required, get_current_user

recycle_bin_bp = Blueprint('recycle_bin', __name__, url_prefix='/recycle-bin')

MODEL_MAP = {
    'employees': Employee,
    'departments': Department,
    'designations': Designation,
    'projects': Project,
    'tasks': Task,
    'assets': Asset,
    'documents': Document,
    'clients': Client,
    'expenses': Expense,
    'invoices': Invoice
}

@recycle_bin_bp.route('/')
@login_required
@hr_or_admin_required
def index():
    tab = request.args.get('tab', 'employees')
    if tab not in MODEL_MAP:
        tab = 'employees'

    model_class = MODEL_MAP[tab]
    deleted_records = model_class.trash_query().order_by(model_class.deleted_at.desc()).all()

    # Counts for badges
    counts = {key: MODEL_MAP[key].trash_query().count() for key in MODEL_MAP}
    total_trash_items = sum(counts.values())

    return render_template(
        'recycle_bin/index.html',
        active_tab=tab,
        records=deleted_records,
        counts=counts,
        total_trash_items=total_trash_items
    )


@recycle_bin_bp.route('/<module_name>/<int:record_id>/restore', methods=['POST'])
@login_required
@hr_or_admin_required
def restore(module_name, record_id):
    if module_name not in MODEL_MAP:
        flash('Invalid module requested.', 'danger')
        return redirect(url_for('recycle_bin.index'))

    model_class = MODEL_MAP[module_name]
    record = model_class.query.filter_by(id=record_id, is_deleted=True).first_or_404()
    user = get_current_user()

    record.restore(user_id=user.id)
    # If restoring employee, restore associated user
    if module_name == 'employees' and getattr(record, 'user', None):
        record.user.restore(user_id=user.id)

    db.session.commit()

    log_audit('RESTORE', model_class.__tablename__, record.id, {'is_deleted': True}, {'is_deleted': False})
    flash(f'Record #{record.id} in {module_name.title()} successfully restored from Recycle Bin.', 'success')
    return redirect(url_for('recycle_bin.index', tab=module_name))


@recycle_bin_bp.route('/<module_name>/<int:record_id>/purge', methods=['POST'])
@login_required
def purge(module_name, record_id):
    user = get_current_user()
    if not user.is_admin and 'super_admin' not in user.role_names:
        flash('Only Super Administrators can permanently purge records.', 'danger')
        return redirect(url_for('recycle_bin.index', tab=module_name))

    if module_name not in MODEL_MAP:
        flash('Invalid module.', 'danger')
        return redirect(url_for('recycle_bin.index'))

    model_class = MODEL_MAP[module_name]
    record = model_class.query.filter_by(id=record_id, is_deleted=True).first_or_404()

    db.session.delete(record)
    db.session.commit()

    log_audit('PURGE', model_class.__tablename__, record_id, None, {'permanently_deleted': True})
    flash(f'Record #{record_id} permanently purged from database.', 'info')
    return redirect(url_for('recycle_bin.index', tab=module_name))
