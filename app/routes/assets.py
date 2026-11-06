from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.asset import Asset, AssetCategory, AssetAssignment, AssetMaintenance, AssetRequest
from app.models.employee import Employee
from app.forms.asset_forms import AssetForm, AssetAssignmentForm, AssetRequestForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, hr_or_admin_required, get_current_user

assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

@assets_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    cat_filter = request.args.get('category_id', '')

    query = Asset.active_query()
    if status_filter:
        query = query.filter_by(asset_status=status_filter)
    if cat_filter and cat_filter.isdigit():
        query = query.filter_by(category_id=int(cat_filter))

    assets_list = query.order_by(Asset.id.desc()).all()
    categories = AssetCategory.active_query().all()
    requests_list = AssetRequest.active_query().order_by(AssetRequest.id.desc()).limit(10).all()

    return render_template(
        'assets/index.html',
        assets=assets_list,
        categories=categories,
        requests=requests_list,
        selected_status=status_filter,
        selected_category=cat_filter
    )


@assets_bp.route('/create', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def create():
    form = AssetForm()
    form.category_id.choices = [(c.id, c.name) for c in AssetCategory.active_query().all()]
    form.purchase_date.data = date.today()

    if form.validate_on_submit():
        if Asset.query.filter_by(asset_tag=form.asset_tag.data.strip().upper()).first():
            flash('Asset tag barcode already exists.', 'danger')
            return render_template('assets/create.html', form=form)

        user = get_current_user()
        asset = Asset(
            category_id=form.category_id.data,
            name=form.name.data.strip(),
            asset_tag=form.asset_tag.data.strip().upper(),
            serial_number=form.serial_number.data.strip() if form.serial_number.data else None,
            purchase_date=form.purchase_date.data,
            purchase_cost=form.purchase_cost.data,
            warranty_expiry=form.warranty_expiry.data,
            condition=form.condition.data,
            asset_status=form.asset_status.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(asset)
        db.session.commit()

        log_audit('CREATE', 'assets', asset.id, None, {'tag': asset.asset_tag, 'name': asset.name})
        flash(f'Asset "{asset.name}" ({asset.asset_tag}) registered.', 'success')
        return redirect(url_for('assets.index'))

    return render_template('assets/create.html', form=form)


@assets_bp.route('/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def edit(asset_id):
    asset = Asset.get_active_or_404(asset_id)
    form = AssetForm(obj=asset)
    form.category_id.choices = [(c.id, c.name) for c in AssetCategory.active_query().all()]

    if form.validate_on_submit():
        tag = form.asset_tag.data.strip().upper()
        existing = Asset.query.filter(Asset.asset_tag == tag, Asset.id != asset.id).first()
        if existing:
            flash('Asset tag already belongs to another item.', 'danger')
            return render_template('assets/edit.html', form=form, asset=asset)

        user = get_current_user()
        old_val = {'name': asset.name, 'tag': asset.asset_tag, 'status': asset.asset_status}

        asset.category_id = form.category_id.data
        asset.name = form.name.data.strip()
        asset.asset_tag = tag
        asset.serial_number = form.serial_number.data.strip() if form.serial_number.data else None
        asset.purchase_date = form.purchase_date.data
        asset.purchase_cost = form.purchase_cost.data
        asset.warranty_expiry = form.warranty_expiry.data
        asset.condition = form.condition.data
        asset.asset_status = form.asset_status.data
        asset.updated_by = user.id

        try:
            db.session.commit()
            log_audit('UPDATE', 'assets', asset.id, old_val, {'name': asset.name, 'tag': asset.asset_tag, 'status': asset.asset_status})
            flash(f'Asset "{asset.name}" updated successfully.', 'success')
            return redirect(url_for('assets.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating asset: {str(e)}', 'danger')

    return render_template('assets/edit.html', form=form, asset=asset)


@assets_bp.route('/<int:asset_id>/assign', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def assign(asset_id):
    asset = Asset.get_active_or_404(asset_id)
    form = AssetAssignmentForm()
    form.employee_id.choices = [(e.id, f"{e.emp_code} - {e.full_name}") for e in Employee.active_query().all()]
    form.assigned_date.data = date.today()

    if form.validate_on_submit():
        user = get_current_user()
        assignment = AssetAssignment(
            asset_id=asset.id,
            employee_id=form.employee_id.data,
            assigned_date=form.assigned_date.data,
            condition_at_assign=form.condition_at_assign.data,
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(assignment)
        asset.asset_status = 'Assigned'
        asset.updated_by = user.id
        db.session.commit()

        log_audit('CREATE', 'asset_assignments', assignment.id, None, {'asset_id': asset.id, 'employee_id': form.employee_id.data})
        flash(f'Asset {asset.asset_tag} assigned successfully.', 'success')
        return redirect(url_for('assets.index'))

    return render_template('assets/assign.html', form=form, asset=asset)


@assets_bp.route('/<int:asset_id>/return', methods=['POST'])
@login_required
@hr_or_admin_required
def return_asset(asset_id):
    asset = Asset.get_active_or_404(asset_id)
    active_assignment = AssetAssignment.active_query().filter_by(asset_id=asset.id, returned_date=None).first()
    user = get_current_user()

    if active_assignment:
        active_assignment.returned_date = date.today()
        active_assignment.condition_at_return = request.form.get('condition', 'Good')
        active_assignment.updated_by = user.id

    asset.asset_status = 'Available'
    asset.updated_by = user.id
    db.session.commit()

    log_audit('UPDATE', 'assets', asset.id, {'status': 'Assigned'}, {'status': 'Available'})
    flash(f'Asset {asset.asset_tag} returned to available inventory.', 'success')
    return redirect(url_for('assets.index'))


@assets_bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_asset():
    form = AssetRequestForm()
    form.category_id.choices = [(c.id, c.name) for c in AssetCategory.active_query().all()]

    if form.validate_on_submit():
        user = get_current_user()
        if not user.employee:
            flash('Employee profile required.', 'danger')
            return redirect(url_for('assets.index'))

        req = AssetRequest(
            employee_id=user.employee.id,
            category_id=form.category_id.data,
            reason=form.reason.data.strip(),
            priority=form.priority.data,
            request_status='Pending',
            created_by=user.id,
            updated_by=user.id
        )
        db.session.add(req)
        db.session.commit()

        log_audit('CREATE', 'asset_requests', req.id, None, {'category_id': req.category_id, 'priority': req.priority})
        flash('Equipment requisition submitted.', 'success')
        return redirect(url_for('assets.index'))

    return render_template('assets/request.html', form=form)


@assets_bp.route('/<int:asset_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete(asset_id):
    asset = Asset.get_active_or_404(asset_id)
    user = get_current_user()

    old_val = {'id': asset.id, 'tag': asset.asset_tag}
    asset.soft_delete(user_id=user.id)
    db.session.commit()

    log_audit('DELETE', 'assets', asset.id, old_val, {'is_deleted': True})
    flash(f'Asset "{asset.name}" moved to Recycle Bin.', 'warning')
    return redirect(url_for('assets.index'))
