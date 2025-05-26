import secrets
from flask import current_app
from flask_bcrypt import Bcrypt
from models import User
import re

def validate_registration(name, email, password):
    """Validate user registration data"""
    if not name or not email or not password:
        return "All fields are required"
    
    if len(password) < 8:
        return "Password must be at least 8 characters"
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format"
    
    return None

def validate_login(email, password):
    """Validate user login credentials"""
    with current_app.db_pool.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        
        if not user_data:
            return None, "Invalid email or password"
        
        if not User.check_password_hash(user_data['password'], password):
            return None, "Invalid email or password"
        
        user = User(user_data['id'], user_data['email'], user_data['name'])
        return user, None

def validate_password_change(current_password, new_password, confirm_password):
    """Validate password change request"""
    if not current_password or not new_password or not confirm_password:
        return "All password fields are required"
    
    if new_password != confirm_password:
        return "New passwords do not match"
    
    if len(new_password) < 8:
        return "New password must be at least 8 characters"
    
    return None

def generate_reset_token():
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)

def validate_reset_token(token):
    """Validate a password reset token"""
    with current_app.db_pool.cursor() as cursor:
        cursor.execute("""
            SELECT prt.*, u.email 
            FROM password_reset_tokens prt
            JOIN users u ON prt.user_id = u.id
            WHERE prt.token = %s AND prt.expires_at > NOW() AND prt.used = 0
        """, (token,))
        return cursor.fetchone()