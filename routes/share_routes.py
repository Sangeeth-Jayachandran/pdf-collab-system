from flask import Blueprint
from controllers.share_controller import (
    share_pdf,
    share_pdf_email,
    view_shared_pdf,
)

share_bp = Blueprint('share_routes', __name__)

# PDF sharing routes
share_bp.route('/share/<int:file_id>', methods=['GET', 'POST'])(share_pdf)
share_bp.route('/email/<int:file_id>', methods=['POST'])(share_pdf_email)
share_bp.route('/shared/<token>', methods=['GET'])(view_shared_pdf)
