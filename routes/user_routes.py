from flask import Blueprint
from controllers.user_controller import (
    get_user_profile,
    update_user_profile,
    change_password
)

user_bp = Blueprint('user_routes', __name__)

# User management routes
user_bp.route('/profile', methods=['GET'])(get_user_profile)
user_bp.route('/profile', methods=['PUT'])(update_user_profile)
user_bp.route('/change_password', methods=['POST'])(change_password)