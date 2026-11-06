from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models.client import Client, ClientContact, ClientInteraction
from app.models.employee import Employee
from app.forms.client_forms import ClientForm, ClientInteractionForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, manager_or_admin_required, get_current_user

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    query = Client.active_query()

    if search:
        query = query.filter(
            (Client.company_name.ilike(f'%{search}%')) |
            (Client.client_code.ilike(f'%{search}%')) |
            (Client.industry.ilike(f'%{search}%'))
        )

    clients = query.order_by(Client.id.desc()).all()
    return render_template('clients/index.html', clients=clients, search=search)


@clients_bp.route('/create', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def create():
    form = ClientForm()
    if form.validate_on_submit():
        code = form.client_code.data.strip().upper()
        if Client.query.filter_by(client_code=code).first():
            flash('Client Code already in use.', 'danger')
            return render_template('clients/create.html', form=form)

        user = get_current_user()
        client = Client(
            company_name=form.company_name.data.strip(),
            client_code=code,
            industry=form.industry.data.strip() if form.industry.data else None,
            email=form.email.data.strip() if form.email.data else None,
            phone=form.phone.data.strip() if form.phone.data else None,
            website=form.website.data.strip() if form.website.data else None,
            address=form.address.data.strip() if form.address.data else None,
            country=form.country.data.strip(),
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(client)
            db.session.commit()
            log_audit('CREATE', 'clients', client.id, None, {'name': client.company_name, 'code': client.client_code})
            flash(f'Client account "{client.company_name}" created successfully.', 'success')
            return redirect(url_for('clients.view', client_id=client.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating client: {str(e)}', 'danger')

    return render_template('clients/create.html', form=form)


@clients_bp.route('/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def edit(client_id):
    client = Client.get_active_or_404(client_id)
    form = ClientForm(obj=client)

    if form.validate_on_submit():
        user = get_current_user()
        code = form.client_code.data.strip().upper()
        existing = Client.query.filter(Client.client_code == code, Client.id != client.id).first()
        if existing:
            flash('Client Code is already used by another client.', 'danger')
            return render_template('clients/edit.html', form=form, client=client)

        old_val = {'company_name': client.company_name, 'client_code': client.client_code}
        client.company_name = form.company_name.data.strip()
        client.client_code = code
        client.industry = form.industry.data.strip() if form.industry.data else None
        client.email = form.email.data.strip() if form.email.data else None
        client.phone = form.phone.data.strip() if form.phone.data else None
        client.website = form.website.data.strip() if form.website.data else None
        client.address = form.address.data.strip() if form.address.data else None
        client.country = form.country.data.strip()
        client.updated_by = user.id

        try:
            db.session.commit()
            log_audit('UPDATE', 'clients', client.id, old_val, {'company_name': client.company_name, 'client_code': client.client_code})
            flash(f'Client account "{client.company_name}" updated successfully.', 'success')
            return redirect(url_for('clients.view', client_id=client.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating client: {str(e)}', 'danger')

    return render_template('clients/edit.html', form=form, client=client)


@clients_bp.route('/<int:client_id>')
@login_required
def view(client_id):
    client = Client.get_active_or_404(client_id)
    employees = Employee.active_query().all()
    form = ClientInteractionForm()
    form.conducted_by_id.choices = [(0, '-- Auto (Logged in user) --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in employees]
    return render_template('clients/view.html', client=client, employees=employees, interaction_form=form)


@clients_bp.route('/<int:client_id>/interactions', methods=['POST'])
@login_required
def add_interaction(client_id):
    client = Client.get_active_or_404(client_id)
    user = get_current_user()
    form = ClientInteractionForm()
    employees = Employee.active_query().all()
    form.conducted_by_id.choices = [(0, '-- Auto (Logged in user) --')] + [(e.id, f"{e.emp_code} - {e.full_name}") for e in employees]

    if form.validate_on_submit():
        emp_id = form.conducted_by_id.data if form.conducted_by_id.data != 0 else (user.employee.id if user.employee else None)
        interaction = ClientInteraction(
            client_id=client.id,
            interaction_type=form.interaction_type.data,
            interaction_date=date.today(),
            conducted_by_id=emp_id,
            summary=form.summary.data.strip(),
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(interaction)
            db.session.commit()
            log_audit('CREATE', 'client_interactions', interaction.id, None, {'client_id': client.id, 'type': interaction.interaction_type})
            flash('Interaction log recorded successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to record interaction: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"{field}: {err}", 'danger')

    return redirect(url_for('clients.view', client_id=client.id))


@clients_bp.route('/<int:client_id>/delete', methods=['POST'])
@login_required
@manager_or_admin_required
def delete(client_id):
    client = Client.get_active_or_404(client_id)
    user = get_current_user()

    old_val = {'id': client.id, 'name': client.company_name}
    try:
        client.soft_delete(user_id=user.id)
        db.session.commit()
        log_audit('DELETE', 'clients', client.id, old_val, {'is_deleted': True})
        flash(f'Client "{client.company_name}" moved to Recycle Bin.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete client: {str(e)}', 'danger')
    return redirect(url_for('clients.index'))
