from flask import current_app
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from utils.database import db_cursor, db_pool, get_db_pool

bcrypt = Bcrypt()

class User(UserMixin):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.email = kwargs.get('email')
        self.password = kwargs.get('password')
        self.created_at = kwargs.get('created_at')
        self.reset_token = kwargs.get('reset_token')
    
    db_pool = get_db_pool()

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
        """Fixed version with proper connection handling"""
        try:
            # Access pool through current_app
            if not hasattr(current_app, 'db_pool'):
                raise RuntimeError("Database pool not initialized")
                
            connection = current_app.db_pool.get_connection()
            try:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    user_data = cursor.fetchone()
                    return User(**user_data) if user_data else None
            finally:
                connection.close()
        except Exception as e:
            current_app.logger.error(f"User lookup failed: {str(e)}")
            return None