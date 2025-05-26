from flask import Blueprint
from controllers.pdf_controller import (
    dashboard,
    upload_file,
    view_pdf,
    uploaded_file,
    delete_pdf,
    search
)

pdf_bp = Blueprint('pdf_routes', __name__)

# PDF management routes
pdf_bp.route('/dashboard', methods=['GET'])(dashboard)
pdf_bp.route('/upload', methods=['POST'])(upload_file)
pdf_bp.route('/view/<int:file_id>', methods=['GET'])(view_pdf)
pdf_bp.route('/uploads/<filename>', methods=['GET'])(uploaded_file)
pdf_bp.route('/delete/<int:file_id>', methods=['POST'])(delete_pdf)
pdf_bp.route('/search', methods=['GET'])(search)