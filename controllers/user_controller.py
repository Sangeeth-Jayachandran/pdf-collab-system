from flask import jsonify, request
from flask_login import current_user, login_required
from models import User
from utils.database import db_cursor
from utils.auth_utils import validate_password_change

@login_required
def get_user_profile():
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, created_at 
                FROM users 
                WHERE id = %s
            """, (current_user.id,))
            user = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'created_at': user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                }
            })
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@login_required
def update_user_profile():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    
    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400
    
    try:
        with db_cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET name = %s, email = %s 
                WHERE id = %s
            """, (name, email, current_user.id))
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@login_required
def change_password():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    error = validate_password_change(current_password, new_password, confirm_password)
    if error:
        return jsonify({'error': error}), 400
    
    try:
        with db_cursor() as cursor:
            # Verify current password
            cursor.execute("SELECT password FROM users WHERE id = %s", (current_user.id,))
            user = cursor.fetchone()
            
            if not user or not User.check_password_hash(user['password'], current_password):
                return jsonify({'error': 'Current password is incorrect'}), 400
            
            # Update password
            hashed_password = User.generate_password_hash(new_password)
            cursor.execute("""
                UPDATE users 
                SET password = %s 
                WHERE id = %s
            """, (hashed_password, current_user.id))
            
            return jsonify({
                'success': True,
                'message': 'Password changed successfully'
            })
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500