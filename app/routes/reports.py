from flask import Blueprint, render_template, request, Response, abort, flash, redirect, url_for
from app.services.report_service import REPORT_DEFINITIONS, generate_report_data, export_to_csv, export_to_excel
from app.utils.decorators import login_required, get_current_user, get_user_role

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

ROLE_ALLOWED_CATEGORIES = {
    'super_admin': None, # Unrestricted
    'hr_manager': ['Employees', 'Attendance', 'Leaves', 'Payroll'],
    'dept_manager': ['Employees', 'Attendance', 'Leaves', 'Projects'],
    'employee': ['Attendance', 'Leaves', 'Projects']
}

ROLE_DISALLOWED_REPORTS = {
    'dept_manager': ['emp_salary_band'],
    'employee': ['emp_salary_band', 'proj_budgets']
}

def get_role_catalog(role):
    allowed_cats = ROLE_ALLOWED_CATEGORIES.get(role, ['Attendance', 'Leaves'])
    disallowed_ids = ROLE_DISALLOWED_REPORTS.get(role, [])

    if allowed_cats is None:
        return REPORT_DEFINITIONS

    return [
        r for r in REPORT_DEFINITIONS
        if r['category'] in allowed_cats and r['id'] not in disallowed_ids
    ]


@reports_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)

    role_catalog = get_role_catalog(role)
    if not role_catalog:
        flash('No reporting modules available for your account role.', 'warning')
        return redirect(url_for('dashboard.index'))

    category_filter = request.args.get('category', '')
    active_report_id = request.args.get('report_id', role_catalog[0]['id'])

    # Validate that active_report_id is permitted for this role
    allowed_ids = [r['id'] for r in role_catalog]
    if active_report_id not in allowed_ids:
        active_report_id = role_catalog[0]['id']

    filtered_catalog = role_catalog
    if category_filter:
        filtered_catalog = [r for r in role_catalog if r['category'].lower() == category_filter.lower()]

    current_report = next((r for r in role_catalog if r['id'] == active_report_id), role_catalog[0])
    headers, rows = generate_report_data(current_report['id'])

    categories = sorted(list(set(r['category'] for r in role_catalog)))

    return render_template(
        'reports/index.html',
        catalog=filtered_catalog,
        all_reports=role_catalog,
        categories=categories,
        current_report=current_report,
        headers=headers,
        rows=rows,
        selected_category=category_filter,
        total_reports_count=len(role_catalog)
    )


@reports_bp.route('/export/csv/<report_id>')
@login_required
def export_csv(report_id):
    user = get_current_user()
    role = get_user_role(user)
    role_catalog = get_role_catalog(role)

    current_report = next((r for r in role_catalog if r['id'] == report_id), None)
    if not current_report:
        abort(403)

    headers, rows = generate_report_data(report_id)
    csv_bytes = export_to_csv(headers, rows)

    filename = f"OMS_Report_{report_id}.csv"
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@reports_bp.route('/export/excel/<report_id>')
@login_required
def export_excel(report_id):
    user = get_current_user()
    role = get_user_role(user)
    role_catalog = get_role_catalog(role)

    current_report = next((r for r in role_catalog if r['id'] == report_id), None)
    if not current_report:
        abort(403)

    headers, rows = generate_report_data(report_id)
    excel_bytes = export_to_excel(current_report['title'], headers, rows)

    filename = f"OMS_Report_{report_id}.xlsx"
    return Response(
        excel_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
