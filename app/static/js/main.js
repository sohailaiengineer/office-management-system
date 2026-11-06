/**
 * Office Management System (OMS) — Enterprise Client JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Bootstrap Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // 2. Auto-dismiss Flash Alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // 3. Confirm Delete / Purge Dialogs
    const deleteForms = document.querySelectorAll('.confirm-delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const message = form.getAttribute('data-confirm-message') || 'Are you sure you want to move this record to the Recycle Bin?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // 4. Quick Table Search Filter
    const quickSearchInput = document.getElementById('tableQuickSearch');
    if (quickSearchInput) {
        quickSearchInput.addEventListener('keyup', function() {
            const value = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('.table-searchable tbody tr');
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.indexOf(value) > -1 ? '' : 'none';
            });
        });
    }

    // 5. Sidebar Toggle for Mobile
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('d-none');
        });
    }
});

// JSON Modal Viewer for Audit Logs
function viewAuditJson(title, jsonString) {
    const modalTitle = document.getElementById('auditModalTitle');
    const modalBody = document.getElementById('auditModalBody');
    if (modalTitle && modalBody) {
        modalTitle.textContent = title;
        try {
            const parsed = JSON.parse(jsonString);
            modalBody.textContent = JSON.stringify(parsed, null, 2);
        } catch (e) {
            modalBody.textContent = jsonString || 'No data recorded.';
        }
        const modal = new bootstrap.Modal(document.getElementById('auditDetailModal'));
        modal.show();
    }
}
