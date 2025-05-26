from flask import Blueprint
from controllers.comment_controller import (
    add_comment,
    get_comments,
    delete_comment
)

comment_bp = Blueprint('comment_routes', __name__)

# Comment routes
comment_bp.route('', methods=['POST'])(add_comment)
comment_bp.route('/<int:file_id>', methods=['GET'])(get_comments)
comment_bp.route('/<int:comment_id>', methods=['DELETE'])(delete_comment)