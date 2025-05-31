from flask import Blueprint, redirect, url_for
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
    return redirect(url_for('auth_routes.login'))

auth_bp.route('/register', methods=['GET', 'POST'])(register)
auth_bp.route('/login', methods=['GET', 'POST'])(login)
auth_bp.route('/logout')(logout)
auth_bp.route('/forgot_password', methods=['GET', 'POST'])(forgot_password)
auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])(reset_password)