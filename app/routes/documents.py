import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, send_from_directory
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.document import Document, DocumentCategory, DocumentVersion, DocumentShare
from app.models.employee import Department
from app.forms.document_forms import DocumentUploadForm
from app.services.audit_service import log_audit
from app.utils.decorators import login_required, get_current_user, get_user_role, get_managed_department

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@login_required
def index():
    user = get_current_user()
    role = get_user_role(user)
    cat_id = request.args.get('category_id', type=str)
    dept_id = request.args.get('department_id', type=str)
    file_type = request.args.get('file_type', type=str)
    search_q = request.args.get('search', '').strip()

    query = Document.active_query()

    # Role scoping for confidential documents
    if role == 'employee':
        emp_dept_id = user.employee.department_id if user.employee else None
        query = query.filter(
            db.or_(
                Document.is_confidential == False,
                Document.uploaded_by_id == user.id
            )
        ).filter(
            db.or_(
                Document.department_id.is_(None),
                Document.department_id == emp_dept_id,
                Document.uploaded_by_id == user.id
            )
        )
    elif role == 'dept_manager':
        managed_dept = get_managed_department(user)
        m_dept_id = managed_dept.id if managed_dept else None
        query = query.filter(
            db.or_(
                Document.is_confidential == False,
                Document.uploaded_by_id == user.id,
                Document.department_id == m_dept_id
            )
        )

    if cat_id and cat_id.isdigit():
        query = query.filter_by(category_id=int(cat_id))

    if dept_id and dept_id.isdigit():
        query = query.filter_by(department_id=int(dept_id))

    if file_type:
        query = query.filter(Document.file_type.ilike(file_type.strip()))

    if search_q:
        query = query.filter(
            db.or_(
                Document.title.ilike(f"%{search_q}%"),
                Document.description.ilike(f"%{search_q}%")
            )
        )

    documents_list = query.order_by(Document.id.desc()).all()
    categories = DocumentCategory.active_query().all()
    departments = Department.active_query().all()

    return render_template(
        'documents/index.html',
        documents=documents_list,
        categories=categories,
        departments=departments,
        selected_category=cat_id,
        selected_dept=dept_id,
        selected_file_type=file_type,
        search=search_q
    )


