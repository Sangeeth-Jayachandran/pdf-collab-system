from flask import current_app
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

class User:
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name
    
    @staticmethod
    def generate_password_hash(password):
        """Generate a password hash"""
        return bcrypt.generate_password_hash(password).decode('utf-8')
    
    @staticmethod
    def check_password_hash(hashed_password, password):
        """Check if password matches hash"""
        return bcrypt.check_password_hash(hashed_password, password)
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        with current_app.db_pool.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_data['id'], user_data['email'], user_data['name'])
            return None