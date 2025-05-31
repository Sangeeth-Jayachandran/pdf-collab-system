from flask import Blueprint, redirect, url_for
from flask_login import current_user
from controllers.auth_controller import (
    register,
    login,
    logout,
    forgot_password,
    reset_password
)

auth_bp = Blueprint('auth_routes', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('auth_routes.dashboard'))
    return redirect(url_for('auth_routes.login'))
# Authentication routes

auth_bp.route('/register', methods=['GET', 'POST'])(register)
auth_bp.route('/login', methods=['GET', 'POST'])(login)
auth_bp.route('/logout')(logout)
auth_bp.route('/forgot_password', methods=['GET', 'POST'])(forgot_password)
auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])(reset_password)