@documents_bp.route('/<int:doc_id>/download')
@login_required
def download(doc_id):
    doc = Document.get_active_or_404(doc_id)
    user = get_current_user()
    role = get_user_role(user)

    # Authorization Check
    if doc.is_confidential:
        if role not in ['super_admin', 'hr_manager'] and doc.uploaded_by_id != user.id:
            managed_dept = get_managed_department(user)
            if not (role == 'dept_manager' and managed_dept and doc.department_id == managed_dept.id):
                flash('Access Denied: This is a restricted confidential document.', 'danger')
                return redirect(url_for('documents.index'))

    if role == 'employee' and doc.department_id:
        emp_dept_id = user.employee.department_id if user.employee else None
        if doc.department_id != emp_dept_id and doc.uploaded_by_id != user.id:
            flash('Access Denied: You do not have permission to download this department document.', 'danger')
            return redirect(url_for('documents.index'))

    filename = os.path.basename(doc.file_path)
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    full_path = os.path.join(upload_dir, filename)

    if not os.path.exists(full_path):
        os.makedirs(upload_dir, exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(
                f"Office Management System - Enterprise Document Repository\r\n"
                f"Title: {doc.title}\r\n"
                f"Category: {doc.category.name if doc.category else 'General'}\r\n"
                f"Uploaded by: {doc.uploaded_by.full_name if doc.uploaded_by else 'Administrator'}\r\n"
                f"Archived Date: {doc.created_at}\r\n"
                f"Confidential: {'YES' if doc.is_confidential else 'NO'}\r\n".encode('utf-8')
            )

    safe_title = secure_filename(doc.title) or 'document'
    download_name = f"{safe_title}.{doc.file_type or 'pdf'}"
    return send_from_directory(upload_dir, filename, as_attachment=True, download_name=download_name)


@documents_bp.route('/<int:doc_id>/view')
@login_required
def view(doc_id):
    doc = Document.get_active_or_404(doc_id)
    user = get_current_user()
    role = get_user_role(user)

    if doc.is_confidential:
        if role not in ['super_admin', 'hr_manager'] and doc.uploaded_by_id != user.id:
            managed_dept = get_managed_department(user)
            if not (role == 'dept_manager' and managed_dept and doc.department_id == managed_dept.id):
                flash('Access Denied: This is a restricted confidential document.', 'danger')
                return redirect(url_for('documents.index'))

    return render_template('documents/view.html', document=doc)


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    categories = DocumentCategory.active_query().all()
    departments = Department.active_query().all()

    form = DocumentUploadForm()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    form.department_id.choices = [(0, 'All / Company-Wide')] + [(d.id, d.name) for d in departments]

    if form.validate_on_submit():
        user = get_current_user()
        file_path = 'uploads/default_document.pdf'
        file_size = 1024
        file_type = 'pdf'

        file = form.file.data
        if file and hasattr(file, 'filename') and file.filename != '':
            filename = secure_filename(file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            file_path = f"uploads/{filename}"
            file_size = os.path.getsize(save_path)
            file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'

        dept_val = form.department_id.data if form.department_id.data != 0 else None
        doc = Document(
            category_id=form.category_id.data,
            title=form.title.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            is_confidential=form.is_confidential.data,
            uploaded_by_id=user.id,
            department_id=dept_val,
            created_by=user.id,
            updated_by=user.id
        )
        try:
            db.session.add(doc)
            db.session.flush()

            # Create version 1.0
            v = DocumentVersion(
                document_id=doc.id,
                version_number='1.0',
                file_path=file_path,
                change_summary='Initial upload',
                uploaded_by_id=user.id,
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(v)
            db.session.commit()

            log_audit('CREATE', 'documents', doc.id, None, {'title': doc.title})
            flash(f'Document "{doc.title}" archived successfully.', 'success')
            return redirect(url_for('documents.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to archive document: {str(e)}', 'danger')

    return render_template('documents/upload.html', form=form, categories=categories, departments=departments)


@documents_bp.route('/<int:doc_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(doc_id):
    doc = Document.get_active_or_404(doc_id)
    categories = DocumentCategory.active_query().all()
    departments = Department.active_query().all()

    form = DocumentUploadForm(obj=doc)
    form.category_id.choices = [(c.id, c.name) for c in categories]
    form.department_id.choices = [(0, 'All / Company-Wide')] + [(d.id, d.name) for d in departments]

    if request.method == 'GET':
        form.department_id.data = doc.department_id or 0

    if form.validate_on_submit():
        user = get_current_user()
        old_val = {'title': doc.title, 'is_confidential': doc.is_confidential}

        doc.title = form.title.data.strip()
        doc.category_id = form.category_id.data
        doc.department_id = form.department_id.data if form.department_id.data != 0 else None
        doc.description = form.description.data.strip() if form.description.data else None
        doc.is_confidential = form.is_confidential.data
        doc.updated_by = user.id

        file = form.file.data
        if file and hasattr(file, 'filename') and file.filename != '':
            filename = secure_filename(file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            doc.file_path = f"uploads/{filename}"
            doc.file_size = os.path.getsize(save_path)
            doc.file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'

            # Add version 2.0 or subsequent
            next_version = f"{len(doc.versions) + 1}.0"
            v = DocumentVersion(
                document_id=doc.id,
                version_number=next_version,
                file_path=doc.file_path,
                change_summary='Document revision upload',
                uploaded_by_id=user.id,
                created_by=user.id,
                updated_by=user.id
            )
            db.session.add(v)

        try:
            db.session.commit()
            log_audit('UPDATE', 'documents', doc.id, old_val, {'title': doc.title})
            flash(f'Document "{doc.title}" updated successfully.', 'success')
            return redirect(url_for('documents.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update document: {str(e)}', 'danger')

    return render_template('documents/edit.html', form=form, document=doc, categories=categories, departments=departments)


@documents_bp.route('/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete(doc_id):
    doc = Document.get_active_or_404(doc_id)
    user = get_current_user()

    old_val = {'id': doc.id, 'title': doc.title}
    try:
        doc.soft_delete(user_id=user.id)
        db.session.commit()
        log_audit('DELETE', 'documents', doc.id, old_val, {'is_deleted': True})
        flash(f'Document "{doc.title}" moved to Recycle Bin.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete document: {str(e)}', 'danger')
    return redirect(url_for('documents.index'))
